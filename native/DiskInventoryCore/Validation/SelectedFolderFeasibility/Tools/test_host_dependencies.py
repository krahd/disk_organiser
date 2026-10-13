"""Memory-only fixtures derived from Apple's pinned -L formatter/test grammar.

The primary otool-classic-L test covers weak/reexport/upward/lazy suffixes.
Names below are our own system-path fixtures, not measured Xcode output.
No target binary, system-tool leaf, process or filesystem inventory is read.
"""
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock, patch
import json
from pathlib import Path
import hashlib
import stat
import unittest

import native_observations as no
import probe_contract as pc
from test_native_observations import ROOT, result

EXE = ROOT + '/' + no.EXECUTABLES[0]
SYSTEM = '/usr/lib/libSystem.B.dylib'
ARGS = (no.OTOOL, '-arch', 'all', '-L', EXE)
IDENTITY = (1, 2, stat.S_IFREG | 0o755, 0, 0, 10000, 3, 4)


def record(name, kind=''):
    return '\t' + name + ' (compatibility version 1.0.0, current version 65535.255.255' + (', '+kind if kind else '') + ')\n'


def output(sections=None):
    sections = sections or [('arm64', [record(SYSTEM)]), ('x86_64', [record(SYSTEM)])]
    return ''.join(EXE+' (architecture '+arch+'):\n'+''.join(rows) for arch, rows in sections).encode()


def tool_stat(**changes):
    values = dict(zip(('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_size',
                       'st_mtime_ns', 'st_ctime_ns'), IDENTITY))
    values.update(changes)
    return SimpleNamespace(**values)


