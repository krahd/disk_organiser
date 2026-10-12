"""Memory-only exact original/derived configuration and expectation mutations."""
from copy import deepcopy
from dataclasses import replace
import plistlib
import unittest

import probe_contract as pc
import runner_expectations as rx
import xctestrun_binding as xb
from test_experiment_controller import model


def encode(value): return plistlib.dumps(value, fmt=plistlib.FMT_XML, sort_keys=False)
def target(value): return value['TestConfigurations'][0]['TestTargets'][0]


class RunnerDerivationTests(unittest.TestCase):
    def setUp(self):
        self.owner,self.inspection,_=model();self.binding=self.inspection.runner_binding
        self.expected=dict(self.binding.expectations);self.raw=self.binding.original.raw

    def testDerivationRetainsOriginalAndChangesOnlyRunnerComparisonData(self):
        original=xb.decode_xml(self.raw);derived=xb.decode_xml(self.binding.derived.raw)
        self.assertNotEqual(self.raw,self.binding.derived.raw)
        for key in rx.KEYS:self.assertEqual(target(derived)['EnvironmentVariables'].pop(key),self.expected[key])
        self.assertEqual(derived,original);self.assertEqual(self.binding.original.raw,self.raw)
        self.assertEqual(rx.verify(self.binding,self.raw,self.binding.derived.raw,self.expected),self.binding)

    def testMissingExtraAndChangedExpectationsRefuse(self):
        for key in rx.KEYS:
            missing=dict(self.expected);missing.pop(key)
            with self.assertRaises(pc.Refusal):rx.verify(self.binding,self.raw,self.binding.derived.raw,missing)
            changed=dict(self.expected);changed[key]+='x'
            with self.assertRaises(pc.Refusal):rx.verify(self.binding,self.raw,self.binding.derived.raw,changed)
        extra=dict(self.expected);extra[rx.PREFIX+'EXTRA']='x'
        with self.assertRaises(pc.Refusal):rx.derive('Owned.xctestrun',self.raw,extra)

    def testEveryReservedCollisionInEitherOriginalEnvironmentRefuses(self):
        for field in ('EnvironmentVariables','TestingEnvironmentVariables'):
            for key in rx.KEYS | {rx.PREFIX+'UNKNOWN'}:
                tree=xb.decode_xml(self.raw);target(tree)[field][key]='collision'
                with self.assertRaises(pc.Refusal):rx.derive('Owned.xctestrun',encode(tree),self.expected)

    def testMissingExtraAndMovedDerivedFieldsRefuseEvenWithForgedParsedSeal(self):
        for mutation in (lambda t:t['EnvironmentVariables'].pop(next(iter(rx.KEYS))),
                         lambda t:t['EnvironmentVariables'].update({rx.PREFIX+'UNKNOWN':'x'}),
                         lambda t:t['TestingEnvironmentVariables'].update({rx.PREFIX+'CDHASH':'a'*40}),
                         lambda t:t['EnvironmentVariables'].update({rx.PREFIX+'CDHASH':'b'*40})):
            tree=xb.decode_xml(self.binding.derived.raw);mutation(target(tree));raw=encode(tree)
            forged=replace(self.binding,derived=xb.parse(raw))
            with self.assertRaises(pc.Refusal):rx.verify(forged,self.raw,raw,self.expected)

    def testNonExpectationMutationCannotHideInNewParsedSeal(self):
        for mutation in (lambda t:t['TestingEnvironmentVariables'].update(OTHER='x'),
                         lambda t:t['EnvironmentVariables'].update(OTHER='x'),
                         lambda t:t.update(TestHostPath=t['TestHostPath']+'x'),
                         lambda t:t.update(TestBundlePath=t['TestBundlePath']+'x')):
            tree=xb.decode_xml(self.binding.derived.raw);mutation(target(tree));raw=encode(tree)
            with self.assertRaises(pc.Refusal):rx.verify(replace(self.binding,derived=xb.parse(raw)),self.raw,raw,self.expected)

    def testOriginalOrDerivedWhitespaceChangeCannotUseRetainedBytes(self):
        for original,derived in ((self.raw.replace(b'<dict>',b'<dict>\n',1),self.binding.derived.raw),
                                 (self.raw,self.binding.derived.raw.replace(b'<dict>',b'<dict>\n',1))):
            with self.assertRaises(pc.Refusal):rx.verify(self.binding,original,derived,self.expected)

    def testMalformedIdentityAndPathValuesRefuse(self):
        for suffix,value in [('CDHASH','a'*41),('CDHASH','x'*40),('SOURCE_COMMIT','x'*40),('FIXTURE_SHA256','a'*63),
                             ('FIXTURE_RUN_ID','invalid'),('FIXTURE_CASE_ID','invalid'),('IDENTIFIER','other'),
                             ('EXECUTABLE','/tmp/other'),('EXECUTABLE',self.expected[rx.PREFIX+'EXECUTABLE'].replace('/Products/','/../Products/'))]:
            changed=dict(self.expected);changed[rx.PREFIX+suffix]=value
            with self.assertRaises(pc.Refusal):rx.derive('Owned.xctestrun',self.raw,changed)

    def testDistinctFixedLeafAndTargetIdentityRequired(self):
        for name in (rx.DERIVED_NAME,'../Owned.xctestrun','/Owned.xctestrun','other','x\\Owned.xctestrun'):
            with self.assertRaises(pc.Refusal):rx.derive(name,self.raw,self.expected)
        tree=xb.decode_xml(self.raw);target(tree)['UITargetAppBundleIdentifier']='other'
        with self.assertRaises(pc.Refusal):rx.derive('Owned.xctestrun',encode(tree),self.expected)

    def testSemanticOriginalOrderPreservedAndByteLimitStillApplied(self):
        tree=xb.decode_xml(self.raw);target(tree)['EnvironmentVariables']['LAST']='last'
        raw=encode(tree);binding=rx.derive('Owned.xctestrun',raw,self.expected)
        self.assertEqual(binding.original.raw,raw)
        self.assertEqual(list(target(xb.decode_xml(binding.derived.raw))['EnvironmentVariables'])[:2],
                         list(target(tree)['EnvironmentVariables'])[:2])
        with self.assertRaises(pc.Refusal):rx.derive('Owned.xctestrun',b'x'*(xb.MAX_BYTES+1),self.expected)

if __name__=='__main__':unittest.main()
