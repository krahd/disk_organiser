"""Inclusive inventory capacity with all source-owner filesystem calls mocked."""
import json
import stat
import unittest
from contextlib import ExitStack
from unittest.mock import patch

import owned_build_observation as ob
import probe_contract as pc
from test_stage_b_receipt import metadata, Entries


class InventoryCapacityTests(unittest.TestCase):
    def observe(self, count, limit, *, refuse=False):
        names = ['file-%d' % number for number in range(count)]
        descriptors = {name: 11+index for index, name in enumerate(names)}
        root = metadata(10, stat.S_IFDIR|0o700)
        values = {fd: metadata(fd, size=1) for fd in descriptors.values()}
        values[10] = root
        owner = object.__new__(ob.OwnedBuild); owner._closed = True
        owner._products = lambda ledger: ledger.acquire(lambda: 10)
        owner._admit = lambda: None
        reads = {}; rows = None
        def read(fd, size):
            reads[fd] = reads.get(fd, 0)+1
            return b'x' if reads[fd] == 1 else b''
        with ExitStack() as stack:
            stack.enter_context(patch.object(pc, 'MAX_ENTRIES', limit))
            stack.enter_context(patch.object(ob.time, 'monotonic', return_value=1))
            stack.enter_context(patch.object(ob.os, 'fstat', side_effect=lambda fd: values[fd]))
            stack.enter_context(patch.object(ob.os, 'stat', side_effect=lambda name, **kw: values[descriptors[name]]))
            stack.enter_context(patch.object(ob.os, 'scandir', return_value=Entries(names)))
            stack.enter_context(patch.object(ob.os, 'getuid', return_value=501))
            opened = stack.enter_context(patch.object(ob.os, 'open', side_effect=lambda name, *a, **kw: descriptors[name]))
            stack.enter_context(patch.object(ob.os, 'read', side_effect=read))
            closed = stack.enter_context(patch.object(ob.os, 'close'))
            check = lambda: pc.require(ob.time.monotonic() < 900, 'attempt deadline')
            if refuse:
                with self.assertRaisesRegex(pc.Refusal, 'product entry budget'):
                    owner.inventory(check=check)
            else:
                rows = [json.loads(row) for row in owner.inventory(check=check)]
            calls = [call.args[0] for call in closed.call_args_list]
            self.assertEqual(len(calls), len(set(calls)))
            self.assertEqual(calls[-1], 10)
            return rows, opened.call_count, calls

    def testExactInclusiveRootAndRegularFileLimitIsAccepted(self):
        self.assertEqual(pc.MAX_ENTRIES, 20000)
        rows, opens, closes = self.observe(2, 3)
        self.assertEqual(len(rows), 3)
        self.assertEqual([row['path'] for row in rows], ['.', 'file-0', 'file-1'])
        self.assertEqual(opens, 2); self.assertEqual(closes, [11, 12, 10])

    def testOneExtraEntryRefusesBeforeOpeningItsFile(self):
        rows, opens, closes = self.observe(3, 3, refuse=True)
        self.assertIsNone(rows); self.assertEqual(opens, 2)
        self.assertEqual(closes, [11, 12, 10])

    def testRootOnlyCanFillOneEntryBudgetWithoutAnotherAdmission(self):
        rows, opens, closes = self.observe(0, 1)
        self.assertEqual(len(rows), 1); self.assertEqual(rows[0]['path'], '.')
        self.assertEqual(opens, 0); self.assertEqual(closes, [10])


if __name__ == '__main__': unittest.main()
