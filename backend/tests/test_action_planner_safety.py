"""Filesystem-boundary regression tests for typed action validation."""

import os

import pytest

from backend.action_planner import validate_actions


def _move(source, destination):
    return {
        "action_type": "move",
        "source": str(source),
        "destination": str(destination),
        "confidence": 1.0,
    }


def _symlink_or_skip(link, target):
    try:
        link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks unavailable in test environment: {exc}")


def test_validate_actions_accepts_normal_path_inside_root(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    source = root / "a.txt"
    source.write_text("a", encoding="utf-8")
    destination = root / "sorted" / "a.txt"

    planned, rejected = validate_actions([_move(source, destination)], [str(root)])

    assert rejected == []
    assert len(planned) == 1
    assert planned[0]["from"] == os.path.abspath(source)
    assert planned[0]["to"] == os.path.abspath(destination)


def test_validate_actions_rejects_source_through_symlink_outside_root(tmp_path):
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    escape = root / "escape"
    _symlink_or_skip(escape, outside)

    planned, rejected = validate_actions(
        [_move(escape / "secret.txt", root / "sorted" / "secret.txt")],
        [str(root)],
    )

    assert planned == []
    assert rejected
    assert rejected[0]["error"] == "move paths must remain within scan roots"


def test_validate_actions_rejects_missing_destination_below_symlink_escape(tmp_path):
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    source = root / "a.txt"
    source.write_text("a", encoding="utf-8")
    escape = root / "escape"
    _symlink_or_skip(escape, outside)

    planned, rejected = validate_actions(
        [_move(source, escape / "new" / "a.txt")],
        [str(root)],
    )

    assert planned == []
    assert rejected
    assert rejected[0]["error"] == "move paths must remain within scan roots"


def test_validate_actions_accepts_paths_through_an_allowed_symlink_root(tmp_path):
    real_root = tmp_path / "real-root"
    real_root.mkdir()
    source = real_root / "a.txt"
    source.write_text("a", encoding="utf-8")
    exposed_root = tmp_path / "exposed-root"
    _symlink_or_skip(exposed_root, real_root)

    planned, rejected = validate_actions(
        [_move(exposed_root / "a.txt", exposed_root / "sorted" / "a.txt")],
        [str(exposed_root)],
    )

    assert rejected == []
    assert len(planned) == 1
