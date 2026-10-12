"""Strict, bounded source prototype for one FormatVersion-2 UI configuration.

No filesystem, SDK, signing, process or launch operation occurs here. The actual
Xcode-16.4 output must be inspected at Stage B; unsupported fields refuse. A
synthetic parser pass is not a verified installed-Xcode configuration or permit.
"""
from dataclasses import dataclass
import json
import re
from xml.parsers import expat

import probe_contract as pc

MAX_BYTES = 1024 * 1024
MAX_DEPTH = 16
MAX_NODES = 4096
METHODS = (
    "SelectionProbeUITests/testSelectedReadSucceedsOnlyDuringScope",
    "SelectionProbeUITests/testGenuinePanelCancellationRetiresWithoutSelection",
    "SelectionProbeUITests/testActiveReadCancelRetiresBeforeRetry",
)


def decode_xml(raw):
    pc.require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES, "xctestrun byte budget")
    pc.require(not raw.startswith(b"bplist"), "unsupported binary xctestrun")
    try:
        raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise pc.Refusal("xctestrun UTF-8 required") from error
    stack, roots = [], []
    nodes = 0

    def start(name, attributes):
        nonlocal nodes
        nodes += 1
        pc.require(nodes <= MAX_NODES and len(stack) < MAX_DEPTH, "xctestrun structure budget")
        pc.require(name in {"plist", "dict", "array", "key", "string", "integer", "true", "false"},
                   "unsupported plist node")
        pc.require(attributes == ({"version": "1.0"} if name == "plist" else {}), "plist attributes")
        stack.append([name, [], []])

    def characters(text):
        if stack:
            stack[-1][2].append(text)
        else:
            pc.require(not text.strip(), "text outside plist")

    def end(name):
        pc.require(bool(stack) and stack[-1][0] == name, "plist nesting")
        _, children, text = stack.pop()
        text = "".join(text)
        if name in ("key", "string"):
            pc.require(not children and len(pc.utf8(text)) <= 4096, "plist text budget")
            value = text
        elif name == "integer":
            pc.require(not children and re.fullmatch(r"0|[1-9][0-9]{0,19}", text), "plist integer")
            value = int(text)
            pc.require(value <= 2**64 - 1, "plist integer range")
        elif name in ("true", "false"):
            pc.require(not children and not text.strip(), "plist boolean")
            value = name == "true"
        else:
            pc.require(not text.strip(), "container text")
            if name == "dict":
                pc.require(len(children) % 2 == 0, "dictionary pair")
                value = {}
                for offset in range(0, len(children), 2):
                    key, item = children[offset], children[offset + 1]
                    pc.require(key[0] == "key" and item[0] != "key", "dictionary key")
                    pc.require(key[1] not in value, "duplicate plist key")
                    value[key[1]] = item[1]
            elif name == "array":
                pc.require(all(k not in ("key", "plist") for k, _ in children), "array member")
                value = [v for _, v in children]
            else:
                pc.require(not stack and len(children) == 1 and children[0][0] == "dict", "plist root")
                value = children[0][1]
        if stack:
            stack[-1][1].append((name, value))
        else:
            pc.require(name == "plist" and not roots, "single plist")
            roots.append(value)

    def doctype(name, system, public, internal):
        pc.require(name == "plist" and system == "http://www.apple.com/DTDs/PropertyList-1.0.dtd"
                   and public == "-//Apple//DTD PLIST 1.0//EN" and not internal, "unsupported doctype")

    def entity(*_):
        raise pc.Refusal("XML entity refused")

    parser = expat.ParserCreate("UTF-8")
    def declaration(version, encoding, standalone):
        pc.require(version == "1.0" and (encoding is None or encoding.upper() == "UTF-8"),
                   "unsupported XML declaration")

    parser.XmlDeclHandler = declaration
    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = characters
    parser.StartDoctypeDeclHandler = doctype
    parser.EntityDeclHandler = entity
    parser.ExternalEntityRefHandler = entity
    try:
        parser.Parse(raw, True)
    except expat.ExpatError as error:
        raise pc.Refusal("malformed XML plist") from error
    pc.require(not stack and len(roots) == 1, "complete plist")
    return roots[0]


