"""Memory-only consistency of two supplied descriptions, never launch authority.

Raw configuration bytes are opaque. This is NOT an xctestrun parser and cannot
prove that the resolved JSON describes those bytes. A later independently
reviewed parser/observer must establish that relation before any real use.
"""
from dataclasses import dataclass
import re

import probe_contract as pc


RAW_BYTES = 1024 * 1024
RESOLVED_BYTES = 64 * 1024
MAX_ITEMS = 128
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
ENV_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
ROOT_FIELDS = {
    "schemaVersion", "rawFormat", "sourceCommit", "fixtureRunID", "fixtureCaseID",
    "fixtureClaimSHA256", "configurationName", "configurationEnabled", "toolchain",
    "destination", "products", "launchArguments", "launchEnvironment",
    "testingEnvironment", "enabledTests", "skippedTests", "instrumentation",
}
INSTRUMENTATION = {
    "codeCoverage", "addressSanitizer", "threadSanitizer",
    "undefinedBehaviorSanitizer", "mainThreadChecker",
}


def _text(value, maximum=1024, empty=False):
    raw = pc.utf8(value)
    pc.require((empty or len(raw) > 0) and len(raw) <= maximum and
               all(ord(c) >= 32 and ord(c) != 127 for c in value), "configuration text")
    return value


def _sequence(value, nonempty=False):
    pc.require(type(value) is list and (not nonempty or bool(value)) and
               len(value) <= MAX_ITEMS, "configuration sequence")
    for item in value:
        _text(item, 4096, empty=True)


def _environment(value):
    pc.require(type(value) is dict and len(value) <= MAX_ITEMS, "configuration environment")
    for key, item in value.items():
        _text(key, 256)
        pc.require(ENV_KEY.fullmatch(key) is not None, "environment key")
        _text(item, 4096, empty=True)


def _validate_resolved(data):
    value = pc.decode_claim(data, RESOLVED_BYTES)
    pc.keys(value, ROOT_FIELDS)
    pc.require(type(value["schemaVersion"]) is int and value["schemaVersion"] == 1,
               "configuration schema")
    pc.require(value["rawFormat"] == "opaque-xctestrun", "unparsed configuration format")
    pc.require(type(value["sourceCommit"]) is str and
               COMMIT.fullmatch(value["sourceCommit"]) is not None, "source commit claim")
    for field in ("fixtureRunID", "fixtureCaseID"):
        pc.require(type(value[field]) is str and pc.UUID.fullmatch(value[field]) is not None,
                   "fixture UUID claim")
    pc.require(type(value["fixtureClaimSHA256"]) is str and
               pc.SHA256.fullmatch(value["fixtureClaimSHA256"]) is not None, "fixture digest claim")
    _text(value["configurationName"], 256)
    pc.require(type(value["configurationEnabled"]) is bool, "configuration enabled type")
    pc.keys(value["toolchain"], {"xcodeVersion", "xcodeBuild", "sdkVersion", "swiftVersion"})
    for item in value["toolchain"].values():
        _text(item, 256)
    _text(value["destination"], 1024)
    pc.keys(value["products"], {"host", "runner", "testBundle"})
    paths = []
    for product in value["products"].values():
        pc.keys(product, {"path", "bundleIdentifier", "inventorySHA256"})
        path = _text(product["path"])
        pc.require(not path.startswith("/") and "\\" not in path and
                   all(p not in ("", ".", "..") for p in path.split("/")), "relative product claim")
        paths.append(path)
        _text(product["bundleIdentifier"], 256)
        pc.require(type(product["inventorySHA256"]) is str and
                   pc.SHA256.fullmatch(product["inventorySHA256"]) is not None, "product digest claim")
    pc.require(len(set(paths)) == 3, "distinct product claims")
    _sequence(value["launchArguments"])
    for field in ("launchEnvironment", "testingEnvironment"):
        _environment(value[field])
    for field in ("enabledTests", "skippedTests"):
        _sequence(value[field], nonempty=field == "enabledTests")
        pc.require(all(value[field]) and len(set(value[field])) == len(value[field]), "test identity claims")
    pc.require(not set(value["enabledTests"]) & set(value["skippedTests"]), "conflicting test claims")
    pc.keys(value["instrumentation"], INSTRUMENTATION)
    pc.require(all(type(v) is bool for v in value["instrumentation"].values()), "instrumentation type")


@dataclass(frozen=True)
class ConfigurationPairClaim:
    """Immutable caller-supplied bytes. Creation is not approval or authentication."""
    raw_configuration: bytes
    resolved_claim: bytes


def capture_configuration_pair(raw_configuration, resolved_claim):
    """Check byte/schema bounds and retain exact bytes, including unknown raw content."""
    pc.require(type(raw_configuration) is bytes and 0 < len(raw_configuration) <= RAW_BYTES,
               "raw configuration byte budget")
    _validate_resolved(resolved_claim)
    return ConfigurationPairClaim(raw_configuration, resolved_claim)


def require_same_configuration_pair(expected, raw_configuration, resolved_claim):
    """Return no permit. Require consistency with a separately supplied expected pair.

    Expected data is caller-owned and untrusted too. Revalidate both sides so a
    directly constructed record cannot skip admission. Exact byte equality is
    deliberately stricter than JSON equivalence; nothing is canonicalised away.
    """
    pc.require(type(expected) is ConfigurationPairClaim, "expected configuration pair")
    admitted = capture_configuration_pair(expected.raw_configuration, expected.resolved_claim)
    candidate = capture_configuration_pair(raw_configuration, resolved_claim)
    pc.require(candidate.raw_configuration == admitted.raw_configuration, "raw configuration changed")
    pc.require(candidate.resolved_claim == admitted.resolved_claim, "resolved configuration changed")


if __name__ == "__main__":
    raise SystemExit(2)  # No file, process, signing or launch operation.
