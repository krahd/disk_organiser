"""Only synthetic temporary folders; no user filesystem or network access."""
import errno
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from backend import guided
from backend.guided import GuidedError, GuidedStore


@unittest.skipUnless(guided.supported(), 'POSIX descriptor operations required')
class GuidedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'source'
        self.root.mkdir()
        (self.root / 'a.txt').write_bytes(b'alpha')
        (self.root / 'b.png').write_bytes(b'synthetic image bytes')
        self.store = GuidedStore(self.base / 'state' / 'guided.sqlite', allow_copy=True)

    def plan(self):
        return self.store.scan(str(self.root))

    def apply(self, p):
        return self.store.apply(p['id'], approved=True, local_only=True)

    def dest(self, p, index=0):
        return self.root / p['actions'][index]['destination']

    def test_scan_preview_apply_verified_and_recovery_retains_files_after_restart(self):
        p = self.plan()
        self.assertEqual(p['state'], 'preview')
        self.assertFalse((self.root / p['output']).exists())
        self.assertEqual(len(p['actions']), 2)
        self.assertEqual(self.apply(p)['state'], 'completed')
        self.assertEqual(self.apply(p)['state'], 'completed')
        for a in p['actions']:
            self.assertEqual((self.root / a['source']).read_bytes(), (self.root / a['destination']).read_bytes())
        restarted = GuidedStore(self.store.db_path, allow_copy=True)
        before = restarted.get(p['id'])
        for _ in range(2):
            with self.assertRaisesRegex(GuidedError, 'disabled'):
                restarted.recover(p['id'], True)
        self.assertEqual(restarted.get(p['id']), before)
        self.assertTrue((self.root / p['output']).exists())
        self.assertEqual((self.root / 'a.txt').read_bytes(), b'alpha')

    def test_approval_is_literal_boolean_and_no_mutation_without_it(self):
        p = self.plan()
        for approval in [False, 'true', 1, None]:
            with self.assertRaises(GuidedError):
                self.store.apply(p['id'], approval, True)
        with self.assertRaises(GuidedError):
            self.store.apply(p['id'], True, False)
        self.assertFalse((self.root / p['output']).exists())

    def test_whole_plan_stale_check_before_copy(self):
        p = self.plan()
        (self.root / 'b.png').write_bytes(b'changed')
        with self.assertRaises(GuidedError):
            self.apply(p)
        self.assertFalse((self.root / p['output']).exists())

    def test_collision_never_overwrites(self):
        p = self.plan()
        output = self.root / p['output']
        output.write_bytes(b'existing')
        with self.assertRaises(GuidedError):
            self.apply(p)
        self.assertEqual(output.read_bytes(), b'existing')

    def test_case_collisions_refused(self):
        (self.root / 'A.txt').write_bytes(b'other')
        with self.assertRaisesRegex(GuidedError, 'collision'):
            self.plan()

    def test_links_hardlinks_fifo_unknown_hidden_and_nested_skipped(self):
        (self.root / 'link.txt').symlink_to(self.root / 'a.txt')
        os.link(self.root / 'b.png', self.root / 'hard.png')
        os.mkfifo(self.root / 'pipe.txt')
        (self.root / '.private.txt').write_text('hidden')
        (self.root / 'nested.txt').mkdir()
        (self.root / 'mystery.unknown').write_text('unknown')
        p = self.plan()
        self.assertEqual([a['source'] for a in p['actions']], ['a.txt'])
        self.assertEqual(len(p['skipped']), 7)

    def test_root_and_source_link_swap_refused(self):
        p = self.plan()
        (self.root / 'a.txt').unlink()
        (self.root / 'a.txt').symlink_to(self.root / 'b.png')
        with self.assertRaises(GuidedError):
            self.apply(p)
        with self.assertRaises(OSError):
            link = self.base / 'link'
            link.symlink_to(self.root, target_is_directory=True)
            self.store.scan(str(link))

    def test_root_replacement_refused(self):
        p = self.plan()
        self.root.rename(self.base / 'old')
        self.root.mkdir()
        with self.assertRaises(GuidedError):
            self.apply(p)

    def test_cloud_folder_and_provider_metadata_refused(self):
        cloud = self.base / 'OneDrive'
        cloud.mkdir()
        with self.assertRaisesRegex(GuidedError, 'Cloud'):
            self.store.scan(str(cloud))
        with mock.patch.object(guided.os, 'listxattr', return_value=['com.apple.fileprovider.fpfs']):
            p = self.plan()
        self.assertEqual(p['actions'], [])
        self.assertEqual(len(p['skipped']), 2)

    def test_unreadable_file_skipped(self):
        (self.root / 'a.txt').chmod(0)
        self.addCleanup((self.root / 'a.txt').chmod, 0o600)
        p = self.plan()
        self.assertEqual([a['source'] for a in p['actions']], ['b.png'])

    def test_disk_full_before_and_during_copy_preserves_originals(self):
        p = self.plan()
        with mock.patch.object(guided.os, 'fstatvfs', return_value=mock.Mock(f_bavail=0, f_frsize=4096)):
            with self.assertRaisesRegex(GuidedError, 'space'):
                self.apply(p)
        self.assertFalse((self.root / p['output']).exists())
        with mock.patch.object(guided.os, 'write', side_effect=OSError(errno.ENOSPC, 'disk full')):
            result = self.apply(p)
        self.assertEqual(result['state'], 'interrupted')
        self.assertEqual((self.root / 'a.txt').read_bytes(), b'alpha')
        with self.assertRaisesRegex(GuidedError, 'disabled'):
            self.store.recover(p['id'], True)
        self.assertTrue(self.dest(p).exists())  # uncertain partial file is retained

    def test_journal_failure_before_first_mutation(self):
        p = self.plan()
        with mock.patch.object(self.store, 'save', side_effect=OSError(errno.ENOSPC, 'journal full')):
            with self.assertRaises(OSError):
                self.apply(p)
        self.assertFalse((self.root / p['output']).exists())

    def test_process_interruption_after_one_copy_recovers_without_reapplying(self):
        p = self.plan()
        original_copy = self.store._copy
        calls = []

        def interrupted(*args):
            if calls:
                raise KeyboardInterrupt('simulated process interruption')
            original_copy(*args)
            calls.append(1)
        with mock.patch.object(self.store, '_copy', side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.apply(p)
        restarted = GuidedStore(self.store.db_path, allow_copy=True)
        self.assertEqual(restarted.get(p['id'])['state'], 'applying')
        with self.assertRaises(GuidedError):
            restarted.apply(p['id'], True, True)
        with self.assertRaisesRegex(GuidedError, 'disabled'):
            restarted.recover(p['id'], True)
        self.assertTrue((self.root / p['output']).exists())

    def test_edited_copy_or_changed_original_not_removed(self):
        p = self.plan()
        self.apply(p)
        self.dest(p).write_bytes(b'user edit')
        (self.root / 'b.png').write_bytes(b'new original')
        with self.assertRaisesRegex(GuidedError, 'disabled'):
            self.store.recover(p['id'], True)
        self.assertEqual(self.dest(p).read_bytes(), b'user edit')
        self.assertTrue(self.dest(p, 1).exists())

    def test_recovery_never_opens_selected_folder_or_removes_anything(self):
        p = self.plan()
        self.apply(p)
        before = self.store.get(p['id'])
        with mock.patch.object(guided, 'open_root') as roots, \
                mock.patch.object(guided.os, 'unlink') as unlink, \
                mock.patch.object(guided.os, 'rmdir') as rmdir:
            with self.assertRaisesRegex(GuidedError, 'disabled'):
                self.store.recover(p['id'], True)
            roots.assert_not_called()
            unlink.assert_not_called()
            rmdir.assert_not_called()
        self.assertEqual(self.store.get(p['id']), before)
        self.assertEqual(self.dest(p).read_bytes(), b'alpha')

    def test_unjournalled_output_and_user_additions_retained(self):
        p = self.plan()
        self.apply(p)
        extra = self.root / p['output'] / 'my-notes.txt'
        extra.write_text('user addition')
        with self.assertRaisesRegex(GuidedError, 'disabled'):
            self.store.recover(p['id'], True)
        self.assertEqual(extra.read_text(), 'user addition')

    def test_preview_expiry_and_bounds(self):
        p = self.plan()
        p['created'] -= 3601
        self.store.save(p)
        with self.assertRaisesRegex(GuidedError, 'expired'):
            self.apply(p)
        with mock.patch.object(guided, 'MAX_FILES', 1):
            with self.assertRaisesRegex(GuidedError, '500'):
                self.plan()
        with mock.patch.object(guided, 'MAX_BYTES', 6):
            # Oversized individual file is skipped; bounded supported file still planned.
            p = self.plan()
            self.assertEqual(len(p['actions']), 1)

    def test_concurrent_apply_lock_refuses_second_writer(self):
        p = self.plan()
        with self.store.lock():
            with self.assertRaisesRegex(GuidedError, 'running'):
                self.apply(p)


class LegacyTrashTests(unittest.TestCase):
    def test_no_permanent_delete_fallback(self):
        from backend import fs_ops
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'original.txt'
            path.write_bytes(b'must survive')
            with mock.patch.object(fs_ops, 'send2trash', None):
                with self.assertRaisesRegex(RuntimeError, 'Nothing was deleted'):
                    fs_ops.delete_path(str(path))
            self.assertEqual(path.read_bytes(), b'must survive')


if __name__ == '__main__':
    unittest.main()
