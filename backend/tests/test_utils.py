import os
import sys
import importlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)

utils = importlib.import_module('backend.utils')


def test_find_duplicates_simple(tmp_path):
    d = tmp_path / 'dup'
    d.mkdir()
    a = d / 'a.txt'
    b = d / 'b.txt'
    c = d / 'c.txt'
    a.write_bytes(b'hello world')
    b.write_bytes(b'hello world')
    c.write_bytes(b'different')

    groups = utils.find_duplicates([str(d)], min_size=1)
    assert isinstance(groups, list)
    # should find at least one duplicate group for a.txt/b.txt
    assert any(len(g['files']) >= 2 for g in groups)
