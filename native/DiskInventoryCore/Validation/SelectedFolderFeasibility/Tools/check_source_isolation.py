"""Read repository source only. These checks are not Xcode/Swift validation."""
from pathlib import Path
import ast
import json
import plistlib
import re
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parents[1]
PACKAGE = HERE.parents[1]
REPO = PACKAGE.parents[1]
checks = []

def require(value, name):
    if not value:
        raise AssertionError(name)
    checks.append(name)

project = (HERE / "Probe.xcodeproj/project.pbxproj").read_text()
require(project.count("isa = PBXNativeTarget;") == 2, "two isolated native targets")
references = re.findall(r'isa = PBXFileReference; lastKnownFileType = [^;]+; path = "([^"]+)";', project)
require(len(references) == len(set(references)) and all((HERE / p).is_file() for p in references), "all project source references exist exactly once")
require(set(p for p in references if p.endswith('.swift')) == {str(p.relative_to(HERE)) for folder in ('Host', 'UITests', 'Generated') for p in (HERE / folder).glob('*.swift')}, "all and only probe Swift files referenced")
require(project.count("CODE_SIGNING_ALLOWED = NO;") == 6 and "CODE_SIGNING_ALLOWED = YES" not in project,
        "all configurations disable signing")
require(project.count("ENABLE_APP_SANDBOX = NO;") == 6 and project.count('CODE_SIGN_ENTITLEMENTS = "$(OWNED_PROBE_HOST_ENTITLEMENTS)";') == 2,
        "sandbox and entitlement activation remain disabled")
require("OWNED_PROBE_HOST_ENTITLEMENTS =\n" in (HERE / "Generated/ProbeBuild.xcconfig").read_text(), "empty default entitlement setting")
entitlements = plistlib.loads((HERE / "Host/host.entitlements.inert.plist").read_bytes())
require(entitlements == {"com.apple.security.app-sandbox": True, "com.apple.security.files.user-selected.read-only": True}, "exact inactive two-entitlement template")
seal = (HERE / "Generated/ProbeSeal.swift").read_text()
require(seal.count('"UNSEALED"') == 5 and json.loads((HERE / "Generated/fixture.json").read_bytes()) == {"unsealed": True}, "default seal refuses real inputs")
scheme = ET.parse(HERE / "Probe.xcodeproj/xcshareddata/xcschemes/OwnedFolderProbe.xcscheme").getroot()
require(scheme.find("LaunchAction") is None and scheme.find("ArchiveAction") is None and
        all(x.attrib.get('buildForRunning') == 'NO' and x.attrib.get('buildForArchiving') == 'NO' for x in scheme.findall('.//BuildActionEntry')), "test-only scheme has no run/archive action")
require(scheme.find('.//TestableReference').attrib == {"skipped": "NO", "parallelizable": "NO"}, "three UI cases run serially if separately activated")
ui = (HERE / 'UITests/SelectionProbeUITests.swift').read_text()
require(re.findall(r'func (test\w+)\(', ui) == ['testSelectedReadSucceedsOnlyDuringScope', 'testGenuinePanelCancellationRetiresWithoutSelection', 'testActiveReadCancelRetiresBeforeRetry'], "exact three authored UI identities")
package = (PACKAGE / 'Package.swift').read_text()
require('SelectedFolderFeasibility' not in package and 'OwnedFolderProbe' not in package, "no SwiftPM probe target")
workflows = list((REPO / '.github/workflows').glob('*.yml'))
require(bool(workflows) and all('SelectedFolderFeasibility' not in p.read_text() and 'OwnedFolderProbe' not in p.read_text() for p in workflows), "no workflow probe invocation")
identity = (HERE / 'Host/HostIdentity.swift').read_text()
require('SecCodeGetStatus' not in identity and 'SecCodeCheckValidity' in identity and 'runningValidityChecked' in identity,
        "public running-validity observation without private status API")
controller_tree = ast.parse((HERE / 'Tools/experiment_controller.py').read_bytes())
gates = [node for node in controller_tree.body if isinstance(node, ast.FunctionDef) and node.name in ('_stage_b_approved', '_stage_c_approved')]
require(len(gates) == 2 and all(len(node.body) == 1 and isinstance(node.body[0], ast.Return) and
        isinstance(node.body[0].value, ast.Constant) and node.body[0].value.value is False for node in gates),
        "both operational controller gates remain closed")
require('ProbePolicy.completedOutcome(cancelAccepted: stopping)' in (HERE / 'Host/ProbeController.swift').read_text(),
        "visible cancellation consulted before queued success publication")
expectation = (HERE / 'UITests/RunnerExpectation.swift').read_text()
require('OWNED_PROBE_EXPECT_' in expectation and 'requireIdentity' in expectation and
        ui.index('ProbeFixture.loadForRunner(expectedCDHash:') < ui.index('app.launch()') <
        ui.index('expectedIdentity.requireIdentity(try XCTUnwrap(launchedIdentity), running: true)') < ui.index('private func chooseFixture'),
        "static and actual guest expectation gates precede panel helpers")
require('app.launchEnvironment = [:]' in ui and 'RunnerExpectation.swift' in project and
        'RunnerExpectation.swift' not in (HERE / 'Host/main.swift').read_text(),
        "runner comparison data is not an ordinary host environment switch")
for path in sorted((HERE / 'Tools').glob('*.py')):
    ast.parse(path.read_bytes(), filename=str(path))
require(True, "all Python sources parse without importing operational functions")
print(json.dumps({"source_checks_passed": len(checks), "checks": checks, "native_execution": False}, indent=2))
