"""Actual fixed-tool observation adapters, called only behind Stage B/C gates.

Parsers are strict prototypes until inspected against the real pinned tools.
Memory tests supply mock ProcessResults; they do not establish a signature.
"""
from dataclasses import dataclass
import hashlib
import re

import probe_contract as pc
import xctestrun_binding as xb

XCODE = '/Applications/Xcode_16.4.app/Contents/Developer/usr/bin/xcodebuild'
DEVELOPER = '/Applications/Xcode_16.4.app/Contents/Developer'
PRODUCTS = ('Debug/OwnedFolderProbe.app', 'Debug/SelectionProbeUITests-Runner.app',
            'Debug/SelectionProbeUITests-Runner.app/Contents/PlugIns/SelectionProbeUITests.xctest')
EXECUTABLES = (PRODUCTS[0] + '/Contents/MacOS/OwnedFolderProbe',
               PRODUCTS[1] + '/Contents/MacOS/SelectionProbeUITests-Runner',
               PRODUCTS[2] + '/Contents/MacOS/SelectionProbeUITests')
ENTITLEMENTS = {'com.apple.security.app-sandbox': True, 'com.apple.security.files.user-selected.read-only': True}

@dataclass(frozen=True)
class Signature:
    identifier: str
    executable: str
    cdhash: str
    entitlements: tuple[tuple[str, bool], ...]
    observation_digests: tuple[str, ...]

@dataclass(frozen=True)
class Observations:
    toolchain: tuple[tuple[str, str], ...]
    signatures: tuple[Signature, ...]
    toolchain_digests: tuple[str, ...]


def _digest(result):
    pc.require(result.returncode == 0 and result.direct_child_reaped and result.owned_group_retired and not result.reason,
               'successful reaped observation tool required')
    return hashlib.sha256(result.stdout + b'\0' + result.stderr).hexdigest()


def _text(value):
    pc.require(type(value) is bytes and len(value) <= 65536, 'observation text budget')
    try:
        return value.decode('utf-8', errors='strict')
    except UnicodeDecodeError as error:
        raise pc.Refusal('observation UTF-8') from error


def parse_signature(metadata, entitlements, *, expected_identifier, expected_executable, expected_entitlements):
    text = _text(metadata)
    fields = {}
    for line in text.splitlines():
        key, separator, value = line.partition('=')
        if key in ('Executable', 'Identifier', 'CDHash', 'Signature') and separator:
            pc.require(key not in fields, 'duplicate signature field')
            fields[key] = value
    pc.require(set(fields) == {'Executable', 'Identifier', 'CDHash', 'Signature'} and
               fields['Executable'] == expected_executable and fields['Identifier'] == expected_identifier and
               fields['Signature'] == 'adhoc' and re.fullmatch(r'[0-9a-f]{40,128}', fields['CDHash']),
               'unexpected signature metadata')
    parsed = xb.decode_xml(entitlements) if entitlements.strip() else {}
    pc.require(type(parsed) is dict and set(parsed) == set(expected_entitlements) and
               all(type(parsed[k]) is bool and parsed[k] is expected_entitlements[k] for k in parsed),
               'unexpected observed entitlements')
    return fields['CDHash'], tuple(sorted(parsed.items()))


def collect_toolchain(tool):
    # tool() is the controller's bounded direct-child owner, not a JSON loader.
    xcode = tool((XCODE, '-version'), timeout=20, max_output=65536)
    sdk = tool(('/usr/bin/xcrun', '--sdk', 'macosx', '--show-sdk-version'), timeout=20, max_output=65536)
    swift = tool(('/usr/bin/xcrun', 'swift', '--version'), timeout=20, max_output=65536)
    pc.require(_text(xcode.stdout).strip() == 'Xcode 16.4\nBuild version 16F6', 'observed Xcode mismatch')
    pc.require(_text(sdk.stdout).strip() == '15.5', 'observed SDK mismatch')
    pc.require(re.fullmatch(r'Apple Swift version 6\.1\.2(?: \([^\n]+\))?\nTarget: [A-Za-z0-9_.-]+\n?',
                           _text(swift.stdout)), 'observed Swift mismatch')
    toolchain = tuple(sorted({'xcodeVersion': '16.4', 'xcodeBuild': '16F6', 'sdkVersion': '15.5', 'swiftVersion': '6.1.2'}.items()))
    return toolchain, tuple(_digest(x) for x in (xcode, sdk, swift))


def collect(tool, products_root, case_id):
    toolchain, toolchain_digests = collect_toolchain(tool)
    base = pc.BUNDLE_PREFIX + case_id
    identifiers = (base, base + '.ui-tests.xctrunner', base + '.ui-tests')
    signatures = []
    for index, (bundle, executable, identifier) in enumerate(zip(PRODUCTS, EXECUTABLES, identifiers)):
        path = products_root + '/' + bundle
        valid = tool(('/usr/bin/codesign', '--verify', '--strict', path), timeout=20, max_output=65536)
        metadata = tool(('/usr/bin/codesign', '--display', '--verbose=4', path), timeout=20, max_output=65536)
        entitlements = tool(('/usr/bin/codesign', '--display', '--entitlements', '-', '--xml', path), timeout=20, max_output=65536)
        digest, values = parse_signature(metadata.stderr, entitlements.stdout,
                                        expected_identifier=identifier, expected_executable=products_root + '/' + executable,
                                        expected_entitlements=ENTITLEMENTS if index == 0 else {})
        signatures.append(Signature(identifier, products_root + '/' + executable, digest, values,
                                    tuple(_digest(x) for x in (valid, metadata, entitlements))))
    return Observations(toolchain, tuple(signatures), toolchain_digests)


if __name__ == '__main__':
    raise SystemExit(2)
