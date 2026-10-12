"""Mocked descriptor/controller checks only. No root/fixture is created."""
from unittest.mock import patch, Mock
from types import SimpleNamespace
import errno
import json
from copy import deepcopy
import os
import stat
import unittest

import owned_build_observation as ob
import probe_contract as pc
import xctestrun_binding as xb
from test_xctestrun_binding import example, encoded

PRODUCTS = ("Debug/OwnedFolderProbe.app", "Debug/SelectionProbeUITests-Runner.app",
            "Debug/SelectionProbeUITests-Runner.app/Contents/PlugIns/SelectionProbeUITests.xctest")
CASE = "22222222-2222-4222-8222-222222222222"
ROOT = "/private/tmp/disk-selection-build-synthetic"

def context():
    return {"schemaVersion": 1, "sourceCommit": "a" * 40, "fixtureSHA256": "b" * 64,
            "fixtureRunID": "11111111-1111-4111-8111-111111111111", "fixtureCaseID": CASE,
            "buildRoot": ROOT, "productsRoot": ROOT + "/Products", "workingDirectory": ROOT,
            "executable": "/Applications/Xcode_16.4.app/Contents/Developer/usr/bin/xcodebuild",
            "arguments": ["test-without-building", "-xctestrun", ROOT + "/Products/Owned.xctestrun",
                          "-destination", "platform=macOS", "-parallel-testing-enabled", "NO",
                          "-resultBundlePath", ROOT + "/Results.xcresult"],
            "environment": {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
                            "DEVELOPER_DIR": "/Applications/Xcode_16.4.app/Contents/Developer",
                            "HOME": "/synthetic-home", "TMPDIR": "/synthetic-temp", "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8"},
            "toolchain": {"xcodeVersion": "16.4", "xcodeBuild": "16F6", "sdkVersion": "15.5", "swiftVersion": "6.1.2"},
            "observedHostSignature": {"valid": True, "identifier": pc.BUNDLE_PREFIX + CASE,
                                      "executable": ROOT + "/Products/Debug/OwnedFolderProbe.app/Contents/MacOS/OwnedFolderProbe",
                                      "cdhash": "c" * 40,
                                      "entitlements": {"com.apple.security.app-sandbox": True,
                                                       "com.apple.security.files.user-selected.read-only": True}}}

def context_bytes(value=None):
    return json.dumps(context() if value is None else value, separators=(",", ":")).encode()

def observed_example():
    value = example()
    target = value["TestConfigurations"][0]["TestTargets"][0]
    target["UITargetAppPath"] = "__TESTROOT__/" + PRODUCTS[0]
    target["TestHostPath"] = "__TESTROOT__/" + PRODUCTS[1]
    target["UITargetAppBundleIdentifier"] = pc.BUNDLE_PREFIX + CASE
    return encoded(value)

def mocked_workspace():
    workspace = object.__new__(ob.OwnedBuild)
    workspace.path = ROOT
    workspace._admit = lambda: None
    workspace.read_configuration = Mock(return_value=observed_example())
    workspace.inventory = Mock(return_value=tuple('{"path":"' + p + '","kind":"directory"}' for p in PRODUCTS))
    return workspace



