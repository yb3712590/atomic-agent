import hashlib
import json

import pytest

from atomic_agent.artifacts import ArtifactWriter, ArtifactWriterConfig, ArtifactWriterError


def make_writer(tmp_path):
    root = tmp_path / "artifacts"
    root.mkdir()
    return ArtifactWriter(
        ArtifactWriterConfig(
            artifact_root=root,
            artifact_ref_prefix="artifact://run_001",
        )
    )


def test_artifact_writer_rejects_missing_root(tmp_path):
    config = ArtifactWriterConfig(
        artifact_root=tmp_path / "missing",
        artifact_ref_prefix="artifact://run_001",
    )

    with pytest.raises(ArtifactWriterError):
        ArtifactWriter(config)


def test_artifact_writer_rejects_file_root(tmp_path):
    root = tmp_path / "artifact-file"
    root.write_text("not a directory", encoding="utf-8")
    config = ArtifactWriterConfig(artifact_root=root, artifact_ref_prefix="artifact://run_001")

    with pytest.raises(ArtifactWriterError):
        ArtifactWriter(config)


def test_artifact_writer_rejects_empty_ref_prefix(tmp_path):
    root = tmp_path / "artifacts"
    root.mkdir()

    with pytest.raises(ArtifactWriterError):
        ArtifactWriter(ArtifactWriterConfig(artifact_root=root, artifact_ref_prefix=""))


@pytest.mark.parametrize("relative_path", ["", " ", "/absolute.txt", "../escape.txt", "nested/../../escape.txt"])
def test_artifact_writer_rejects_unsafe_relative_paths(tmp_path, relative_path):
    writer = make_writer(tmp_path)

    with pytest.raises(ArtifactWriterError):
        writer.write_text(relative_path, "content")


def test_artifact_writer_rejects_existing_symlink_escape(tmp_path):
    writer = make_writer(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    link = tmp_path / "artifacts" / "link.txt"
    try:
        link.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"symlink creation is unavailable: {error}")

    with pytest.raises(ArtifactWriterError):
        writer.write_text("link.txt", "escaped")

    assert outside.read_text(encoding="utf-8") == "outside"


def test_write_text_creates_real_artifact_with_hash(tmp_path):
    writer = make_writer(tmp_path)

    payload = writer.write_text("provider/turn_000001.txt", "hello", truncated_in_observation=False)

    artifact_path = tmp_path / "artifacts" / "provider" / "turn_000001.txt"
    assert artifact_path.read_text(encoding="utf-8") == "hello"
    assert payload == {
        "artifact_ref": "artifact://run_001/provider/turn_000001.txt",
        "sha256": "sha256:" + hashlib.sha256(b"hello").hexdigest(),
        "size_bytes": 5,
        "truncated_in_observation": False,
    }


def test_write_json_uses_stable_utf8_json(tmp_path):
    writer = make_writer(tmp_path)
    data = {"z": 1, "a": "中文"}

    payload = writer.write_json("observations/tool_000001.json", data, truncated_in_observation=True)

    artifact_path = tmp_path / "artifacts" / "observations" / "tool_000001.json"
    expected_text = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert artifact_path.read_text(encoding="utf-8") == expected_text
    assert payload["artifact_ref"] == "artifact://run_001/observations/tool_000001.json"
    assert payload["sha256"] == "sha256:" + hashlib.sha256(expected_text.encode("utf-8")).hexdigest()
    assert payload["size_bytes"] == len(expected_text.encode("utf-8"))
    assert payload["truncated_in_observation"] is True
