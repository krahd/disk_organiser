"""Bounded, local-only copy organisation with a durable recovery journal.

Originals are never renamed, unlinked or modified. POSIX descriptor-relative
operations avoid traversing links; unsupported platforms fail closed. A journal
is evidence, not a backup: recovery refuses anything it cannot prove unchanged.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import time
import uuid

MAX_FILES = 500
MAX_BYTES = 1024 ** 3
RESERVE_BYTES = 16 * 1024 ** 2
CATEGORIES = {
    'Documents': {'.pdf', '.txt', '.md', '.docx', '.odt', '.csv', '.xlsx'},
    'Images': {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.heic'},
    'Audio': {'.wav', '.mp3', '.aiff', '.flac', '.m4a', '.ogg'},
    'Video': {'.mp4', '.mov', '.mkv', '.webm'},
    'Archives': {'.zip', '.tar', '.gz', '.7z'},
}
CLOUD_NAMES = {'onedrive', 'dropbox', 'google drive', 'googledrive', 'icloud',
               'cloudstorage', 'mobile documents'}
LIMITS = ('Copies top-level regular files only; originals stay in place. '
          'No space is reclaimed. No deletion, moving, deduplication or AI. '
          'Local POSIX disks only. Synced/cloud/network folders, links, '
          'special files and metadata/ACL preservation are unsupported. '
          'Keep a separate backup; never erase source media based on this report.')


class GuidedError(Exception):
    """An expected safe stop that can be shown to the user."""


def supported():
    return (os.name == 'posix' and hasattr(os, 'O_NOFOLLOW')
            and os.open in os.supports_dir_fd and os.link in os.supports_dir_fd)


def identity(st):
    return [st.st_dev, st.st_ino]


def stamp(st):
    return [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_mode]


def _cloud(path, st):
    if any(any(name in part.casefold() for name in CLOUD_NAMES) for part in Path(path).parts):
        return True
    if getattr(st, 'st_flags', 0) & 0x40000000:  # macOS UF_DATALESS
        return True
    return bool(getattr(st, 'st_file_attributes', 0) & (0x1000 | 0x40000 | 0x400000))


@contextlib.contextmanager
def open_root(path):
    if not supported():
        raise GuidedError('Guided copies require macOS/Linux POSIX file APIs; this platform is read-only unsupported.')
    if not isinstance(path, str) or not path or not os.path.isabs(path) or '\x00' in path:
        raise GuidedError('Choose an absolute local folder path.')
    if '..' in Path(path).parts:
        raise GuidedError('Parent traversal is not supported; choose the direct folder path.')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in Path(path).parts[1:]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        if _cloud(path, os.fstat(fd)):
            raise GuidedError('Cloud/synchronised folders are unsupported. '
                              'Choose a fully local, unsynchronised folder.')
        yield fd
    finally:
        os.close(fd)


def fingerprint(fd, name):
    before = os.stat(name, dir_fd=fd, follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise GuidedError('Links, hard links and special files are not supported.')
    if not before.st_mode & 0o444 or _cloud(name, before):
        raise GuidedError('Unreadable files and cloud placeholders are not supported.')
    if before.st_size > MAX_BYTES:
        raise GuidedError('File exceeds the 1 GiB first-version limit.')
    filefd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    try:
        if stamp(os.fstat(filefd)) != stamp(before):
            raise GuidedError('File changed while being opened; scan again.')
        # Known provider metadata is rejected before reading content (no hydration).
        if hasattr(os, 'listxattr'):
            try:
                attrs = os.listxattr(filefd)
            except OSError as exc:
                raise GuidedError('Cannot inspect file metadata safely.') from exc
            if any('fileprovider' in x.casefold() or 'icloud' in x.casefold() for x in attrs):
                raise GuidedError('Cloud provider metadata is unsupported.')
        digest = hashlib.sha256()
        count = 0
        while True:
            chunk = os.read(filefd, 1024 * 1024)
            if not chunk:
                break
            count += len(chunk)
            if count > MAX_BYTES:
                raise GuidedError('File grew beyond the first-version limit.')
            digest.update(chunk)
        after = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if stamp(os.fstat(filefd)) != stamp(before) or stamp(after) != stamp(before):
            raise GuidedError('File changed during verification; scan again.')
        return {'stamp': stamp(before), 'sha256': digest.hexdigest(), 'size': count}
    finally:
        os.close(filefd)


def _exists(fd, name):
    try:
        os.stat(name, dir_fd=fd, follow_symlinks=False)
        return True
    except FileNotFoundError:
        return False


def _sync(fd):
    os.fsync(fd)


class GuidedStore:
    def __init__(self, db_path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as con:
            con.execute('CREATE TABLE IF NOT EXISTS guided (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')

    @contextlib.contextmanager
    def connection(self):
        con = sqlite3.connect(self.db_path, timeout=2)
        try:
            con.execute('PRAGMA synchronous=FULL')
            with con:
                yield con
        finally:
            con.close()

    @contextlib.contextmanager
    def lock(self):
        import fcntl
        with open(self.db_path + '.lock', 'a') as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise GuidedError('Another guided operation is running. Wait, then refresh history.') from exc
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def save(self, plan):
        with self.connection() as con:
            con.execute('INSERT OR REPLACE INTO guided VALUES (?,?)', (plan['id'], json.dumps(plan)))

    def get(self, plan_id):
        with self.connection() as con:
            row = con.execute('SELECT payload FROM guided WHERE id=?', (plan_id,)).fetchone()
        if not row:
            raise GuidedError('Plan not found. Refresh history or scan again.')
        return json.loads(row[0])

    def history(self):
        with self.connection() as con:
            rows = con.execute('SELECT payload FROM guided ORDER BY rowid DESC LIMIT 50')
            return [json.loads(row[0]) for row in rows]

    def scan(self, root):
        with open_root(root) as fd:
            names = []
            with os.scandir(fd) as entries:
                for entry in entries:
                    if len(names) >= MAX_FILES:
                        raise GuidedError('Folder exceeds 500 entries. Choose a smaller folder; '
                                          'no partial plan was created.')
                    names.append(entry.name)
            names.sort()
            plan_id = uuid.uuid4().hex
            plan = {'id': plan_id, 'root': os.path.normpath(root), 'root_identity': identity(os.fstat(fd)),
                    'output': 'Organised-' + plan_id[:12], 'state': 'preview', 'created': time.time(),
                    'actions': [], 'skipped': [], 'directories': {}, 'limitations': LIMITS,
                    'bytes': 0, 'error': None}
            for name in names:
                suffix = Path(name).suffix.casefold()
                category = next((key for key, suffixes in CATEGORIES.items() if suffix in suffixes), None)
                try:
                    if name.startswith('.') or not category:
                        raise GuidedError('Hidden, nested or unrecognised files stay unchanged.')
                    fp = fingerprint(fd, name)
                    plan['bytes'] += fp['size']
                    if plan['bytes'] > MAX_BYTES:
                        raise GuidedError('Folder exceeds the 1 GiB first-version limit; choose a smaller folder.')
                    plan['actions'].append({'source': name, 'category': category,
                                            'destination': f"{plan['output']}/{category}/{name}",
                                            'reason': f"{suffix} extension → {category}; content is not interpreted",
                                            'fingerprint': fp, 'state': 'planned', 'owned': None})
                except (GuidedError, OSError) as exc:
                    if plan['bytes'] > MAX_BYTES:
                        raise GuidedError('Folder exceeds the 1 GiB first-version limit; '
                                          'choose a smaller folder.') from exc
                    plan['skipped'].append({'path': name, 'reason': str(exc)})
            # Portable case-folding check rejects collisions even on case-sensitive hosts.
            targets = [a['destination'].casefold() for a in plan['actions']]
            if len(targets) != len(set(targets)):
                raise GuidedError('Case-insensitive filename collision. '
                                  'Rename the conflicting files yourself before scanning again.')
            if _exists(fd, plan['output']):
                raise GuidedError('Output folder already exists; scan again.')
            plan['required_bytes'] = plan['bytes'] + RESERVE_BYTES
            self.save(plan)
            return plan

    def _root_matches(self, plan, fd):
        if identity(os.fstat(fd)) != plan['root_identity']:
            raise GuidedError('Selected folder was replaced. No further changes are permitted.')

    def _create_dir(self, plan, parent, name, key):
        os.mkdir(name, mode=0o700, dir_fd=parent)
        _sync(parent)
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        plan['directories'][key] = identity(os.fstat(fd))
        try:
            self.save(plan)
        except BaseException:
            os.close(fd)
            raise
        return fd

    def _open_owned_dir(self, plan, parent, name, key):
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        if identity(os.fstat(fd)) != plan['directories'].get(key):
            os.close(fd)
            raise GuidedError('Generated folder ownership cannot be verified; inspect it manually.')
        return fd

    def apply(self, plan_id, approved=False, local_only=False):
        if approved is not True or local_only is not True:
            raise GuidedError('Explicit approval and confirmation of a local, unsynchronised folder are required.')
        if not supported():
            raise GuidedError('This platform does not support guided copies.')
        with self.lock():
            plan = self.get(plan_id)
            if plan['state'] == 'completed':
                return plan  # idempotent response to an uncertain/repeated submission
            if plan['state'] != 'preview' or not plan['actions']:
                raise GuidedError('Plan cannot be applied. Recover an interrupted operation or create a new preview.')
            with open_root(plan['root']) as root:
                self._root_matches(plan, root)
                if time.time() - plan['created'] > 3600:
                    raise GuidedError('Preview expired after one hour. Scan again.')
                if _exists(root, plan['output']):
                    raise GuidedError('Destination now exists. Nothing was overwritten; scan again.')
                for action in plan['actions']:
                    if fingerprint(root, action['source']) != action['fingerprint']:
                        raise GuidedError('A source changed since preview. No copies made; scan again.')
                fs = os.fstatvfs(root)
                if fs.f_bavail * fs.f_frsize < plan['required_bytes']:
                    raise GuidedError('Insufficient free space for all copies plus a 16 MiB safety reserve.')
                plan['state'] = 'applying'
                self.save(plan)  # durable intent before the first filesystem mutation
                output = None
                try:
                    output = self._create_dir(plan, root, plan['output'], '.')
                    for category in sorted({a['category'] for a in plan['actions']}):
                        folder = self._create_dir(plan, output, category, category)
                        try:
                            for action in [a for a in plan['actions'] if a['category'] == category]:
                                self._copy(plan, action, root, folder)
                        finally:
                            os.close(folder)
                    plan['state'] = 'completed'
                    self.save(plan)
                except Exception as exc:
                    plan['state'] = 'interrupted'
                    plan['error'] = f'{type(exc).__name__}: {exc}. Originals retained; use recovery.'
                    self.save(plan)
                finally:
                    if output is not None:
                        os.close(output)
                return plan

    def _copy(self, plan, action, root, folder):
        name = action['source']
        if fingerprint(root, name) != action['fingerprint']:
            raise GuidedError('Source changed during apply.')
        # O_EXCL never replaces an existing name; O_NOFOLLOW rejects link redirection.
        dest = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=folder)
        try:
            action['owned'] = identity(os.fstat(dest))
            action['state'] = 'copying'
            self.save(plan)
            src = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root)
            try:
                if stamp(os.fstat(src)) != action['fingerprint']['stamp']:
                    raise GuidedError('Source changed before copying.')
                count = 0
                while True:
                    chunk = os.read(src, 1024 * 1024)
                    if not chunk:
                        break
                    count += len(chunk)
                    if count > action['fingerprint']['size']:
                        raise GuidedError('Source grew while copying.')
                    view = memoryview(chunk)
                    while view:
                        written = os.write(dest, view)
                        if not written:
                            raise OSError('Short write')
                        view = view[written:]
                _sync(dest)
            finally:
                os.close(src)
        finally:
            os.close(dest)
        _sync(folder)
        copy = fingerprint(folder, name)
        if copy['sha256'] != action['fingerprint']['sha256'] or fingerprint(root, name) != action['fingerprint']:
            raise GuidedError('Verification changed; retain originals and inspect recovery.')
        action['result_fingerprint'] = copy
        action['state'] = 'copied'
        self.save(plan)

    def recover(self, plan_id, approved=False):
        if approved is not True:
            raise GuidedError('Explicit approval to remove only verified generated copies is required.')
        if not supported():
            raise GuidedError('This platform does not support guided recovery.')
        with self.lock():
            plan = self.get(plan_id)
            if plan['state'] == 'undone':
                return plan
            if plan['state'] not in {'completed', 'applying', 'interrupted', 'recovery_blocked', 'recovering'}:
                raise GuidedError('This plan has no applied copies to recover.')
            plan['state'] = 'recovering'
            plan['error'] = None
            self.save(plan)
            conflicts = []
            try:
                with open_root(plan['root']) as root:
                    self._root_matches(plan, root)
                    if not _exists(root, plan['output']):
                        # Root disappearance is safe; do not search elsewhere or recreate it.
                        plan['state'] = 'undone'
                        self.save(plan)
                        return plan
                    output = self._open_owned_dir(plan, root, plan['output'], '.')
                    try:
                        for action in reversed(plan['actions']):
                            if action['state'] == 'undone':
                                continue
                            folder = None
                            try:
                                if not _exists(output, action['category']):
                                    continue
                                folder = self._open_owned_dir(plan, output, action['category'], action['category'])
                                name = action['source']
                                if not _exists(folder, name):
                                    action['state'] = 'undone'
                                    self.save(plan)
                                    continue
                                current = fingerprint(folder, name)
                                if current['stamp'][:2] != action['owned']:
                                    raise GuidedError('Copy was replaced or its ownership was not journalled.')
                                # Partial or edited copies are deliberately left for manual inspection.
                                if current['sha256'] != action['fingerprint']['sha256']:
                                    raise GuidedError('Copy is incomplete or changed. Retained for manual inspection.')
                                if fingerprint(root, name) != action['fingerprint']:
                                    raise GuidedError('Original changed or disappeared. Retaining the generated copy.')
                                # Final lstat check before unlink; untrusted concurrent writers are unsupported.
                                if stamp(os.stat(name, dir_fd=folder, follow_symlinks=False)) != current['stamp']:
                                    raise GuidedError('Copy changed during recovery.')
                                os.unlink(name, dir_fd=folder)
                                _sync(folder)
                                action['state'] = 'undone'
                                self.save(plan)
                            except (OSError, GuidedError) as exc:
                                conflicts.append({'path': action['destination'], 'reason': str(exc)})
                            finally:
                                if folder is not None:
                                    os.close(folder)
                        # Only our inode-verified empty directories can be removed. User additions stay.
                        for category in sorted(plan['directories']):
                            if category == '.' or not _exists(output, category):
                                continue
                            fd = self._open_owned_dir(plan, output, category, category)
                            os.close(fd)
                            try:
                                os.rmdir(category, dir_fd=output)
                                _sync(output)
                            except OSError as exc:
                                conflicts.append({'path': category, 'reason': str(exc)})
                    finally:
                        os.close(output)
                    try:
                        # Recheck ownership immediately before the empty-directory removal.
                        fd = self._open_owned_dir(plan, root, plan['output'], '.')
                        os.close(fd)
                        os.rmdir(plan['output'], dir_fd=root)
                        _sync(root)
                    except OSError as exc:
                        conflicts.append({'path': plan['output'], 'reason': str(exc)})
            except (OSError, GuidedError) as exc:
                conflicts.append({'path': plan['output'], 'reason': str(exc)})
            plan['conflicts'] = conflicts
            plan['state'] = 'recovery_blocked' if conflicts else 'undone'
            self.save(plan)
            return plan
