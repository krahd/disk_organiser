"""Pure generated-source oracles. No fixture creation, signing or launch."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import fixture_inputs as fi
import probe_contract as pc


class ClaimedInputTests(unittest.TestCase):
    def setUp(self):
        self.value = json.loads((Path(__file__).parent / "fixture-claim.example.json").read_bytes())
        for key in ("fixtureParent", "selectedPath", "selectedFile", "siblingFile", "absentPath"):
            self.value[key] = self.value[key].replace("/owned-fixture-placeholder", "/private/tmp/disk-selection-owned-synthetic")
        self.raw = json.dumps(self.value, separators=(",", ":")).encode()
        self.capture_identity = {"device": 1, "inode": 9}
        self.executable = "/private/tmp/disk-selection-build-synthetic/Products/Debug/OwnedFolderProbe.app/Contents/MacOS/OwnedFolderProbe"

    def testExactClaimBytesAndIdentityProduceOnlyThreeInputs(self):
        result = fi.render_claimed_inputs(self.raw, "a" * 40, self.executable, self.capture_identity)
        self.assertEqual(set(result), {"Generated/ProbeSeal.swift", "Generated/fixture.json", "Generated/ProbeBuild.xcconfig"})
        self.assertEqual(result["Generated/fixture.json"], self.raw)
        self.assertIn(hashlib.sha256(self.raw).hexdigest().encode(), result["Generated/ProbeSeal.swift"])
        self.assertEqual(result["Generated/ProbeBuild.xcconfig"], ("OWNED_PROBE_IDENTIFIER = " + self.value["bundleIdentifier"] + "\n").encode())
        self.assertNotIn(b"ENTITLEMENTS", result["Generated/ProbeBuild.xcconfig"])

    def testSourceAndExecutableCoordinatesRefuseBeforeGeneration(self):
        for source in ("", "a" * 39, "A" * 40, "a" * 40 + '\\(injection)'):
            with self.assertRaises(pc.Refusal):
                fi.render_claimed_inputs(self.raw, source, self.executable, self.capture_identity)
        for executable in ("/usr/bin/other", self.executable + '"', self.executable.replace("-synthetic", "-../other"),
                           self.executable.replace("-synthetic", "-é"), self.executable.replace("Debug", "Release")):
            with self.assertRaises(pc.Refusal):
                fi.render_claimed_inputs(self.raw, "a" * 40, executable, self.capture_identity)

    def testNoncanonicalFixtureCoordinatesRefuse(self):
        for replacement in ("/other-owned", "/private/tmp/disk-selection-owned-a/b", "/private/tmp/disk-selection-owned-é"):
            value = deepcopy(self.value)
            for key in ("fixtureParent", "selectedPath", "selectedFile", "siblingFile", "absentPath"):
                value[key] = value[key].replace("/private/tmp/disk-selection-owned-synthetic", replacement)
            with self.assertRaises(pc.Refusal):
                fi.render_claimed_inputs(json.dumps(value).encode(), "a" * 40, self.executable, self.capture_identity)

    def testDuplicateOrOversizedClaimDoesNotBecomeGeneratedTrust(self):
        duplicate = self.raw.replace(b'{', b'{"schemaVersion":1,', 1)
        for raw in (duplicate, b" " * (pc.FIXTURE_BYTES + 1)):
            with self.assertRaises(pc.Refusal):
                fi.render_claimed_inputs(raw, "a" * 40, self.executable, self.capture_identity)

    def testMemoryGenerationCallsNoFixtureOrFilesystemCapability(self):
        with patch.object(fi, "create_owned_fixture") as create, patch.object(fi.os, "open") as opened, \
             patch.object(fi.tempfile, "mkdtemp") as mkdir:
            fi.render_claimed_inputs(self.raw, "a" * 40, self.executable, self.capture_identity)
            create.assert_not_called(); opened.assert_not_called(); mkdir.assert_not_called()

    def testChangedClaimBytesChangeTheSealedHashWithoutObservationClaim(self):
        first = fi.render_claimed_inputs(self.raw, "a" * 40, self.executable, self.capture_identity)
        second = fi.render_claimed_inputs(self.raw + b" ", "a" * 40, self.executable, self.capture_identity)
        self.assertNotEqual(first["Generated/ProbeSeal.swift"], second["Generated/ProbeSeal.swift"])
        self.assertNotIn(b"observed", second["Generated/ProbeSeal.swift"])


if __name__ == "__main__":
    unittest.main()
