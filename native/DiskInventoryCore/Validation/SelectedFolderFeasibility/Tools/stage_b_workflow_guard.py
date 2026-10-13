"""Source-only guard for the reviewed native lane's explicit local closure.

The baseline pins nine existing workflow YAML files and the known native-lane
helpers/local imports. Ordinary native .swift/.py/.cjs paths are autodiscovered.
This is not generic dynamic caller inference or an OS-security boundary.
"""
import hashlib
import json
from pathlib import Path

WORKFLOW = '.github/workflows/owned-selected-folder-build.yml'
STARTUP_WORKFLOW = '.github/workflows/owned-startup-key-observation.yml'
NATIVE = 'native/DiskInventoryCore/'
QUARANTINE = NATIVE + 'Validation/SelectedFolderFeasibility/'


def ordinary_native_source(path):
    """Exclude only the exact isolated subtree, never a similar name elsewhere."""
    return (path.startswith(NATIVE) and not path.startswith(QUARANTINE) and
            path.endswith(('.swift', '.py', '.cjs')))


def validate(files, baseline, template, enabled, startup_template=None):
    if type(enabled) is not bool or type(files) is not dict or type(baseline) is not dict:
        raise AssertionError('guard inputs')
    workflows = {path for path in files if path.startswith('.github/workflows/') and path.endswith(('.yml', '.yaml'))}
    expected = {path for path in baseline if path.startswith('.github/workflows/')}
    startup_active = STARTUP_WORKFLOW in files
    if startup_active and (enabled or type(startup_template) is not bytes or
                           not 0 < len(startup_template) <= 16384 or
                           files[STARTUP_WORKFLOW] != startup_template):
        raise AssertionError('only exact startup observation with build disabled')
    if workflows != expected | ({WORKFLOW} if enabled else set()) | ({STARTUP_WORKFLOW} if startup_active else set()):
        raise AssertionError('only exact designated workflow may be active')
    if ({path for path in files if ordinary_native_source(path)} !=
            {path for path in baseline if ordinary_native_source(path)}):
        raise AssertionError('ordinary native source graph changed')
    for path, digest in baseline.items():
        if path not in files or hashlib.sha256(files[path]).hexdigest() != digest:
            raise AssertionError('ordinary workflow/helper changed:' + path)
    # The template is reviewed as a complete byte sequence. Its parsed semantic
    # restrictions are tested separately; activation cannot swap steps/callers.
    if enabled and files[WORKFLOW] != template:
        raise AssertionError('active build-only workflow differs from reviewed template')
    if not enabled and WORKFLOW in files:
        raise AssertionError('disabled build-only workflow present')
    return True


def check(repo, enabled):
    probe = repo / 'native/DiskInventoryCore/Validation/SelectedFolderFeasibility'
    baseline = json.loads((probe/'StageB/workflow-baseline.json').read_bytes())
    files = {path: (repo/path).read_bytes() for path in baseline}
    for path in (repo/'.github/workflows').rglob('*'):
        if path.is_file() and path.suffix in ('.yml', '.yaml'):
            files[str(path.relative_to(repo))] = path.read_bytes()
    for path in (repo/'native/DiskInventoryCore').rglob('*'):
        relative = str(path.relative_to(repo))
        if path.is_file() and ordinary_native_source(relative):
            files[relative] = path.read_bytes()
    startup = ((probe/'StageB/owned-startup-key-observation.yml.inert').read_bytes()
               if STARTUP_WORKFLOW in files else None)
    return validate(files, baseline, (probe/'StageB/owned-selected-folder-build.environment-diagnostic.yml.inert').read_bytes(),
                    enabled, startup_template=startup)