class HostDependencyTests(unittest.TestCase):
    def testPrimaryFormatterQualifiersAndDifferentArchitectureSets(self):
        rows = [record(SYSTEM)] + [record('/usr/lib/lib'+kind+'.dylib', kind)
                                   for kind in ('weak', 'reexport', 'upward', 'lazy')]
        framework = record('/System/Library/Frameworks/AppKit.framework/Versions/C/AppKit')
        nested = record('/System/Library/Frameworks/ApplicationServices.framework/Versions/A/Frameworks/CoreGraphics.framework/Versions/A/CoreGraphics')
        sections = [('arm64', rows + [framework]), ('x86_64', [record(SYSTEM), nested])]
        parsed = no.parse_host_dependencies(output(sections), EXE)
        self.assertEqual(parsed, no.parse_host_dependencies(output(sections[::-1]), EXE))
        self.assertEqual([x[0] for x in parsed], ['arm64', 'x86_64'])
        self.assertEqual([x[3] for x in parsed[0][1]], ['normal', 'weak', 'reexport', 'upward', 'lazy', 'normal'])
        self.assertNotEqual(parsed[0][1], parsed[1][1])

    def testMissingDuplicateForeignThinAndUnlabelledArchitecturesRefuse(self):
        raw = output()
        variants = [output([('arm64', [record(SYSTEM)])]), raw+raw,
                    raw.replace(b'architecture x86_64', b'architecture arm64'),
                    raw.replace(b'architecture x86_64', b'architecture arm64e'),
                    raw.replace(b' (architecture arm64)', b''),
                    raw.replace(EXE.encode(), b'/other/OwnedFolderProbe', 1),
                    raw.replace(b' (architecture arm64):', b' (architecture arm64): warning'),
                    record(SYSTEM).encode()+raw]
        for changed in variants:
            with self.subTest(raw=changed[:80]), self.assertRaises(pc.Refusal):
                no.parse_host_dependencies(changed, EXE)

    def testEachArchitectureRequiresExactSystemAndUniqueRecords(self):
        for rows in ([], [record('/usr/lib/libSystem.B.dylib.extra')], [record(SYSTEM)]*2):
            for arch in ('arm64', 'x86_64'):
                sections = [(a, rows if a == arch else [record(SYSTEM)]) for a in ('arm64', 'x86_64')]
                with self.assertRaises(pc.Refusal): no.parse_host_dependencies(output(sections), EXE)

    def testForbiddenInstallNamesRefuseInEveryArchitecture(self):
        names = ['@rpath/OwnedFolderProbe.debug.dylib', '@loader_path/__preview.dylib',
                 '@executable_path/OwnedFolderProbe.debug.dylib', '@rpath/libswiftCore.dylib',
                 '/usr/lib/OwnedFolderProbe.debug.dylib', '/usr/lib/__preview.dylib',
                 '/System/Library/Frameworks/X.framework/__preview.dylib',
                 '/usr/lib/../outside.dylib', '/usr/lib/./libX.dylib', '/usr/lib//libX.dylib',
                 '/usr/lib/.hidden', '/usr/lib/libX.dylib/', '/usr/library/libX.dylib',
                 '/Library/Frameworks/X.framework/X', '/System/Library/PrivateFrameworks/X.framework/X',
                 ROOT+'/Debug/OwnedFolderProbe.app/Contents/MacOS/OwnedFolderProbe.debug.dylib',
                 'libX.dylib', '/usr/lib/name with spaces', '/usr/lib/x\\y', '/usr/lib/x\0y',
                 '/usr/lib/é.dylib', '/usr/lib/'+'x'*129]
        for name in names:
            for arch in ('arm64', 'x86_64'):
                sections = [(a, [record(SYSTEM)]+([record(name)] if a == arch else [])) for a in ('arm64','x86_64')]
                with self.subTest(name=name, arch=arch), self.assertRaises(pc.Refusal):
                    no.parse_host_dependencies(output(sections), EXE)

    def testFullRecordVersionQualifierAndEncodingRefusals(self):
        raw = output()
        variants = [raw[:-1], raw+b'\n', raw+b'warning\n', raw.replace(b'\n', b'\r\n'),
                    raw.replace(b'\t', b' '), raw.replace(b'1.0.0', b'01.0.0'),
                    raw.replace(b'65535.255.255', b'65536.255.255'),
                    raw.replace(b'65535.255.255', b'65535.256.255'),
                    raw.replace(b'65535.255.255', b'65535.255.256'),
                    raw.replace(b'65535.255.255)', b'65535.255.255, normal)'),
                    raw.replace(b'65535.255.255)', b'65535.255.255, weak, lazy)'),
                    raw.replace(b'current version', b'current versions'), b'\xff'+raw,
                    raw.decode(), None, b'']
        for changed in variants:
            with self.subTest(kind=type(changed).__name__), self.assertRaises(pc.Refusal):
                no.parse_host_dependencies(changed, EXE)

    def testSixtyFourRecordsPerArchitectureAndOverLimitRefusal(self):
        rows = [record(SYSTEM)]+[record('/usr/lib/libFixture'+str(i)+'.dylib') for i in range(63)]
        self.assertEqual(len(no.parse_host_dependencies(output([('arm64', rows), ('x86_64', rows)]), EXE)[0][1]), 64)
        for arch in ('arm64', 'x86_64'):
            sections = [(a, rows+([record('/usr/lib/libExtra.dylib')] if a == arch else [])) for a in ('arm64','x86_64')]
            with self.assertRaises(pc.Refusal): no.parse_host_dependencies(output(sections), EXE)
        with self.assertRaises(pc.Refusal): no.parse_host_dependencies(b'x'*65537, EXE)
        with self.assertRaises(pc.Refusal): no.parse_host_dependencies(b'x'*1025+b'\n'+output(), EXE)

    def testFixedToolLeafIdentityAndRefusals(self):
        with patch.object(no.os, 'lstat', return_value=tool_stat()) as probe:
            self.assertEqual(no.inspector_identity(), IDENTITY)
            probe.assert_called_once_with(no.OTOOL)
        for values in (dict(st_mode=stat.S_IFLNK|0o755), dict(st_mode=stat.S_IFDIR|0o755),
                       dict(st_mode=stat.S_IFREG|0o644), dict(st_mode=stat.S_IFREG|0o775),
                       dict(st_mode=stat.S_IFREG|0o757), dict(st_uid=501),
                       dict(st_size=0), dict(st_size=64*1024*1024+1)):
            with patch.object(no.os, 'lstat', return_value=tool_stat(**values)), self.assertRaises(pc.Refusal):
                no.inspector_identity()
        with patch.object(no.os, 'lstat', side_effect=FileNotFoundError), self.assertRaises(FileNotFoundError):
            no.inspector_identity()

    def testExactStaticCallAndRetirementResultRequired(self):
        tool = Mock(return_value=result(ARGS, output()))
        with patch.object(no, 'inspector_identity', return_value=IDENTITY) as identity:
            parsed = no.inspect_host_dependencies(tool, ROOT, IDENTITY)
        self.assertEqual(len(parsed), 2); self.assertEqual(identity.call_count, 2)
        tool.assert_called_once_with(ARGS, timeout=20, max_output=65536)
        for changed in (dict(returncode=1), dict(stderr=b'warning'), dict(direct_child_reaped=False),
                        dict(owned_group_retired=False), dict(cancelled=True), dict(reason='tool-deadline'),
                        dict(arguments=(no.OTOOL, '-L', EXE)), dict(stdout=output()[:-1])):
            tool = Mock(return_value=replace(result(ARGS, output()), **changed))
            with patch.object(no, 'inspector_identity', return_value=IDENTITY), self.assertRaises(pc.Refusal):
                no.inspect_host_dependencies(tool, ROOT, IDENTITY)
            self.assertEqual(tool.call_count, 1)

    def testToolMutationBeforeAndAfterNeverRetries(self):
        changed = IDENTITY[:-1]+(5,)
        for states, expected_calls in (([changed],0), ([IDENTITY,changed],1)):
            tool = Mock(return_value=result(ARGS, output()))
            with patch.object(no, 'inspector_identity', side_effect=states), self.assertRaises(pc.Refusal):
                no.inspect_host_dependencies(tool, ROOT, IDENTITY)
            self.assertEqual(tool.call_count, expected_calls)

    def testMonolithicInventoryRequiresExactlyDirectoryAndExecutable(self):
        folder = no.PRODUCTS[0]+'/Contents/MacOS'; exe = no.EXECUTABLES[0]
        good = {folder:{'kind':'directory'},exe:{'kind':'file','size':100}}
        no.require_monolithic_host_inventory(good)
        variants = [{exe:good[exe]}, {folder:good[folder]}]
        for leaf, kind in (('OwnedFolderProbe.debug.dylib','file'), ('__preview.dylib','file'),
                           ('other','file'), ('other','directory'), ('other','symlink')):
            variants.append({**good,folder+'/'+leaf:{'kind':kind,'size':100}})
        for values in ({'kind':'symlink','size':100},{'kind':'directory','size':100},
                       {'kind':'file','size':0},{'kind':'file','size':True}):
            variants.append({**good,exe:values})
        for changed in variants:
            with self.assertRaises(pc.Refusal): no.require_monolithic_host_inventory(changed)


    def testPrimaryDerivedFixedFixtureAndRecordedProvenance(self):
        here = Path(__file__).parent
        raw = (here/'otool-system.example.txt').read_bytes()
        provenance = json.loads((here/'otool-system.provenance.json').read_bytes())
        self.assertEqual(hashlib.sha256(raw).hexdigest(), provenance['fixture_sha256'])
        self.assertEqual(provenance['kind'], 'synthetic assembly from primary formatter grammar; not runner output')
        parsed = no.parse_host_dependencies(raw, EXE)
        self.assertEqual([row[3] for row in parsed[0][1]], ['normal','weak','reexport','upward','lazy'])
        self.assertEqual(parsed[1][1][1][0], '/System/Library/Frameworks/AppKit.framework/Versions/C/AppKit')
        self.assertTrue(all('e0d56624eca2a76c2ace4c21850df9e666de4ca5' in row['url'] for row in provenance['sources']))

    def testExactByteAndInstallNameBoundsHavePositiveControls(self):
        def name(size, index):
            prefix = '/usr/lib/f'+str(index)+'/'
            remaining = size-len(prefix)
            parts = []
            while remaining > 128:
                parts.append('a'*127); remaining -= 128
            parts.append('b'*remaining)
            return prefix+'/'.join(parts)
        self.assertEqual(len(name(512,0)), 512)
        self.assertTrue(no._install_name(name(512,0)))
        self.assertFalse(no._install_name(name(513,0)))
        # Use 126 independently named variable-length records plus libSystem
        # in each architecture. Every other grammar/count bound remains valid.
        sizes = [16]*126
        def packed():
            rows = [record(name(size,i)) for i,size in enumerate(sizes)]
            return output([('arm64',[record(SYSTEM)]+rows[:63]),('x86_64',[record(SYSTEM)]+rows[63:])])
        remaining = 65536-len(packed())
        for i in range(len(sizes)):
            amount = min(512-sizes[i],remaining);sizes[i]+=amount;remaining-=amount
        self.assertEqual(remaining,0)
        raw=packed();self.assertEqual(len(raw),65536)
        self.assertEqual(len(no.parse_host_dependencies(raw,EXE)[1][1]),64)
        index=next(i for i,size in enumerate(sizes) if size<512)
        sizes[index]+=1;raw=packed();self.assertEqual(len(raw),65537)
        with self.assertRaisesRegex(pc.Refusal,'output bounds'):no.parse_host_dependencies(raw,EXE)

    def testExpectedOwnedFilenameAndEachToolIdentityFieldAreExact(self):
        for exe in (EXE+'/',EXE.replace('/private/tmp/','/tmp/'),EXE.replace('OwnedFolderProbe','Other'),
                    EXE+'\n',EXE.encode(),None):
            with self.assertRaises(pc.Refusal):no.parse_host_dependencies(output(),exe)
        for index in range(len(IDENTITY)):
            changed=list(IDENTITY);changed[index]+=1
            tool=Mock(return_value=result(ARGS,output()))
            with patch.object(no,'inspector_identity',return_value=tuple(changed)),self.assertRaises(pc.Refusal):
                no.inspect_host_dependencies(tool,ROOT,IDENTITY)
            tool.assert_not_called()


if __name__ == '__main__':
    unittest.main()
