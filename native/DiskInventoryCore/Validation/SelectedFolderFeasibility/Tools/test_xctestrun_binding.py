"""Synthetic, memory-only parser/whole-configuration oracles; no Xcode run."""
from copy import deepcopy
import plistlib
import unittest

import probe_contract as pc
import xctestrun_binding as xb

PRODUCTS = ("OwnedFolderProbe.app", "SelectionProbeUITests-Runner.app",
            "SelectionProbeUITests-Runner.app/Contents/PlugIns/SelectionProbeUITests.xctest")


def example():
    return {"__xctestrun_metadata__": {"FormatVersion": 2}, "TestConfigurations": [{
        "Name": "Owned probe", "IsEnabled": True, "TestTargets": [{
            "BlueprintName": "SelectionProbeUITests", "IsUITestBundle": True,
            "TestBundlePath": "__TESTHOST__/Contents/PlugIns/SelectionProbeUITests.xctest",
            "TestHostPath": "__TESTROOT__/" + PRODUCTS[1],
            "UITargetAppPath": "__TESTROOT__/" + PRODUCTS[0],
            "UITargetAppBundleIdentifier": "org.diskorganiser.owned-selection-probe.synthetic",
            "OnlyTestIdentifiers": list(xb.METHODS), "SkipTestIdentifiers": [],
            "CommandLineArguments": [], "EnvironmentVariables": {"OWNED_MARKER": "one"},
            "TestingEnvironmentVariables": {"OWNED_RUNNER_MARKER": "two"},
        }]}]}


def encoded(value):
    return plistlib.dumps(value, fmt=plistlib.FMT_XML, sort_keys=False)


