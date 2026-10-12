"""Read-only upload packet verification with fully mocked descriptors."""
from contextlib import ExitStack
from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import patch
import hashlib
import json
import os
import stat
import unittest

import stage_b_receipt as receipt
import stage_b_upload as upload
from test_stage_b_receipt import MemoryFS, Entries, ROOT, metadata


class UploadTests(unittest.TestCase):
    def setUp(self):
        self.fs=MemoryFS();self.stack=ExitStack();self.addCleanup(self.stack.close)
        for name in ('open','stat','fstat','read','write','close','scandir','lseek'):
            self.stack.enter_context(patch.object(receipt.os,name,side_effect=getattr(self.fs,name)))
        self.stack.enter_context(patch.object(receipt.os,'getuid',return_value=501))
        self.stack.enter_context(patch.object(receipt.os,'fsync',return_value=None))
        self.stack.enter_context(patch.object(receipt.sys,'platform','darwin'))
        self.stack.enter_context(patch.object(receipt.tempfile,'mkdtemp',return_value=ROOT))
        self.stack.enter_context(patch.object(receipt.time,'monotonic',return_value=1))
        self.stack.enter_context(patch('builtins.open',side_effect=AssertionError('unmocked file')))
        report=receipt.Report.create(deadline=900);report.add('raw.bin',b'$HOME `x` \x00 \xf0\x9f\x92\xbe');report.add('empty.bin',b'')
        self.terminal=report.finalise(json.dumps({'outcome':'candidate_pass','runID':'123','driverCommit':'a'*40}).encode())
        self.record=asdict(self.terminal);self.record['report_path']=self.record.pop('path');self.record.update(runID='123',driverCommit='a'*40)
        self.env={'GITHUB_RUN_ID':'123','GITHUB_SHA':'a'*40}
        self.parents={'/':90,'private':91,'tmp':92,ROOT.split('/')[-1]:10}
        def opened(name,flags,*args,**kwargs):
            if name in self.parents:return self.parents[name]
            return self.fs.open(name,flags,*args,**kwargs)
        self.stack.enter_context(patch.object(upload.os,'open',side_effect=opened))
        self.fs.closed.clear()

    def verify(self,record=None):
        return upload.verify_packet('OWNED_BUILD_TERMINAL '+json.dumps(self.record if record is None else record),self.env)

    def testExactPacketRawBytesAndRootRetirement(self):
        self.assertEqual(self.verify(),ROOT)
        for fd in self.parents.values():self.assertEqual(self.fs.closed.count(fd),1)

    def testRunSHAPathAndRootIdentityMutationsRefuse(self):
        for field,value in [('runID','124'),('driverCommit','b'*40),('root_inode',99),('root_device',True),
                            ('report_path','/private/tmp/other'),('manifest_bytes',True),('manifest_sha256','b'*64)]:
            changed=dict(self.record);changed[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.verify(changed)

    def testChangedPayloadAndUnexpectedMemberRefuse(self):
        self.fs.data['raw.bin']=b'x'*len(self.fs.data['raw.bin'])
        with self.assertRaisesRegex(ValueError,'payload mismatch'):self.verify()
        self.fs.data['extra.bin']=b'';self.fs.nodes['extra.bin']=metadata(999)
        with self.assertRaises(ValueError):self.verify()

    def testMissingAndNonregularLeavesRefuse(self):
        for mode in (stat.S_IFLNK|0o600,stat.S_IFIFO|0o600,stat.S_IFREG|0o644):
            self.fs.nodes['raw.bin'].st_mode=mode
            with self.assertRaises(ValueError):self.verify()
        del self.fs.nodes['raw.bin']
        with self.assertRaises(FileNotFoundError):self.verify()

    def testAmbiguousCloseIsNotRetried(self):
        self.fs.close_errors[10]=OSError('ambiguous')
        with self.assertRaisesRegex(ValueError,'close'):self.verify()
        self.assertEqual(self.fs.closed.count(10),1)

    def testMultilineDuplicateKeyAndConstantRefuseBeforeOpen(self):
        values=['OWNED_BUILD_TERMINAL {}\n','OWNED_BUILD_TERMINAL {"x":1,"x":2}','OWNED_BUILD_TERMINAL {"x":NaN}']
        for raw in values:
            with patch.object(upload.os,'open') as opened,self.assertRaises(ValueError):
                upload.verify_packet(raw,self.env)
            opened.assert_not_called()

    def testOutcomeIdentityCannotBeReboundUnderNewManifest(self):
        changed={'outcome':'candidate_pass','runID':'other','driverCommit':'a'*40}
        self.fs.data['outcome.json']=json.dumps(changed).encode();self.fs.nodes['outcome.json'].st_size=len(self.fs.data['outcome.json'])
        manifest=json.loads(self.fs.data['manifest.json'])
        for row in manifest['files']:
            if row['path']=='outcome.json':row.update(bytes=len(self.fs.data['outcome.json']),sha256=hashlib.sha256(self.fs.data['outcome.json']).hexdigest())
        raw=json.dumps(manifest).encode();self.fs.data['manifest.json']=raw;self.fs.nodes['manifest.json'].st_size=len(raw)
        self.record.update(manifest_bytes=len(raw),manifest_sha256=hashlib.sha256(raw).hexdigest())
        with self.assertRaisesRegex(ValueError,'outcome binding'):self.verify()

    def testMissingOutcomeCannotCountAsComplete(self):
        manifest=json.loads(self.fs.data['manifest.json']);manifest['files']=[r for r in manifest['files'] if r['path']!='outcome.json']
        raw=json.dumps(manifest).encode();self.fs.data['manifest.json']=raw;self.fs.nodes['manifest.json'].st_size=len(raw)
        self.record.update(manifest_bytes=len(raw),manifest_sha256=hashlib.sha256(raw).hexdigest())
        with self.assertRaisesRegex(ValueError,'outcome binding'):self.verify()

    def testShortReadAndRootReplacementRefuse(self):
        with patch.object(upload.os,'read',return_value=b''):
            with self.assertRaises(ValueError):self.verify()
        self.fs.nodes[ROOT].st_ino=999
        with self.assertRaisesRegex(ValueError,'root changed'):self.verify()


if __name__=='__main__':unittest.main()
