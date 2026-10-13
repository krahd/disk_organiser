"""Actual fixed-tool observation adapters, called only behind Stage B/C gates.

Parsers are strict prototypes until inspected against the real pinned tools.
Memory tests supply mock ProcessResults; they do not establish a signature.
"""
from dataclasses import dataclass
import hashlib
import os
import re
import stat

import probe_contract as pc
import xctestrun_binding as xb

XCODE = '/Applications/Xcode_16.4.app/Contents/Developer/usr/bin/xcodebuild'
DEVELOPER = '/Applications/Xcode_16.4.app/Contents/Developer'
OTOOL = DEVELOPER + '/Toolchains/XcodeDefault.xctoolchain/usr/bin/otool-classic'
PRODUCTS = ('Debug/OwnedFolderProbe.app', 'Debug/SelectionProbeUITests-Runner.app',
            'Debug/SelectionProbeUITests-Runner.app/Contents/PlugIns/SelectionProbeUITests.xctest')
EXECUTABLES = (PRODUCTS[0] + '/Contents/MacOS/OwnedFolderProbe',
               PRODUCTS[1] + '/Contents/MacOS/SelectionProbeUITests-Runner',
               PRODUCTS[2] + '/Contents/MacOS/SelectionProbeUITests')
ENTITLEMENTS = {'com.apple.security.app-sandbox': True, 'com.apple.security.files.user-selected.read-only': True}


def inspector_identity():
    """Fixed trusted-toolchain leaf only; no search or signature attestation."""
    value = os.lstat(OTOOL)
    pc.require(stat.S_ISREG(value.st_mode) and value.st_uid == 0 and
               value.st_mode & 0o111 and not value.st_mode & 0o022 and
               0 < value.st_size <= 64 * 1024 * 1024,
               'fixed dependency inspector identity refused')
    return (value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_gid,
            value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _install_name(value):
    if type(value) is not str or not 1 <= len(value) <= 512:
        return False
    if not value.startswith(('/usr/lib/', '/System/Library/Frameworks/')):
        return False
    parts = value.split('/')[1:]
    return all(re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}', part) and
               part not in ('.', '..') and not part.endswith('.debug.dylib') and
               part != '__preview.dylib' for part in parts)


def parse_host_dependencies(raw, expected_executable):
    """Direct install names only, not dyld resolution or transitive closure."""
    pc.require(type(raw) is bytes and 0 < len(raw) <= 65536 and raw.endswith(b'\n'),
               'dependency output bounds')
    pc.require(type(expected_executable) is str and re.fullmatch(
        r'/private/tmp/disk-selection-build-[A-Za-z0-9_-]{1,128}/Products/'
        r'Debug/OwnedFolderProbe\.app/Contents/MacOS/OwnedFolderProbe', expected_executable),
        'fixed owned host inspection spelling')
    try:
        text = raw.decode('ascii', errors='strict')
    except UnicodeDecodeError as error:
        raise pc.Refusal('dependency output ASCII') from error
    lines = text[:-1].split('\n')
    pc.require(len(lines) <= 130 and all(0 < len(line) <= 1024 for line in lines),
               'dependency line bounds')
    sections = {}
    architecture = None
    number = r'(0|[1-9][0-9]{0,4})\.(0|[1-9][0-9]{0,2})\.(0|[1-9][0-9]{0,2})'
    record = re.compile(r'\t([^\s]+) \(compatibility version ' + number +
                        r', current version ' + number + r'(?:, (weak|reexport|upward|lazy))?\)')
    for line in lines:
        header = re.fullmatch(re.escape(expected_executable) + r' \(architecture (arm64|x86_64)\):', line)
        if header:
            architecture = header.group(1)
            pc.require(architecture not in sections, 'duplicate dependency architecture')
            sections[architecture] = []
            continue
        match = record.fullmatch(line)
        pc.require(architecture is not None and match is not None, 'dependency record grammar')
        name, *fields = match.groups()
        pc.require(_install_name(name), 'unapproved direct dependency')
        versions = tuple(int(value) for value in fields[:6])
        pc.require(all(value <= ceiling for value, ceiling in zip(versions, (65535, 255, 255) * 2)),
                   'dependency version range')
        current = sections[architecture]
        pc.require(len(current) < 64 and name not in {row[0] for row in current},
                   'dependency count or duplicate')
        current.append((name, versions[:3], versions[3:], fields[6] or 'normal'))
    pc.require(set(sections) == {'arm64', 'x86_64'} and all(
        rows and '/usr/lib/libSystem.B.dylib' in {row[0] for row in rows}
        for rows in sections.values()), 'complete dependency architecture evidence')
    return tuple((arch, tuple(sections[arch])) for arch in ('arm64', 'x86_64'))


def inspect_host_dependencies(tool, products_root, identity):
    pc.require(inspector_identity() == identity, 'dependency inspector changed before call')
    executable = products_root + '/' + EXECUTABLES[0]
    arguments = (OTOOL, '-arch', 'all', '-L', executable)
    result = tool(arguments, timeout=20, max_output=65536)
    pc.require(inspector_identity() == identity, 'dependency inspector changed after call')
    pc.require(result.arguments == arguments and result.stderr == b'' and not result.cancelled,
               'dependency observation identity or diagnostic')
    _digest(result)
    return parse_host_dependencies(result.stdout, executable)


def require_monolithic_host_inventory(rows):
    """Consume an already bounded owned inventory; never inspect supplied paths."""
    folder = PRODUCTS[0] + '/Contents/MacOS'
    executable = EXECUTABLES[0]
    pc.require({name for name in rows if name == folder or name.startswith(folder + '/')} ==
               {folder, executable}, 'unexpected host executable layout')
    pc.require(rows[folder]['kind'] == 'directory' and rows[executable]['kind'] == 'file' and
               type(rows[executable]['size']) is int and rows[executable]['size'] > 0,
               'missing regular host executable layout')

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