class OwnedBuildSourceTests(unittest.TestCase):
    def testNoReopenFromPathOrClaimConstructor(self):
        with self.assertRaisesRegex(pc.Refusal, "fresh owned build capability"):
            ob.OwnedBuild(object(), "/not-opened", 42, (1, 2))

    def testCloseFailureRetiresAllOnceWithoutRetry(self):
        with patch.object(ob.os, "close", side_effect=[OSError(errno.EINTR, "synthetic"), None]) as close:
            ledger = ob._Descriptors()
            ledger.acquire(lambda: 11); ledger.acquire(lambda: 12)
            with self.assertRaisesRegex(pc.Refusal, "ambiguous descriptor"):
                ledger.finish()
            self.assertEqual([call.args for call in close.call_args_list], [(12,), (11,)])
            self.assertEqual(ledger.owned, [])
            with self.assertRaises(pc.Refusal):
                ledger.finish()
            self.assertEqual(close.call_count, 2)

    def testNonregularAndOversizedConfigurationRefuseBeforeRead(self):
        for mode, size in [(stat.S_IFIFO | 0o600, 0), (stat.S_IFREG | 0o600, xb.MAX_BYTES + 1)]:
            workspace = object.__new__(ob.OwnedBuild)
            workspace._products = lambda ledger: ledger.acquire(lambda: 17)
            value = SimpleNamespace(st_mode=mode, st_nlink=1, st_uid=os.getuid(), st_size=size)
            with patch.object(ob.os, "open", return_value=18) as opened, patch.object(ob.os, "fstat", return_value=value), \
                 patch.object(ob.os, "read") as read, patch.object(ob.os, "close") as close:
                with self.assertRaises(pc.Refusal):
                    workspace.read_configuration("Owned.xctestrun")
                self.assertTrue(opened.call_args.args[1] & os.O_NONBLOCK)
                self.assertTrue(opened.call_args.args[1] & os.O_NOFOLLOW)
                read.assert_not_called()
                self.assertEqual([call.args for call in close.call_args_list], [(18,), (17,)])

    def testChangedConfigurationCannotSealUnderStaleParsedRecord(self):
        workspace = mocked_workspace()
        raw = observed_example()
        workspace.read_configuration = Mock(side_effect=[raw, raw + b" "])
        workspace.inventory = Mock(return_value=tuple('{"path":"' + p + '","kind":"directory"}' for p in PRODUCTS))
        with self.assertRaisesRegex(pc.Refusal, "configuration changed during freeze"):
            ob.freeze(workspace, "Owned.xctestrun", PRODUCTS, context_bytes())

    def testExactFreezeVerificationUsesBothInventoryAndConfiguration(self):
        workspace = mocked_workspace()
        raw = observed_example()
        inventory = tuple('{"path":"' + p + '","kind":"directory"}' for p in PRODUCTS)
        workspace.read_configuration = Mock(return_value=raw)
        workspace.inventory = Mock(return_value=inventory)
        expected = ob.freeze(workspace, "Owned.xctestrun", PRODUCTS, context_bytes())
        ob.verify_unchanged(workspace, expected, "Owned.xctestrun", context_bytes())
        workspace.inventory.return_value = inventory + ('{"path":"extra","kind":"file"}',)
        with self.assertRaisesRegex(pc.Refusal, "observed build changed"):
            ob.verify_unchanged(workspace, expected, "Owned.xctestrun", context_bytes())

    def testDriverContextMutationRefusesTheExistingFreeze(self):
        workspace = mocked_workspace()
        expected = ob.freeze(workspace, "Owned.xctestrun", PRODUCTS, context_bytes())
        for field, value in [("sourceCommit", "d" * 40), ("fixtureSHA256", "e" * 64),
                             ("fixtureRunID", "33333333-3333-4333-8333-333333333333")]:
            changed = context(); changed[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(pc.Refusal, "observed build changed"):
                ob.verify_unchanged(workspace, expected, "Owned.xctestrun", context_bytes(changed))
        for group, field, value in [("environment", "HOME", "/other-home"), ("environment", "TMPDIR", "/other-temp"),
                                    ("observedHostSignature", "cdhash", "d" * 40)]:
            changed = context(); changed[group][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(pc.Refusal, "observed build changed"):
                ob.verify_unchanged(workspace, expected, "Owned.xctestrun", context_bytes(changed))
        with self.assertRaisesRegex(pc.Refusal, "observed build changed"):
            ob.verify_unchanged(workspace, expected, "Owned.xctestrun", context_bytes() + b" ")

    def testDriverContextWrongInvocationEnvironmentToolchainAndSignatureRefuse(self):
        mutations = [lambda x: x.update(workingDirectory="/elsewhere"),
                     lambda x: x.update(executable="/usr/bin/xcodebuild"),
                     lambda x: x["arguments"].append("build"),
                     lambda x: x["environment"].update(INJECT="value"),
                     lambda x: x["toolchain"].update(xcodeVersion="16.5"),
                     lambda x: x["observedHostSignature"].update(valid=1),
                     lambda x: x["observedHostSignature"]["entitlements"].update(extra=True),
                     lambda x: x["observedHostSignature"]["entitlements"].update({"com.apple.security.app-sandbox": 1}),
                     lambda x: x.update(extra=True)]
        for mutation in mutations:
            value = context(); mutation(value)
            with self.assertRaises(pc.Refusal):
                ob.bind_driver_context(mocked_workspace(), "Owned.xctestrun", context_bytes(value))

    def testConfigurationMustMatchObservedSignatureAndFixedProducts(self):
        workspace = mocked_workspace()
        value = example()
        workspace.read_configuration.return_value = encoded(value)
        with self.assertRaisesRegex(pc.Refusal, "identifier mismatch"):
            ob.freeze(workspace, "Owned.xctestrun", PRODUCTS, context_bytes())
        workspace = mocked_workspace()
        with self.assertRaisesRegex(pc.Refusal, "fixed experiment products"):
            ob.freeze(workspace, "Owned.xctestrun", ("other.app",) + PRODUCTS[1:], context_bytes())

    def testProductsReplacementRefusesAndRetiresOpenedDescriptor(self):
        workspace = mocked_workspace(); workspace._descriptor = 10; workspace._products_identity = (1, 2)
        original = SimpleNamespace(st_dev=1, st_ino=2, st_mode=stat.S_IFDIR | 0o700, st_uid=os.getuid())
        replacement = SimpleNamespace(st_dev=1, st_ino=3, st_mode=stat.S_IFDIR | 0o700, st_uid=os.getuid())
        with patch.object(ob.os, "open", return_value=11), patch.object(ob.os, "fstat", return_value=original), \
             patch.object(ob.os, "stat", return_value=replacement), patch.object(ob.os, "close") as close:
            with self.assertRaisesRegex(pc.Refusal, "product directory replaced"), ob._Descriptors() as ledger:
                workspace._products(ledger)
            close.assert_called_once_with(11)


if __name__ == "__main__":
    unittest.main()
