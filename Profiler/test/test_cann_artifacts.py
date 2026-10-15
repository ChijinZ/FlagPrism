"""CPU copy/verify/cleanup contracts for owned CANN SDK session output."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def helper():
    path = Path(__file__).resolve(
    ).parents[1] / "python/flagtree_profiler/cann_artifacts.py"
    spec = importlib.util.spec_from_file_location("cann_artifacts_under_test",
                                                  path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def capture(tmp_path):
    root = tmp_path / "sdk-owned-root"
    source = root / "flagtree_profiler_session_7"
    (source / "PROF_7/host/sqlite").mkdir(parents=True)
    (source / "PROF_7/device_0/empty").mkdir(parents=True)
    (source / "PROF_7/host/sqlite/runtime.db"
     ).write_bytes(b"opaque sqlite bytes\x00\xff")
    (source / "PROF_7/info.json").write_text('{"native":true}')
    base, output = tmp_path / "capture", tmp_path / "bundle"
    metadata = {
        "backend": "cann",
        "config": {
            "aclprof_runtime_enabled": "true",
            "aclprof_output_path": str(source),
            "aclprof_output_root": str(root),
            "aclprof_output_path_temporary": "true",
        }
    }
    base.with_suffix(".meta.json").write_text(json.dumps(metadata))
    return base, output, source, root, metadata


def write_metadata(base, metadata):
    base.with_suffix(".meta.json").write_text(json.dumps(metadata))


@pytest.mark.parametrize("metadata", [
    None, {
        "backend": "cuda"
    }, {
        "backend": "cann",
        "config": {}
    }, {
        "backend": "cann",
        "config": {
            "aclprof_runtime_enabled": "false"
        }
    }
])
def test_absent_or_unrelated_capture_is_noop(helper, tmp_path, metadata):
    base, output = tmp_path / "capture", tmp_path / "bundle"
    if metadata is not None:
        write_metadata(base, metadata)
    assert helper.retain_native_capture(base, output) is None
    assert helper.cleanup_retained_native_capture(base, output) is False
    assert not output.exists()


def test_enabled_sdk_missing_output_path_is_explicit(helper, tmp_path):
    base = tmp_path / "capture"
    write_metadata(base, {
        "backend": "cann",
        "config": {
            "cann_aclprof_runtime": "yes"
        }
    })
    with pytest.raises(ValueError, match="no output path"):
        helper.retain_native_capture(base, tmp_path / "bundle")


def test_retains_opaque_tree_with_original_and_bundle_paths(helper, capture):
    base, output, source, root, _ = capture
    manifest = helper.retain_native_capture(base, output)
    assert source.exists()
    assert manifest == json.loads(
        (output / "raw/native/cann-sdk-retention.json").read_text())
    assert manifest["status"] == "complete"
    assert manifest["source_owned_root"] == str(root)
    assert manifest["source_capture_root"] == str(source)
    assert manifest["mapping"] == {
        "source": str(source),
        "bundle_relative": "raw/native/cann_sdk"
    }
    assert (output / "raw/native/cann_sdk/PROF_7/device_0/empty").is_dir()
    for row in manifest["files"]:
        original = (source / row["source_relative"]).read_bytes()
        assert (output / row["bundle_relative"]).read_bytes() == original
        assert row["sha256"] == hashlib.sha256(original).hexdigest()
        assert row["bytes"] == len(original)


def test_output_path_alias_and_temporary_boolean(helper, capture):
    base, output, source, root, metadata = capture
    config = metadata["config"]
    config["output_path"] = config.pop("aclprof_output_path")
    config["aclprof_output_path_temporary"] = True
    write_metadata(base, metadata)
    helper.retain_native_capture(base, output)
    assert helper.cleanup_retained_native_capture(base, output) is True
    assert not source.exists() and not root.exists()
    assert helper.cleanup_retained_native_capture(base, output) is False


@pytest.mark.parametrize("temporary", [False, "false", "0", "off"])
def test_user_owned_non_temporary_output_is_never_deleted(
        helper, capture, temporary):
    base, output, source, root, metadata = capture
    metadata["config"]["aclprof_output_path_temporary"] = temporary
    write_metadata(base, metadata)
    helper.retain_native_capture(base, output)
    assert helper.cleanup_retained_native_capture(base, output) is False
    assert source.exists() and root.exists()


def test_cleanup_only_owned_session_and_preserve_sibling(helper, capture):
    base, output, source, root, _ = capture
    sibling = root / "flagtree_profiler_session_8"
    sibling.mkdir()
    (sibling / "other.db").write_bytes(b"another session")
    helper.retain_native_capture(base, output)
    assert helper.cleanup_retained_native_capture(base, output)
    assert not source.exists()
    assert (sibling / "other.db").read_bytes() == b"another session"
    assert root.exists()


@pytest.mark.parametrize("kind", ["file", "directory", "internal"])
def test_source_symlink_is_rejected_without_touching_original(
        helper, capture, tmp_path, kind):
    base, output, source, _, _ = capture
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret").write_text("keep")
    target = outside / "secret" if kind == "file" else source / "PROF_7" if kind == "internal" else outside
    (source / "link").symlink_to(target, target_is_directory=target.is_dir())
    with pytest.raises(ValueError, match="symlink"):
        helper.retain_native_capture(base, output)
    assert (outside / "secret").read_text() == "keep"
    assert source.exists()
    assert not (output / "raw/native/cann-sdk-retention.json").exists()


@pytest.mark.parametrize("empty", [False, True])
def test_missing_or_empty_sdk_output_fails(helper, capture, empty):
    base, output, source, _, _ = capture
    import shutil
    shutil.rmtree(source)
    if empty:
        source.mkdir()
    with pytest.raises(FileNotFoundError, match="CANN SDK output"):
        helper.retain_native_capture(base, output)
    assert not (output / "raw/native/cann-sdk-retention.json").exists()


@pytest.mark.parametrize("destination",
                         ["cann_sdk", "cann-sdk-retention.json"])
def test_existing_destination_is_not_overwritten(helper, capture, destination):
    base, output, source, _, _ = capture
    path = output / "raw/native" / destination
    path.parent.mkdir(parents=True)
    path.write_bytes(b"keep destination")
    with pytest.raises(FileExistsError):
        helper.retain_native_capture(base, output)
    assert path.read_bytes() == b"keep destination"
    assert source.exists()


def test_existing_empty_target_directory_is_not_overwritten(helper, capture):
    base, output, source, _, _ = capture
    path = output / "raw/native/cann_sdk"
    path.mkdir(parents=True)
    with pytest.raises(FileExistsError):
        helper.retain_native_capture(base, output)
    assert list(path.iterdir()) == [] and source.exists()


def test_bundle_symlink_cannot_escape_capture(helper, capture, tmp_path):
    base, output, source, _, _ = capture
    outside = tmp_path / "outside"
    outside.mkdir()
    output.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        helper.retain_native_capture(base, output)
    assert not list(outside.iterdir()) and source.exists()


def test_copy_failure_retains_source_and_never_publishes_manifest(
        helper, capture, monkeypatch):
    base, output, source, _, _ = capture
    original = (source / "PROF_7/host/sqlite/runtime.db").read_bytes()

    def fail_copy(*args):
        raise OSError("injected copy I/O failure")

    monkeypatch.setattr(helper, "_copy_file", fail_copy)
    with pytest.raises(OSError, match="copy I/O failure"):
        helper.retain_native_capture(base, output)
    assert (source / "PROF_7/host/sqlite/runtime.db").read_bytes() == original
    assert not (output / "raw/native/cann-sdk-retention.json").exists()
    assert not (output / "raw/native/cann_sdk").exists()


@pytest.mark.parametrize("mutation", ["edit", "delete", "extra", "symlink"])
def test_bad_retained_tree_prevents_cleanup(helper, capture, mutation,
                                            tmp_path):
    base, output, source, _, _ = capture
    helper.retain_native_capture(base, output)
    tree = output / "raw/native/cann_sdk"
    file = tree / "PROF_7/info.json"
    if mutation == "edit":
        file.write_text("corrupt")
    elif mutation == "delete":
        file.unlink()
    elif mutation == "extra":
        (tree / "extra").write_text("new")
    else:
        outside = tmp_path / "outside"
        outside.write_text("keep")
        (tree / "link").symlink_to(outside)
    with pytest.raises((ValueError, RuntimeError), match="symlink|mismatch"):
        helper.cleanup_retained_native_capture(base, output)
    assert source.exists()


@pytest.mark.parametrize("mutation", ["edit", "extra"])
def test_sdk_tree_changes_after_copy_are_not_deleted(helper, capture,
                                                     mutation):
    base, output, source, _, _ = capture
    helper.retain_native_capture(base, output)
    path = source / ("PROF_7/info.json" if mutation == "edit" else "new.db")
    path.write_text("new SDK data")
    with pytest.raises(RuntimeError, match="mismatch"):
        helper.cleanup_retained_native_capture(base, output)
    assert path.read_text() == "new SDK data"


@pytest.mark.parametrize("problem",
                         ["wrong-name", "not-direct-child", "missing-root"])
def test_temporary_cleanup_does_not_guess_ownership(helper, capture, problem):
    base, output, source, root, metadata = capture
    if problem == "wrong-name":
        renamed = source.with_name("user-output")
        source.rename(renamed)
        source = renamed
        metadata["config"]["aclprof_output_path"] = str(source)
    elif problem == "not-direct-child":
        metadata["config"]["aclprof_output_root"] = str(root.parent)
    else:
        metadata["config"].pop("aclprof_output_root")
    write_metadata(base, metadata)
    helper.retain_native_capture(base, output)
    with pytest.raises(ValueError,
                       match="isolated session|explicit owned root"):
        helper.cleanup_retained_native_capture(base, output)
    assert source.exists()


def test_modified_metadata_cannot_redirect_cleanup(helper, capture):
    base, output, source, _, metadata = capture
    helper.retain_native_capture(base, output)
    metadata["unrelated_change"] = True
    write_metadata(base, metadata)
    with pytest.raises(ValueError, match="does not match"):
        helper.cleanup_retained_native_capture(base, output)
    assert source.exists()


def test_incomplete_manifest_prevents_cleanup(helper, capture):
    base, output, source, _, _ = capture
    manifest = helper.retain_native_capture(base, output)
    manifest["status"] = "copying"
    (output / "raw/native/cann-sdk-retention.json").write_text(
        json.dumps(manifest))
    with pytest.raises(ValueError, match="does not match"):
        helper.cleanup_retained_native_capture(base, output)
    assert source.exists()


def test_cleanup_requires_a_retention_manifest(helper, capture):
    base, output, source, _, _ = capture
    with pytest.raises(FileNotFoundError):
        helper.cleanup_retained_native_capture(base, output)
    assert source.exists()


def test_source_and_bundle_must_be_disjoint(helper, capture):
    base, _, source, _, _ = capture
    with pytest.raises(ValueError, match="disjoint"):
        helper.retain_native_capture(base, source / "bundle")
    assert not (source / "bundle").exists()


def test_parent_traversal_cannot_hide_a_symlink(helper, capture, tmp_path):
    base, output, source, _, metadata = capture
    link = tmp_path / "link"
    link.symlink_to(source.parent, target_is_directory=True)
    metadata["config"]["aclprof_output_path"] = str(link / ".." / source.name)
    write_metadata(base, metadata)
    with pytest.raises(ValueError, match="parent traversal"):
        helper.retain_native_capture(base, output)
    assert source.exists()


@pytest.mark.parametrize("temporary", [True, False])
def test_real_export_capture_retains_sdk_before_optional_cleanup(
        capture, temporary):
    from flagtree.profiler._capture import export_capture
    base, output, source, root, metadata = capture
    metadata["run_id"] = "1792036069252534137-7"
    metadata["session_name"] = str(base)
    metadata["config"]["aclprof_output_path_temporary"] = temporary
    write_metadata(base, metadata)
    base.with_suffix(".vendor.json").write_text(
        json.dumps({
            "backend": "cann",
            "associations": []
        }))
    expected = (source / "PROF_7/host/sqlite/runtime.db").read_bytes()
    export_capture(base, output)
    retained = output / "raw/native/cann_sdk/PROF_7/host/sqlite/runtime.db"
    assert retained.read_bytes() == expected
    manifest = json.loads((output / "manifest.json").read_text())
    relative = retained.relative_to(output).as_posix()
    assert manifest["files"][relative]["sha256"] == hashlib.sha256(
        expected).hexdigest()
    assert "raw/native/cann-sdk-retention.json" in manifest["files"]
    assert source.exists() is (not temporary)
    assert root.exists() is (not temporary)


@pytest.mark.parametrize("failure", ["write_manifest", "reconstruction"])
def test_real_export_failure_keeps_sdk_and_partial_bundle(
        capture, monkeypatch, failure):
    from flagtree.profiler import _capture, reconstruction
    base, output, source, _, _ = capture
    base.with_suffix(".vendor.json").write_text(
        json.dumps({
            "backend": "cann",
            "associations": []
        }))
    expected = (source / "PROF_7/host/sqlite/runtime.db").read_bytes()

    def fail(*args, **kwargs):
        raise RuntimeError("injected export completion failure")

    if failure == "write_manifest":
        monkeypatch.setattr(_capture._report, "write_manifest", fail)
    else:
        base.with_suffix(".observations.json").write_text(
            json.dumps({
                "captures": [],
                "observations": []
            }))
        monkeypatch.setattr(reconstruction, "write_view", fail)
    with pytest.raises(RuntimeError, match="export completion failure"):
        _capture.export_capture(base, output)
    assert (source / "PROF_7/host/sqlite/runtime.db").read_bytes() == expected
    assert (output / "raw/native/cann_sdk/PROF_7/host/sqlite/runtime.db"
            ).read_bytes() == expected
    assert (output / "raw/native/cann-sdk-retention.json").exists()
    assert not (output / "manifest.json").exists()


def test_zip_retains_every_member_and_empty_directory_then_cleans(
        helper, capture, monkeypatch):
    import zipfile
    monkeypatch.setattr(helper, '_ARCHIVE_THRESHOLD_BYTES', 1)
    base, output, source, root, _ = capture
    inventory = helper._inventory(source)
    manifest = helper.retain_native_capture(base, output)
    assert manifest['schema_version'] == 2
    assert manifest['storage'] == 'zip_deflate'
    assert not (output / 'raw/native/cann_sdk').exists()
    path = output / manifest['archive']['bundle_relative']
    with zipfile.ZipFile(path) as archive:
        for relative, digest in inventory['files'].items():
            data = archive.read(relative)
            assert data == (source / relative).read_bytes()
            assert hashlib.sha256(data).hexdigest() == digest['sha256']
        assert 'PROF_7/device_0/empty/' in archive.namelist()
    assert helper.cleanup_retained_native_capture(base, output) is True
    assert not source.exists() and not root.exists()
    assert helper.cleanup_retained_native_capture(base, output) is False


@pytest.mark.parametrize(
    'name', ['../escape', '/absolute', 'a/../escape', 'a\\escape', './escape'])
def test_unsafe_zip_members_rejected(helper, tmp_path, name):
    import zipfile
    path = tmp_path / 'bad.zip'
    with zipfile.ZipFile(path, 'x') as archive:
        archive.writestr(name, b'bytes')
    with pytest.raises(ValueError, match='relative'):
        helper._verify_archive(path, {'directories': [], 'files': {}})


@pytest.mark.parametrize('problem', [
    'duplicate', 'extra', 'missing', 'hash', 'directory', 'symlink', 'notzip'
])
def test_invalid_zip_never_authorizes_cleanup(helper, capture, monkeypatch,
                                              problem):
    import zipfile
    import stat
    monkeypatch.setattr(helper, '_ARCHIVE_THRESHOLD_BYTES', 1)
    base, output, source, _, _ = capture
    manifest = helper.retain_native_capture(base, output)
    path = output / manifest['archive']['bundle_relative']
    expected = helper._expected_inventory(manifest)
    if problem == 'notzip':
        path.write_bytes(b'not a zip')
    elif problem == 'hash':
        manifest['files'][0]['sha256'] = '0' * 64
    else:
        with zipfile.ZipFile(path, 'w') as archive:
            for relative in expected['directories']:
                if problem == 'directory' and relative == expected[
                        'directories'][0]:
                    continue
                archive.writestr(relative + '/', b'')
            for i, relative in enumerate(expected['files']):
                if problem == 'missing' and i == 0:
                    continue
                archive.writestr(relative, (source / relative).read_bytes())
            if problem == 'duplicate':
                relative = next(iter(expected['files']))
                with pytest.warns(UserWarning, match='Duplicate'):
                    archive.writestr(relative,
                                     (source / relative).read_bytes())
            if problem == 'extra':
                archive.writestr('unknown-file', b'new')
            if problem == 'symlink':
                info = zipfile.ZipInfo('link')
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(info, b'/outside')
    # Update only outer hash: inner member verification must still reject it.
    manifest['archive'].update(helper._file_digest(path))
    (output / 'raw/native/cann-sdk-retention.json').write_text(
        json.dumps(manifest))
    with pytest.raises((ValueError, RuntimeError, zipfile.BadZipFile)):
        helper.cleanup_retained_native_capture(base, output)
    assert source.exists()


def test_archive_outer_corruption_and_source_mutation_refuse_cleanup(
        helper, capture, monkeypatch):
    monkeypatch.setattr(helper, '_ARCHIVE_THRESHOLD_BYTES', 1)
    base, output, source, _, _ = capture
    manifest = helper.retain_native_capture(base, output)
    path = output / manifest['archive']['bundle_relative']
    original = path.read_bytes()
    path.write_bytes(original[:-1])
    with pytest.raises(RuntimeError, match='hash/size'):
        helper.cleanup_retained_native_capture(base, output)
    assert source.exists()
    path.write_bytes(original)
    (source / 'new SDK data').write_bytes(b'changed')
    with pytest.raises(RuntimeError, match='mismatch'):
        helper.cleanup_retained_native_capture(base, output)
    assert source.exists()


def test_archive_existing_destination_is_never_overwritten(
        helper, capture, monkeypatch):
    monkeypatch.setattr(helper, '_ARCHIVE_THRESHOLD_BYTES', 1)
    base, output, source, _, _ = capture
    target = output / 'raw/native/cann_sdk.zip'
    target.parent.mkdir(parents=True)
    target.write_bytes(b'keep')
    with pytest.raises(FileExistsError):
        helper.retain_native_capture(base, output)
    assert target.read_bytes() == b'keep' and source.exists()


def test_archive_verification_failure_preserves_staging_and_source(
        helper, capture, monkeypatch):
    monkeypatch.setattr(helper, '_ARCHIVE_THRESHOLD_BYTES', 1)
    base, output, source, _, _ = capture

    def fail(*args):
        raise RuntimeError('injected archive validation failure')

    monkeypatch.setattr(helper, '_verify_archive', fail)
    with pytest.raises(RuntimeError, match='archive validation'):
        helper.retain_native_capture(base, output)
    assert source.exists()
    assert list(
        (output / 'raw/native').glob('.cann-sdk-archive-*/cann_sdk.zip'))
    assert not (output / 'raw/native/cann-sdk-retention.json').exists()
    assert not (output / 'raw/native/cann_sdk.zip').exists()


def test_archive_changed_source_during_retention_is_not_committed(
        helper, capture, monkeypatch):
    monkeypatch.setattr(helper, '_ARCHIVE_THRESHOLD_BYTES', 1)
    base, output, source, _, _ = capture
    verify = helper._verify_archive

    def mutate(*args):
        verify(*args)
        (source /
         'PROF_7/info.json').write_bytes(b'changed after archive validation')

    monkeypatch.setattr(helper, '_verify_archive', mutate)
    with pytest.raises(RuntimeError, match='mismatch'):
        helper.retain_native_capture(base, output)
    assert source.exists()
    assert list(
        (output / 'raw/native').glob('.cann-sdk-archive-*/cann_sdk.zip'))
    assert not (output / 'raw/native/cann-sdk-retention.json').exists()


def test_zip_bad_member_crc_is_rejected_without_extraction(helper, tmp_path):
    import zipfile
    import struct
    path = tmp_path / 'bad-crc.zip'
    content = b'opaque contents'
    with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_STORED) as archive:
        archive.writestr('data', content)
    data = bytearray(path.read_bytes())
    name_length, extra_length = struct.unpack_from('<HH', data, 26)
    data[30 + name_length + extra_length] ^= 1
    path.write_bytes(data)
    expected = {
        'directories': [],
        'files': {
            'data': {
                'bytes': len(content),
                'sha256': hashlib.sha256(content).hexdigest()
            }
        }
    }
    with pytest.raises(zipfile.BadZipFile, match='CRC'):
        helper._verify_archive(path, expected, helper._file_digest(path))
    assert not (tmp_path / 'data').exists()


@pytest.mark.parametrize('temporary', [True, False])
def test_real_export_uses_archive_threshold_and_verifies_before_cleanup(
        capture, temporary):
    import zipfile
    from flagtree.profiler._capture import export_capture
    base, output, source, _, metadata = capture
    metadata['config']['aclprof_output_path_temporary'] = temporary
    write_metadata(base, metadata)
    large = b'opaque SDK retained bytes\x00\xff' * 350000
    (source / 'PROF_7/large.db').write_bytes(large)
    base.with_suffix('.vendor.json').write_text(
        json.dumps({
            'backend': 'cann',
            'associations': []
        }))
    export_capture(base, output)
    retention = json.loads(
        (output / 'raw/native/cann-sdk-retention.json').read_text())
    assert retention['schema_version'] == 2
    archive_path = output / retention['archive']['bundle_relative']
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.read('PROF_7/large.db') == large
    bundle = json.loads((output / 'manifest.json').read_text())
    assert bundle['files']['raw/native/cann_sdk.zip'][
        'sha256'] == hashlib.sha256(archive_path.read_bytes()).hexdigest()
    assert not (output / 'raw/native/cann_sdk').exists()
    assert source.exists() is (not temporary)


def test_real_archive_export_completion_failure_preserves_original(
        capture, monkeypatch):
    from flagtree.profiler import _capture
    base, output, source, _, _ = capture
    (source / 'PROF_7/large.db').write_bytes(b'opaque SDK bytes' * 600000)
    base.with_suffix('.vendor.json').write_text(
        json.dumps({
            'backend': 'cann',
            'associations': []
        }))

    def fail(*args):
        raise RuntimeError(
            'injected completion failure after archive retention')

    monkeypatch.setattr(_capture._report, 'write_manifest', fail)
    with pytest.raises(RuntimeError, match='completion failure'):
        _capture.export_capture(base, output)
    assert source.exists()
    assert (output / 'raw/native/cann_sdk.zip').exists()
    assert (output / 'raw/native/cann-sdk-retention.json').exists()
    assert not (output / 'manifest.json').exists()
