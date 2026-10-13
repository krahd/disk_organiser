"""Pure workflow mutations plus read-only checks of the inert source template."""
from pathlib import Path, PurePosixPath
import ast
import hashlib
import posixpath
import sys
import json
import re
import unittest

import stage_b_workflow_guard as guard


class MemoryPath:
    """Only the read-only Path surface used by guard.check; no filesystem IO."""
    def __init__(self, files, name=''):
        self.files = files; self.name = name

    def __truediv__(self, child):
        return MemoryPath(self.files, self.name + ('/' if self.name else '') + child)

    def __str__(self):
        return self.name

    @property
    def suffix(self):
        return PurePosixPath(self.name).suffix

    def relative_to(self, root):
        prefix = root.name + '/' if root.name else ''
        if not self.name.startswith(prefix):
            raise ValueError('outside model root')
        return self.name.removeprefix(prefix)

    def rglob(self, pattern):
        if pattern != '*':
            raise ValueError('model glob')
        return (MemoryPath(self.files, name) for name in self.files if name.startswith(self.name + '/'))

    def is_file(self):
        return self.name in self.files

    def read_bytes(self):
        if self.name not in self.files:
            raise FileNotFoundError(self.name)
        return self.files[self.name]


class WorkflowTests(unittest.TestCase):
    def model(self):
        files={'.github/workflows/old.yml':b'old job', 'native/DiskInventoryCore/Package.swift':b'fixed package'}
        baseline={k:hashlib.sha256(v).hexdigest() for k,v in files.items()}
        return files,baseline,b'exact manual template'

    def testDisabledAndExactSingleManualActivation(self):
        files,base,template=self.model()
        self.assertTrue(guard.validate(files,base,template,False))
        files[guard.WORKFLOW]=template
        with self.assertRaises(AssertionError):guard.validate(files,base,template,False)
        self.assertTrue(guard.validate(files,base,template,True))

    def testNewOrRenamedYamlWorkflowAndTransitiveCallerRefuse(self):
        # Workflow-byte mutations only; the explicit local closure is tested below.
        for path,data in [('.github/workflows/other.yaml',b'on: workflow_call'),('.github/workflows/new.yml',b'uses: ./helper'),
                          ('.github/workflows/sub/other.yaml',b'workflow_run'),('.github/workflows/new.yml',b'python disguised.py')]:
            files,base,template=self.model();files[path]=data
            with self.assertRaises(AssertionError):guard.validate(files,base,template,False)

    def testChangedOrdinaryHelperOrAddedAutodiscoveredSourceRefuses(self):
        files,base,template=self.model();files['native/DiskInventoryCore/Package.swift']=b'add host'
        with self.assertRaises(AssertionError):guard.validate(files,base,template,False)
        files,base,template=self.model();files['native/DiskInventoryCore/Tests/New.swift']=b'invoke host'
        with self.assertRaises(AssertionError):guard.validate(files,base,template,False)

    def testOnlyExactQuarantineSubtreeIsExcluded(self):
        self.assertFalse(guard.ordinary_native_source(guard.QUARANTINE + 'Sources/Host.swift'))
        for path in (
                'native/DiskInventoryCore/Sources/DiskInventoryDesktop/SelectedFolderFeasibilityHook.swift',
                'native/DiskInventoryCore/Sources/DiskInventoryDesktop/SelectedFolderFeasibility/Hook.swift',
                'native/DiskInventoryCore/Validation/SelectedFolderFeasibilityOther/Hook.swift',
                'native/DiskInventoryCore/Validation/SelectedFolderFeasibility.py'):
            with self.subTest(path=path):
                self.assertTrue(guard.ordinary_native_source(path))
                for enabled in (False, True):
                    files,base,template=self.model();files[path]=b'ordinary caller'
                    if enabled:files[guard.WORKFLOW]=template
                    with self.assertRaisesRegex(AssertionError,'ordinary native source graph changed'):
                        guard.validate(files,base,template,enabled)

    def testCollectionUsesSameExactSubtreePredicateInBothModes(self):
        for enabled in (False, True):
            for path in (
                    'native/DiskInventoryCore/Sources/DiskInventoryDesktop/SelectedFolderFeasibilityHook.swift',
                    'native/DiskInventoryCore/Sources/DiskInventoryDesktop/SelectedFolderFeasibility/Hook.swift'):
                with self.subTest(enabled=enabled,path=path):
                    files,base,template=self.model()
                    files[guard.QUARANTINE+'StageB/workflow-baseline.json']=json.dumps(base).encode()
                    files[guard.QUARANTINE+'StageB/owned-selected-folder-build.static-dependencies.yml.inert']=template
                    files[guard.QUARANTINE+'Sources/Host.swift']=b'isolated host'
                    if enabled:files[guard.WORKFLOW]=template
                    self.assertTrue(guard.check(MemoryPath(files),enabled))
                    files[path]=b'ordinary caller'
                    with self.assertRaisesRegex(AssertionError,'ordinary native source graph changed'):
                        guard.check(MemoryPath(files),enabled)

    def testKnownNativeLaneHelperAndExplicitLocalImportMutationsRefuse(self):
        paths=('scripts/test_native_library_protocol.cjs', 'frontend/native-library-protocol.js',
               'backend/observation_session.py', 'backend/disk_model_analysis.py', 'backend/disk_model_schema.py')
        repo=Path(__file__).parents[5]
        actual=json.loads((Path(__file__).parents[1]/'StageB/workflow-baseline.json').read_bytes())
        self.assertTrue(set(paths)<=actual.keys())
        for enabled in (False, True):
            for changed in paths:
                with self.subTest(enabled=enabled,path=changed):
                    files,base,template=self.model()
                    files.update({path:(repo/path).read_bytes() for path in paths})
                    base.update({path:actual[path] for path in paths})
                    files[guard.QUARANTINE+'StageB/workflow-baseline.json']=json.dumps(base).encode()
                    files[guard.QUARANTINE+'StageB/owned-selected-folder-build.static-dependencies.yml.inert']=template
                    if enabled:files[guard.WORKFLOW]=template
                    self.assertTrue(guard.check(MemoryPath(files),enabled))
                    files[changed]+=b'\nchanged ordinary caller'
                    with self.assertRaisesRegex(AssertionError,'ordinary workflow/helper changed:'):
                        guard.check(MemoryPath(files),enabled)
    def testAllNativeClosurePythonImportNodesAndLiteralLocalJSRequiresArePinned(self):
        repo=Path(__file__).parents[5]
        pinned=json.loads((Path(__file__).parents[1]/'StageB/workflow-baseline.json').read_bytes())
        dependencies=set()
        for path in pinned:
            if path.endswith('.py'):
                for node in ast.walk(ast.parse((repo/path).read_bytes())):
                    if isinstance(node,ast.Import):
                        modules=[item.name for item in node.names]
                    elif isinstance(node,ast.ImportFrom):
                        self.assertEqual(node.level,0,path)
                        modules=([node.module+'.'+item.name for item in node.names]
                                 if node.module=='backend' else [node.module])
                    else:continue
                    for name in modules:
                        if name.split('.')[0] in sys.stdlib_module_names:continue
                        candidates=[name.replace('.','/')+'.py',
                                    posixpath.join(posixpath.dirname(path),name.replace('.','/')+'.py')]
                        local=[item for item in candidates if (repo/item).is_file()]
                        self.assertTrue(local,(path,name))
                        self.assertTrue(set(local)<=pinned.keys(),(path,name,local))
                        dependencies.update(local)
            elif path.endswith(('.js','.cjs')):
                raw=(repo/path).read_text()
                for name in re.findall(r'require\(["\']([^"\']+)["\']\)',raw):
                    if not name.startswith('.'):continue
                    target=posixpath.normpath(posixpath.join(posixpath.dirname(path),name))
                    self.assertIn(target,pinned,(path,name))
                    dependencies.add(target)
        self.assertTrue({'backend/disk_model_analysis.py','backend/disk_model_schema.py',
                         'frontend/manual-planning-model.js'}<=dependencies)

    def testEnabledCannotSwapManualBytesOrOldWorkflow(self):
        files,base,template=self.model();files[guard.WORKFLOW]=b'on: push'
        with self.assertRaises(AssertionError):guard.validate(files,base,template,True)
        files[guard.WORKFLOW]=template;files['.github/workflows/old.yml']=b'call manual job'
        with self.assertRaises(AssertionError):guard.validate(files,base,template,True)

    def testSeparateStartupWorkflowOnlyExactBytesWithBuildFalse(self):
        files,base,template=self.model();startup=b'exact startup template'
        self.assertTrue(guard.validate(files,base,template,False,startup_template=startup))
        files[guard.STARTUP_WORKFLOW]=startup
        self.assertTrue(guard.validate(files,base,template,False,startup_template=startup))
        for replacement in [None,b'',b'wrong',b'x'*16385,'text']:
            with self.assertRaises(AssertionError):guard.validate(files,base,template,False,startup_template=replacement)

    def testBuildAndStartupActivationCannotCoexist(self):
        files,base,template=self.model();startup=b'exact startup template'
        files[guard.WORKFLOW]=template;files[guard.STARTUP_WORKFLOW]=startup
        with self.assertRaisesRegex(AssertionError,'build disabled'):
            guard.validate(files,base,template,True,startup_template=startup)

    def testStartupAllowanceDoesNotAdmitOtherCallersOrMutatedBaseline(self):
        for path in ['.github/workflows/owned-startup-key-observation.yaml',
                     '.github/workflows/Owned-startup-key-observation.yml',
                     '.github/workflows/nested/owned-startup-key-observation.yml']:
            files,base,template=self.model();files[path]=b'exact startup template'
            with self.assertRaises(AssertionError):guard.validate(files,base,template,False,startup_template=files[path])
        files,base,template=self.model();files[guard.STARTUP_WORKFLOW]=b'exact startup template'
        files['.github/workflows/old.yml']=b'changed'
        with self.assertRaises(AssertionError):guard.validate(files,base,template,False,startup_template=files[guard.STARTUP_WORKFLOW])

    def testStartupCollectionUsesOnlyFixedTemplateAndKeepsOrdinaryGraph(self):
        files,base,template=self.model();startup=b'exact startup template'
        files[guard.QUARANTINE+'StageB/workflow-baseline.json']=json.dumps(base).encode()
        files[guard.QUARANTINE+'StageB/owned-selected-folder-build.static-dependencies.yml.inert']=template
        files[guard.QUARANTINE+'StageB/owned-startup-key-observation.yml.inert']=startup
        files[guard.STARTUP_WORKFLOW]=startup
        self.assertTrue(guard.check(MemoryPath(files),False))
        files['native/DiskInventoryCore/Sources/New.swift']=b'ordinary caller'
        with self.assertRaisesRegex(AssertionError,'ordinary native source graph changed'):
            guard.check(MemoryPath(files),False)

    def testStartupRemovalReturnsToOriginalDisabledState(self):
        files,base,template=self.model();startup=b'exact startup template'
        files[guard.STARTUP_WORKFLOW]=startup
        self.assertTrue(guard.validate(files,base,template,False,startup_template=startup))
        del files[guard.STARTUP_WORKFLOW]
        self.assertTrue(guard.validate(files,base,template,False))

    def testFrozenTemplateHasOnlyReviewedManualSurface(self):
        root=Path(__file__).parents[1];raw=(root/'StageB/owned-selected-folder-build.yml.inert').read_text()
        self.assertEqual(re.findall(r'^  ([A-Za-z_-]+):$',raw,re.M),['workflow_dispatch','owned-build-only'])
        self.assertIn('runs-on: macos-15',raw);self.assertIn('timeout-minutes: 20',raw)
        self.assertIn('persist-credentials: false',raw);self.assertIn('set-safe-directory: false',raw)
        self.assertEqual(raw.count('uses:'),2);self.assertNotIn('continue-on-error',raw)
        self.assertNotIn('test-without-building',raw);self.assertNotIn('workflow_call',raw)
        self.assertIn('if-no-files-found: error',raw);self.assertIn('retention-days: 14',raw)
        self.assertNotIn('${{ inputs.',raw.split('        run: |')[1])


if __name__=='__main__':unittest.main()
