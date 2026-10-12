"""Retained fixture owner tests with every descriptor/path operation mocked."""
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import errno
import json
import unittest

import fixture_inputs as fi
import probe_contract as pc

class FixtureOwnerTests(unittest.TestCase):
    def setUp(self):
        self.value=json.loads((Path(__file__).parent/'fixture-claim.example.json').read_bytes())
        self.raw=json.dumps(self.value).encode()

    def metadata(self,key):
        row=self.value['objects'][key]
        return SimpleNamespace(st_dev=row['device'],st_ino=row['inode'],st_mode=row['mode'],st_uid=row['uid'],st_gid=row['gid'],
                               st_size=row['size'],st_nlink=1,st_mtime_ns=0,st_ctime_ns=0)

    def verify(self,*,missing=False,changed=False,extra=False,close_error=False):
        parent=self.metadata('parent');selected=self.metadata('selected');file=self.metadata('selectedFile');sibling=self.metadata('siblingFile')
        outside=self.metadata('selected');outside.st_ino=9
        metadata={10:parent,11:selected,12:file,13:outside,14:sibling}; counts={};data={12:[pc.SELECTED,b''],14:[pc.SIBLING,b'']}
        def opened(name,*args,**kwargs):
            if missing and name=='probe.bin':raise FileNotFoundError(errno.ENOENT,'synthetic')
            return {'selected':11,'probe.bin':12,'outside':13,'sentinel.bin':14}[name]
        def fstat(fd):
            counts[fd]=counts.get(fd,0)+1
            if changed and fd==12 and counts[fd]>1:
                later=self.metadata('selectedFile');later.st_mtime_ns=1;return later
            return metadata[fd]
        def named(path,**kwargs):
            if path=='must-remain-absent.bin':
                if extra:return file
                raise FileNotFoundError(errno.ENOENT,'synthetic')
            return parent
        with ExitStack() as stack:
            stack.enter_context(patch.object(fi.os,'open',side_effect=opened))
            stack.enter_context(patch.object(fi.os,'fstat',side_effect=fstat))
            stack.enter_context(patch.object(fi.os,'stat',side_effect=named))
            stack.enter_context(patch.object(fi.os,'read',side_effect=lambda fd,n:data[fd].pop(0)))
            closed=stack.enter_context(patch.object(fi.os,'close',side_effect=OSError(errno.EINTR,'synthetic') if close_error else None))
            owner=fi.PreparedFixture(fi._FIXTURE_KEY,self.value['fixtureParent'],self.raw,10)
            try:
                try:outcome=owner.verify()
                except BaseException as error:outcome=error
                self.assertNotIn((10,),[call.args for call in closed.call_args_list])
            finally:
                try:owner.close()
                except pc.Refusal:pass
            return outcome,[call.args for call in closed.call_args_list]

    def testVerifiedBytesUseRetainedRootAndSameReadDescriptors(self):
        outcome,closed=self.verify()
        self.assertEqual(outcome,fi.hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(closed,[(14,),(13,),(12,),(11,),(10,)])

    def testMissingContentAndChangedMetadataRefuse(self):
        for kwargs in ({'missing':True},{'changed':True}):
            outcome,closed=self.verify(**kwargs)
            self.assertIsInstance(outcome,(pc.Refusal,OSError));self.assertEqual(closed[-1],(10,))

    def testUnexpectedCreatedControlIsPreservedAndRefused(self):
        outcome,closed=self.verify(extra=True)
        self.assertIsInstance(outcome,pc.Refusal);self.assertIn('evidence preserved',str(outcome))
        self.assertEqual(closed,[(11,),(10,)])

    def testCloseFailuresAttemptEveryOwnedDescriptorWithoutRetry(self):
        outcome,closed=self.verify(close_error=True)
        self.assertIsInstance(outcome,pc.Refusal)
        self.assertEqual(closed,[(14,),(13,),(12,),(11,),(10,)])

    def testImportedClaimCannotConstructFixtureCapability(self):
        with self.assertRaisesRegex(pc.Refusal,'fresh fixture capability'):
            fi.PreparedFixture(object(),'/not-opened',self.raw,10)

    def testRetiredFixtureAndRepeatedCloseDoNotTouchDescriptors(self):
        owner=fi.PreparedFixture(fi._FIXTURE_KEY,'/not-opened',self.raw,10)
        with patch.object(fi.os,'close') as close,patch.object(fi.os,'fstat') as fstat:
            owner.close();owner.close()
            with self.assertRaisesRegex(pc.Refusal,'retired fixture'):owner.verify()
            close.assert_called_once_with(10);fstat.assert_not_called()

if __name__=='__main__':unittest.main()
