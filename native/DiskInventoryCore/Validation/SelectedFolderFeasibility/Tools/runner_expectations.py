"""Pure exact derivation of comparison data for the isolated UI runner.

These strings neither create an owned capability nor approve any action. The
original emitted configuration remains retained; Stage C writes neither file.
"""
from dataclasses import dataclass
import plistlib
import re

import probe_contract as pc
import xctestrun_binding as xb

PREFIX = 'OWNED_PROBE_EXPECT_'
FIELDS = ('CDHASH', 'IDENTIFIER', 'EXECUTABLE', 'SOURCE_COMMIT', 'FIXTURE_SHA256', 'FIXTURE_RUN_ID', 'FIXTURE_CASE_ID')
KEYS = frozenset(PREFIX + name for name in FIELDS)
DERIVED_NAME = 'OwnedProbeBound.xctestrun'


@dataclass(frozen=True)
class Derivation:
    original_name: str
    original: xb.ParsedConfiguration
    derived_name: str
    derived: xb.ParsedConfiguration
    expectations: tuple[tuple[str, str], ...]


def validate(expectations):
    pc.require(type(expectations) is dict and set(expectations) == KEYS, 'exact runner expectations')
    pc.require(all(type(value) is str for value in expectations.values()), 'runner expectation strings')
    values = {name: expectations[PREFIX + name] for name in FIELDS}
    pc.require(re.fullmatch(r'[0-9a-f]{40,128}', values['CDHASH']) and len(values['CDHASH']) % 2 == 0,
               'runner CDHash expectation')
    pc.require(re.fullmatch(r'[0-9a-f]{40}', values['SOURCE_COMMIT']) and
               re.fullmatch(r'[0-9a-f]{64}', values['FIXTURE_SHA256']), 'runner source/fixture expectation')
    for name in ('FIXTURE_RUN_ID', 'FIXTURE_CASE_ID'):
        pc.require(re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', values[name]),
                   'runner fixture UUID expectation')
    pc.require(values['IDENTIFIER'] == pc.BUNDLE_PREFIX + values['FIXTURE_CASE_ID'], 'runner identifier expectation')
    path = values['EXECUTABLE']
    pc.require(path.startswith('/private/tmp/disk-selection-build-') and len(path.encode()) <= 1024 and
               path.endswith('/Products/Debug/OwnedFolderProbe.app/Contents/MacOS/OwnedFolderProbe') and
               re.fullmatch(r'[A-Za-z0-9_./-]+', path) and all(p not in ('', '.', '..') for p in path.split('/')[1:]),
               'runner executable expectation')
    return tuple(sorted(expectations.items()))


def derive(original_name, original_raw, expectations):
    pc.require(type(original_name) is str and 0 < len(original_name.encode()) <= 255 and
               original_name.endswith('.xctestrun') and '/' not in original_name and '\\' not in original_name and
               original_name != DERIVED_NAME, 'distinct original configuration leaf')
    admitted = validate(expectations)
    original = xb.parse(original_raw)
    tree = xb.decode_xml(original_raw)
    target = tree['TestConfigurations'][0]['TestTargets'][0]
    for field in ('EnvironmentVariables', 'TestingEnvironmentVariables'):
        pc.require(not any(key.startswith(PREFIX) for key in target[field]), 'reserved runner expectation collision')
    pc.require(target['UITargetAppBundleIdentifier'] == expectations[PREFIX + 'IDENTIFIER'], 'derived target identifier')
    # Only this runner dictionary is augmented. Host launchEnvironment remains
    # explicitly empty in the UI source. Actual Xcode propagation is untested.
    target['EnvironmentVariables'].update(dict(admitted))
    derived_raw = plistlib.dumps(tree, fmt=plistlib.FMT_XML, sort_keys=False)
    derived = xb.parse(derived_raw)
    result = Derivation(original_name, original, DERIVED_NAME, derived, admitted)
    verify(result, original_raw, derived_raw, expectations)
    return result


def verify(binding, original_raw, derived_raw, expectations):
    pc.require(type(binding) is Derivation and binding.derived_name == DERIVED_NAME and
               binding.original_name != DERIVED_NAME, 'retained runner derivation')
    admitted = validate(expectations)
    pc.require(binding.expectations == admitted and xb.parse(original_raw) == binding.original and
               xb.parse(derived_raw) == binding.derived, 'runner derivation bytes/expectations changed')
    original = xb.decode_xml(original_raw); derived = xb.decode_xml(derived_raw)
    old = original['TestConfigurations'][0]['TestTargets'][0]
    new = derived['TestConfigurations'][0]['TestTargets'][0]
    for field in ('EnvironmentVariables', 'TestingEnvironmentVariables'):
        pc.require(not any(key.startswith(PREFIX) for key in old[field]), 'original reserved-key collision')
    pc.require({key for key in new['EnvironmentVariables'] if key.startswith(PREFIX)} == KEYS and
               not any(key.startswith(PREFIX) for key in new['TestingEnvironmentVariables']), 'derived reserved-key set')
    pc.require({key: new['EnvironmentVariables'].pop(key) for key in KEYS} == dict(admitted), 'derived expectation values')
    pc.require(derived == original, 'non-expectation configuration changed')
    return binding