class XctestrunBindingTests(unittest.TestCase):
    def setUp(self):
        self.value = example()
        self.raw = encoded(self.value)
        self.expected = xb.parse(self.raw)
        xb.bind(self.expected, self.raw, PRODUCTS)

    def testExactRawAndFullTreeAreRetained(self):
        self.assertEqual(self.expected.raw, self.raw)
        self.assertIn(b'"OWNED_RUNNER_MARKER":"two"', self.expected.complete_tree)
        self.assertEqual(xb.decode_xml(self.raw), self.value)

    def testChangedHostOrRunnerOrBundleCannotUseStaleExpected(self):
        for field in ["UITargetAppPath", "TestHostPath", "TestBundlePath"]:
            value = deepcopy(self.value)
            value["TestConfigurations"][0]["TestTargets"][0][field] += "changed"
            candidate = encoded(value)
            xb.parse(candidate)  # Positive schema admission before equality refusal.
            with self.assertRaisesRegex(pc.Refusal, "configuration changed"):
                xb.bind(self.expected, candidate, PRODUCTS)

    def testBothCompleteEnvironmentsAreBound(self):
        for field in ["EnvironmentVariables", "TestingEnvironmentVariables"]:
            for mutate in [lambda env: env.update(NEW_KEY="three"),
                           lambda env: env.update({next(iter(env)): "changed"}),
                           lambda env: env.clear()]:
                value = deepcopy(self.value)
                mutate(value["TestConfigurations"][0]["TestTargets"][0][field])
                candidate = encoded(value)
                xb.parse(candidate)
                with self.assertRaisesRegex(pc.Refusal, "configuration changed"):
                    xb.bind(self.expected, candidate, PRODUCTS)

    def testWhitespaceOnlyRawMutationStillRefuses(self):
        candidate = self.raw.replace(b"<dict>", b"<dict>\n", 1)
        self.assertEqual(xb.decode_xml(candidate), self.value)
        with self.assertRaisesRegex(pc.Refusal, "configuration changed"):
            xb.bind(self.expected, candidate, PRODUCTS)

    def testUnknownFieldAtEverySemanticLevelRefuses(self):
        for location in [(), ("__xctestrun_metadata__",), ("TestConfigurations", 0),
                         ("TestConfigurations", 0, "TestTargets", 0)]:
            value = deepcopy(self.value)
            selected = value
            for key in location:
                selected = selected[key]
            selected["UnreviewedNewField"] = "never ignored"
            with self.assertRaises(pc.Refusal):
                xb.parse(encoded(value))

    def testDuplicateKeysRefuseBeforeDictionaryCollapse(self):
        candidate = self.raw.replace(b"<key>FormatVersion</key>",
                                     b"<key>FormatVersion</key><integer>2</integer><key>FormatVersion</key>")
        with self.assertRaisesRegex(pc.Refusal, "duplicate plist key"):
            xb.parse(candidate)

    def testMethodOmissionReorderingAndSkippingRefuse(self):
        for field, items in [("OnlyTestIdentifiers", list(reversed(xb.METHODS))),
                             ("OnlyTestIdentifiers", list(xb.METHODS[:2])),
                             ("SkipTestIdentifiers", [xb.METHODS[0]])]:
            value = deepcopy(self.value)
            value["TestConfigurations"][0]["TestTargets"][0][field] = items
            with self.assertRaisesRegex(pc.Refusal, "exact three UI methods"):
                xb.parse(encoded(value))

    def testBooleanIntegerConfusionAndDisabledConfigurationRefuse(self):
        value = deepcopy(self.value)
        value["__xctestrun_metadata__"]["FormatVersion"] = True
        with self.assertRaises(pc.Refusal):
            xb.parse(encoded(value))
        for item in [1, False]:
            value = deepcopy(self.value)
            value["TestConfigurations"][0]["IsEnabled"] = item
            with self.assertRaises(pc.Refusal):
                xb.parse(encoded(value))

    def testEntityAndUnsupportedBinaryRefuse(self):
        with self.assertRaisesRegex(pc.Refusal, "unsupported binary"):
            xb.parse(plistlib.dumps(self.value, fmt=plistlib.FMT_BINARY))
        payload = b'<!DOCTYPE plist [<!ENTITY e "expand">]><plist version="1.0"><dict><key>k</key><string>&e;</string></dict></plist>'
        with self.assertRaises(pc.Refusal):
            xb.decode_xml(payload)

    def testPairedByteAndStructureBudgets(self):
        padded = self.raw + b" " * (xb.MAX_BYTES - len(self.raw))
        self.assertEqual(xb.parse(padded).complete_tree, self.expected.complete_tree)
        with self.assertRaisesRegex(pc.Refusal, "byte budget"):
            xb.parse(padded + b" ")
        def nested(depth):
            return b'<plist version="1.0"><dict><key>x</key>' + b'<array>' * depth + b'<string>x</string>' + b'</array>' * depth + b'</dict></plist>'
        xb.decode_xml(nested(13))  # plist + dict + thirteen arrays + string = 16.
        with self.assertRaisesRegex(pc.Refusal, "structure budget"):
            xb.decode_xml(nested(14))

    def testResolvedProductsRejectEscapeAndDifferentHost(self):
        for products in [("../escape.app", *PRODUCTS[1:]), ("Different.app", *PRODUCTS[1:]),
                         (PRODUCTS[0], PRODUCTS[1], "Elsewhere/Test.xctest")]:
            with self.assertRaises(pc.Refusal):
                xb.bind(self.expected, self.raw, products)

    def testMalformedNodesAndInvalidUTF8Refuse(self):
        for payload in [b"\xff", b'<plist version="1.0"><dict><string>key</string><string>value</string></dict></plist>',
                        b'<plist version="1.0"><dict><key>x</key><real>1</real></dict></plist>']:
            with self.assertRaises(pc.Refusal):
                xb.decode_xml(payload)

    def testDeclaredEncodingMatchesStrictUTF8Bytes(self):
        self.value["TestConfigurations"][0]["TestTargets"][0]["EnvironmentVariables"]["UNICODE"] = "é"
        raw = encoded(self.value)
        actual = xb.parse(raw)
        self.assertIn("é".encode(), actual.complete_tree)
        for encoding in (b"ISO-8859-1", b"UTF-16", b"unknown-encoding"):
            with self.assertRaisesRegex(pc.Refusal, "unsupported XML declaration"):
                xb.parse(raw.replace(b'encoding="UTF-8"', b'encoding="' + encoding + b'"'))
        with self.assertRaises(pc.Refusal):
            xb.parse(raw.replace(b'version="1.0" encoding', b'version="1.1" encoding', 1))
        with self.assertRaisesRegex(pc.Refusal, "UTF-8 required"):
            xb.parse(raw.replace("é".encode(), b"\xff"))


if __name__ == "__main__":
    unittest.main()
