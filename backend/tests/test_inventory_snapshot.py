"""Only freshly created owned directories are observed by this test module."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from backend import disk_model as dm
from backend import inventory_snapshot as bridge
from backend.observation_session import SelectionError, observe_once, select_root

POSIX = pytest.mark.skipif(not dm.traversal_supported(), reason="Owned descriptor-relative observation is unsupported")


def owned_root(tmp_path):
    root = tmp_path / "owned-project"
    root.mkdir()
    (root / "Photos").mkdir()
    (root / "Photos" / "Trip.jpg").write_bytes(b"owned illustrative file")
    (root / "Notes.txt").write_text("owned note")
    return root


@POSIX
def test_owned_observation_projects_only_display_metadata(tmp_path, monkeypatch):
    root = owned_root(tmp_path)
    monkeypatch.setattr(os, "read", lambda *_args: pytest.fail("metadata bridge read file content"))
    selection = select_root(str(root))
    result = bridge.observe_snapshot(selection, "Illustrative owned folder")
    assert result["state"] == "observed"
    snapshot = result["snapshot"]
    assert snapshot["source"]["coverage"] == "complete"
    assert snapshot["entries"][2]["kind"] == "directory"
    assert all(set(row) == {"path", "kind", "status", "logical_bytes"} for row in snapshot["entries"])
    assert str(root) not in json.dumps(snapshot)
    for forbidden in ("device", "inode", "fingerprint", "authenticated", "execution_authority", "allocated_bytes"):
        assert forbidden not in json.dumps(snapshot)
    assert selection.state == "spent"
    with pytest.raises(SelectionError):
        bridge.observe_snapshot(selection, "Same selection")


@POSIX
def test_partial_owned_symlink_and_placeholder_are_displayed_unselected(tmp_path):
    root = owned_root(tmp_path)
    (root / "Alias").symlink_to(root / "Photos", target_is_directory=True)
    (root / "Unhydrated.icloud").write_text("owned placeholder marker")
    result = bridge.observe_snapshot(select_root(str(root)), "Owned partial")
    assert result["state"] == "partial"
    assert result["snapshot"]["source"]["coverage"] == "partial"
    rows = {row["path"]: row for row in result["snapshot"]["entries"]}
    assert rows["Alias"]["kind"] == "symlink" and rows["Alias"]["status"] == "unsupported"
    assert rows["Unhydrated.icloud"]["status"] == "unsupported"
    assert result["snapshot"]["gaps"]["exclusions"]


@POSIX
@pytest.mark.parametrize("action", ["cancel", "revoke", "failure"])
def test_terminal_observation_never_supplies_snapshot(tmp_path, action):
    selection = select_root(str(owned_root(tmp_path)))
    if action == "cancel":
        out = bridge.observe_snapshot(selection, "Owned", cancel=lambda: True)
    elif action == "revoke":
        def revoke():
            selection.revoke()
            return False
        out = bridge.observe_snapshot(selection, "Owned", cancel=revoke)
    else:
        def fail():
            raise ValueError("owned deliberate callback failure")
        out = bridge.observe_snapshot(selection, "Owned", cancel=fail)
    assert out["snapshot"] is None
    assert out["state"] == {"cancel": "cancelled", "revoke": "revoked", "failure": "failed"}[action]


@pytest.mark.parametrize("label", [None, "", " ", "x" * 241, "bad\nlabel", "bad\x85label", "bad\u2028label", "\ud800"])
def test_label_rejects_before_observation(monkeypatch, label):
    monkeypatch.setattr(bridge, "observe_once", lambda *_args, **_kwargs: pytest.fail("bad label consumed selection"))
    with pytest.raises((ValueError, UnicodeError)):
        bridge.observe_snapshot(None, label)


def test_untrusted_dictionary_is_not_a_live_selection():
    with pytest.raises(SelectionError):
        bridge.observe_snapshot({"observation": {}, "state": "observed"}, "Forged")


def test_unsupported_platform_abstains(monkeypatch):
    monkeypatch.setattr(dm, "traversal_supported", lambda: False)
    result = bridge.observe_snapshot(select_root("owned but not opened"), "Owned unsupported")
    assert result == {"state": "unsupported", "snapshot": None}


@POSIX
def test_unrepresentable_native_name_rejects_entire_projection(tmp_path):
    root = owned_root(tmp_path)
    (root / "name\\not-a-separator").write_text("owned")
    selection = select_root(str(root))
    with pytest.raises(ValueError, match="relative"):
        bridge.observe_snapshot(selection, "Owned")
    assert selection.state == "spent"


@POSIX
def test_fresh_owned_producer_is_accepted_by_browser_contract(tmp_path):
    if not shutil.which("node"):
        pytest.skip("Node unavailable for cross-language contract")
    snapshot = bridge.observe_snapshot(select_root(str(owned_root(tmp_path))), "Owned browser contract")["snapshot"]
    script = """
    globalThis.crypto = require('node:crypto').webcrypto;
    const C = require('./frontend/inventory-snapshot-model.js');
    const M = require('./frontend/manual-planning-model.js');
    const s = C.parse(require('node:fs').readFileSync(0,'utf8'));
    const c = C.add(C.empty(), s, 'Offline record');
    const p = C.buildPlan(c,[{source_id:c.records[0].id,path:'Photos'}],'Owned project','2026-10-09T07:00:00Z');
    if (M.strictParse(M.exportPlan(p)).items[0].location.path_text !== 'Photos') process.exit(1);
    console.log('owned producer / parser / manual plan roundtrip passed');
    """
    run = subprocess.run(["node", "-e", script], input=json.dumps(snapshot), text=True, capture_output=True, cwd=Path(__file__).resolve().parents[2], timeout=15)
    assert run.returncode == 0, run.stderr


def test_import_has_no_application_or_store_side_effects():
    script = "import sys; import backend.inventory_snapshot; assert 'backend.app' not in sys.modules; assert 'backend.op_store' not in sys.modules; assert 'backend.fs_ops' not in sys.modules"
    subprocess.run([sys.executable, "-c", script], check=True, cwd=Path(__file__).resolve().parents[2], timeout=15)
