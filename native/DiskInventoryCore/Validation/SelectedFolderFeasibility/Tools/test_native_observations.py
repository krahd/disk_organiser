"""Synthetic fixed-tool outputs only; no process or signature API is invoked."""
import plistlib
from dataclasses import replace
import unittest

import bounded_process as bp
import native_observations as no
import probe_contract as pc

ROOT = '/private/tmp/disk-selection-build-memory/Products'
CASE = '22222222-2222-4222-8222-222222222222'

def result(args, stdout=b'', stderr=b''):
    return bp.ProcessResult(args, stdout, stderr, 0, True, False, '', True)

def metadata(identifier, executable):
    return ('Executable=' + executable + '\nIdentifier=' + identifier + '\nCDHash=' + 'a' * 40 + '\nSignature=adhoc\n').encode()

def tool(arguments, **_):
    if arguments == (no.XCODE, '-version'): return result(arguments, b'Xcode 16.4\nBuild version 16F6\n')
    if arguments[1:] == ('--sdk','macosx','--show-sdk-version'): return result(arguments,b'15.5\n')
    if arguments[1:] == ('swift','--version'): return result(arguments,b'Apple Swift version 6.1.2 (synthetic)\nTarget: arm64-apple-macosx15.0\n')
    index = [ROOT + '/' + p for p in no.PRODUCTS].index(arguments[-1])
    identifiers = [pc.BUNDLE_PREFIX + CASE, pc.BUNDLE_PREFIX + CASE + '.ui-tests.xctrunner', pc.BUNDLE_PREFIX + CASE + '.ui-tests']
    if '--verify' in arguments: return result(arguments)
    if '--verbose=4' in arguments: return result(arguments,stderr=metadata(identifiers[index],ROOT + '/' + no.EXECUTABLES[index]))
    return result(arguments,plistlib.dumps(no.ENTITLEMENTS if index == 0 else {}))

class NativeObservationTests(unittest.TestCase):
    def testThreeFixedProductsAndPinnedToolchainAreObserved(self):
        calls=[]
        def record(args, **kwargs): calls.append(args); return tool(args,**kwargs)
        value = no.collect(record,ROOT,CASE)
        self.assertEqual(len(value.signatures),3); self.assertEqual(len(calls),12)
        self.assertEqual(dict(value.signatures[0].entitlements),no.ENTITLEMENTS)
        self.assertEqual(value.signatures[1].entitlements,())
        self.assertTrue(all(args[0] in bp.TOOLS for args in calls))

    def testSuccessfulDictionaryWithoutVerificationIsNotAccepted(self):
        def failed(args,**kwargs):
            value=tool(args,**kwargs)
            return replace(value,returncode=1) if '--verify' in args else value
        with self.assertRaisesRegex(pc.Refusal,'successful reaped'): no.collect(failed,ROOT,CASE)

    def testMissingWrongOrDuplicateIdentityRefuses(self):
        identifier=pc.BUNDLE_PREFIX+CASE; path=ROOT+'/'+no.EXECUTABLES[0]; raw=metadata(identifier,path)
        for candidate in (raw+b'Identifier=other\n',raw.replace(identifier.encode(),b'other'),raw.replace(path.encode(),b'/other'),raw.replace(b'Signature=adhoc',b'Signature=Developer ID')):
            with self.assertRaises(pc.Refusal):
                no.parse_signature(candidate,plistlib.dumps(no.ENTITLEMENTS),expected_identifier=identifier,expected_executable=path,expected_entitlements=no.ENTITLEMENTS)

    def testExtraFalseAndIntegerEntitlementsRefuse(self):
        identifier=pc.BUNDLE_PREFIX+CASE; path=ROOT+'/'+no.EXECUTABLES[0]
        for values in ({**no.ENTITLEMENTS,'extra':True},{**no.ENTITLEMENTS,'com.apple.security.app-sandbox':False},
                       {**no.ENTITLEMENTS,'com.apple.security.app-sandbox':1},{}):
            with self.assertRaises(pc.Refusal):
                no.parse_signature(metadata(identifier,path),plistlib.dumps(values),expected_identifier=identifier,expected_executable=path,expected_entitlements=no.ENTITLEMENTS)

    def testUnexpectedToolchainAndUnreapedObservationRefuse(self):
        for changed in ('version','reaping'):
            def bad(args,**kwargs):
                value=tool(args,**kwargs)
                if args==(no.XCODE,'-version'):
                    return replace(value,stdout=b'Xcode 16.5\nBuild version other') if changed=='version' else replace(value,direct_child_reaped=False)
                return value
            with self.assertRaises(pc.Refusal): no.collect(bad,ROOT,CASE)

    def testRawObservationDigestChangesAreRetained(self):
        before=no.collect(tool,ROOT,CASE)
        def changed(args,**kwargs):
            value=tool(args,**kwargs)
            return replace(value,stderr=value.stderr+b'Observed diagnostic\n') if '--verify' in args else value
        after=no.collect(changed,ROOT,CASE)
        self.assertNotEqual(before,after)
        self.assertEqual(before.signatures[0].cdhash,after.signatures[0].cdhash)

if __name__ == '__main__': unittest.main()