def _text(value):
    pc.require(type(value) is str and 0 < len(pc.utf8(value)) <= 4096 and
               all(ord(c) >= 32 and ord(c) != 127 for c in value), "xctestrun text")
    return value


def _environment(value):
    pc.require(type(value) is dict and len(value) <= 128, "xctestrun environment")
    for key, item in value.items():
        pc.require(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", _text(key)), "environment key")
        pc.require(type(item) is str and len(pc.utf8(item)) <= 4096 and
                   all(ord(c) >= 32 and ord(c) != 127 for c in item), "environment value")


@dataclass(frozen=True)
class ParsedConfiguration:
    raw: bytes
    complete_tree: bytes
    host_path: str
    runner_path: str
    test_bundle_path: str


def parse(raw):
    value = decode_xml(raw)
    pc.keys(value, {"TestConfigurations", "__xctestrun_metadata__"})
    metadata = value["__xctestrun_metadata__"]
    pc.keys(metadata, {"FormatVersion"})
    pc.require(type(metadata["FormatVersion"]) is int and metadata["FormatVersion"] == 2,
               "unsupported xctestrun version")
    configurations = value["TestConfigurations"]
    pc.require(type(configurations) is list and len(configurations) == 1, "one test configuration")
    configuration = configurations[0]
    pc.keys(configuration, {"Name", "IsEnabled", "TestTargets"})
    _text(configuration["Name"])
    pc.require(configuration["IsEnabled"] is True, "enabled configuration")
    targets = configuration["TestTargets"]
    pc.require(type(targets) is list and len(targets) == 1, "one UI target")
    target = targets[0]
    pc.keys(target, {"BlueprintName", "TestBundlePath", "TestHostPath", "UITargetAppPath",
                     "UITargetAppBundleIdentifier", "IsUITestBundle", "OnlyTestIdentifiers",
                     "SkipTestIdentifiers", "CommandLineArguments", "EnvironmentVariables",
                     "TestingEnvironmentVariables"})
    pc.require(target["BlueprintName"] == "SelectionProbeUITests" and target["IsUITestBundle"] is True,
               "fixed UI target")
    pc.require(target["OnlyTestIdentifiers"] == list(METHODS) and target["SkipTestIdentifiers"] == [],
               "exact three UI methods")
    pc.require(target["CommandLineArguments"] == [], "no test arguments")
    for field in ("EnvironmentVariables", "TestingEnvironmentVariables"):
        _environment(target[field])
    _text(target["UITargetAppBundleIdentifier"])
    # All admitted fields are retained, including both complete environments;
    # there is no test-name-only seal or dropped unknown-key path.
    complete = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return ParsedConfiguration(bytes(raw), complete, _text(target["UITargetAppPath"]),
                               _text(target["TestHostPath"]), _text(target["TestBundlePath"]))


def bind(expected, raw, expected_products):
    pc.require(type(expected) is ParsedConfiguration, "admitted expected configuration")
    candidate = parse(raw)
    pc.require(candidate == expected, "configuration changed")
    pc.require(type(expected_products) is tuple and len(expected_products) == 3,
               "expected product tuple")
    host, runner, test = expected_products
    for path in expected_products:
        pc.require(type(path) is str and path and not path.startswith("/") and "\\" not in path
                   and all(part not in ("", ".", "..") for part in path.split("/")), "relative product path")
    pc.require(candidate.host_path == "__TESTROOT__/" + host and
               candidate.runner_path == "__TESTROOT__/" + runner and
               candidate.test_bundle_path in ("__TESTROOT__/" + test,
                                              "__TESTHOST__/" + test.removeprefix(runner + "/")) and
               test.startswith(runner + "/"), "resolved product mismatch")
    return candidate


if __name__ == "__main__":
    raise SystemExit("This quarantined source module supplies no build, signing or launch command.")
