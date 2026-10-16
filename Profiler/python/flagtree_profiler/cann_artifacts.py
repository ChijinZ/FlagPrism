"""Retain CANN SDK output before removing its owned temporary session directory.

This module copies opaque files. It does not interpret SDK clocks or task IDs.
The completed retention manifest is the prerequisite for temporary cleanup.
"""
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
import zipfile

_TREE = "raw/native/cann_sdk"
_MANIFEST = "raw/native/cann-sdk-retention.json"
_ARCHIVE = "raw/native/cann_sdk.zip"
_ARCHIVE_THRESHOLD_BYTES = 8 * 1024 * 1024
_ARCHIVE_COMPRESSION_LEVEL = 6


def _true(value):
    return str(value).strip().lower() in {"1", "true", "on", "yes"}


def _path(value):
    if not isinstance(value, (str, os.PathLike)) or not str(value).strip():
        raise ValueError("CANN SDK output path must be nonempty")
    if ".." in Path(value).parts:
        raise ValueError("CANN artifact paths cannot contain parent traversal")
    path = Path(os.path.abspath(value))
    for component in reversed((path, *path.parents)):
        if component.is_symlink():
            raise ValueError(
                f"CANN artifact path contains a symlink: {component}")
    return path


def _metadata(base):
    path = Path(base).with_suffix(".meta.json")
    if not path.exists() and not path.is_symlink():
        return None
    path = _path(path)
    data = path.read_bytes()
    metadata = json.loads(data)
    if not isinstance(metadata, dict):
        raise ValueError("CANN capture metadata must be an object")
    if metadata.get("backend") != "cann":
        return None
    config = metadata.get("config", {})
    if not isinstance(config, dict):
        raise ValueError("CANN capture config must be an object")
    configured = config.get("aclprof_output_path") or config.get("output_path")
    if not configured:
        if any(
                _true(config.get(key, False))
                for key in ("aclprof_runtime_enabled",
                            "cann_aclprof_runtime")):
            raise ValueError("Enabled CANN SDK capture has no output path")
        return None
    return {
        "metadata_path": str(path),
        "metadata_sha256": hashlib.sha256(data).hexdigest(),
        "config": config,
        "configured_path": str(configured),
        "source": _path(configured),
    }


def _file_digest(path):
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(
                f"CANN SDK artifact is not a regular file: {path}")
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
        after = os.fstat(stream.fileno())
    if (before.st_size, before.st_mtime_ns) != (after.st_size,
                                                after.st_mtime_ns):
        raise RuntimeError(f"CANN SDK artifact changed while reading: {path}")
    return {"sha256": digest.hexdigest(), "bytes": after.st_size}


def _inventory(root):
    root = _path(root)
    if not root.is_dir():
        raise FileNotFoundError(
            f"CANN SDK output directory is missing: {root}")
    directories, files = [], {}
    for directory, names, filenames in os.walk(root, followlinks=False):
        for name in sorted(names + filenames):
            path = _path(Path(directory) / name)
            mode = path.lstat().st_mode
            relative = path.relative_to(root).as_posix()
            if stat.S_ISDIR(mode):
                directories.append(relative)
            elif stat.S_ISREG(mode):
                files[relative] = _file_digest(path)
            else:
                raise ValueError(
                    f"CANN SDK artifact is not regular data: {path}")
    return {
        "directories": sorted(directories),
        "files": dict(sorted(files.items()))
    }


def _copy_file(source, destination):
    descriptor = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as original:
        if not stat.S_ISREG(os.fstat(original.fileno()).st_mode):
            raise ValueError(
                f"CANN SDK artifact is not regular data: {source}")
        with destination.open("xb") as retained:
            shutil.copyfileobj(original, retained)


def _same_tree(root, expected):
    if _inventory(root) != expected:
        raise RuntimeError(
            f"CANN SDK retention inventory/hash mismatch: {root}")


def _safe_relative(relative):
    if (not isinstance(relative, str) or not relative or "\\" in relative
            or ":" in relative or Path(relative).is_absolute()
            or ".." in Path(relative).parts
            or Path(relative).as_posix() != relative or relative == "."):
        raise ValueError("Invalid relative CANN SDK archive path")
    return relative


def _verify_archive(path, expected, archive_digest=None):
    """Verify every member without extracting attacker-controlled paths."""
    path = _path(path)
    if archive_digest is not None and _file_digest(path) != archive_digest:
        raise RuntimeError("CANN SDK archive hash/size mismatch")
    names, directories, files = set(), [], {}
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            name = member.filename
            relative = _safe_relative(name[:-1] if member.is_dir() else name)
            if relative in names:
                raise ValueError("Duplicate CANN SDK archive member")
            names.add(relative)
            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode) or (stat.S_IFMT(mode)
                                      not in (0, stat.S_IFREG, stat.S_IFDIR)):
                raise ValueError("Nonregular CANN SDK archive member")
            if stat.S_IFMT(mode) and stat.S_ISDIR(mode) != member.is_dir():
                raise ValueError("CANN SDK archive member type mismatch")
            if member.is_dir():
                if relative not in expected['directories'] or member.file_size:
                    raise ValueError("Unexpected CANN SDK archive directory")
                directories.append(relative)
                continue
            if relative not in expected['files']:
                raise ValueError("Unexpected CANN SDK archive member")
            target = expected['files'][relative]
            if member.file_size != target['bytes']:
                raise RuntimeError("CANN SDK archive member size mismatch")
            size, digest = 0, hashlib.sha256()
            with archive.open(member) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    size += len(block)
                    if size > target['bytes']:
                        raise RuntimeError(
                            "CANN SDK archive member exceeds declared size")
                    digest.update(block)
            files[relative] = {'bytes': size, 'sha256': digest.hexdigest()}
    if {
            'directories': sorted(directories),
            'files': dict(sorted(files.items()))
    } != expected:
        raise RuntimeError("CANN SDK archive member inventory/hash mismatch")


def _retain_archive(source, output, inventory, manifest):
    target, manifest_path = output / _ARCHIVE, output / _MANIFEST
    staging = Path(
        tempfile.mkdtemp(prefix='.cann-sdk-archive-', dir=target.parent))
    archive = staging / 'cann_sdk.zip'
    with zipfile.ZipFile(archive,
                         'x',
                         compression=zipfile.ZIP_DEFLATED,
                         compresslevel=_ARCHIVE_COMPRESSION_LEVEL,
                         allowZip64=True) as retained:
        for relative in inventory['directories']:
            retained.write(source / relative, relative + '/')
        for relative in inventory['files']:
            retained.write(source / relative, relative)
    archive_digest = _file_digest(archive)
    _verify_archive(archive, inventory, archive_digest)
    _same_tree(source, inventory)
    manifest.update(schema_version=2,
                    storage='zip_deflate',
                    bundle_capture_root=_ARCHIVE,
                    mapping={
                        'source': manifest['source_capture_root'],
                        'bundle_relative': _ARCHIVE
                    },
                    archive=dict(bundle_relative=_ARCHIVE,
                                 compression='ZIP_DEFLATED',
                                 compresslevel=_ARCHIVE_COMPRESSION_LEVEL,
                                 **archive_digest),
                    files=[
                        dict(source_relative=relative,
                             archive_member=relative,
                             **digest)
                        for relative, digest in inventory['files'].items()
                    ])
    # Exclusive hard links never replace an existing archive or manifest. Keep
    # staging and source on every failure so partial retention is inspectable.
    staged_manifest = staging / 'manifest.json'
    staged_manifest.write_text(
        json.dumps(manifest, separators=(',', ':')) + '\n')
    os.link(archive, target)
    os.link(staged_manifest, manifest_path)
    shutil.rmtree(staging)
    return manifest


def retain_native_capture(base, output):
    """Copy one native CANN session tree and return its complete manifest.

    Missing metadata, other backends and disabled SDK captures without an output
    path return None. Existing destinations, missing data and failed copies
    raise; the original SDK directory is never removed by this function.
    """
    metadata = _metadata(base)
    if metadata is None:
        return None
    source, output = metadata["source"], _path(output)
    if source == output or source in output.parents or output in source.parents:
        raise ValueError("CANN SDK source and bundle output must be disjoint")
    target, manifest_path = output / _TREE, output / _MANIFEST
    _path(target)
    _path(manifest_path)
    archive_path = _path(output / _ARCHIVE)
    if target.exists() or archive_path.exists() or manifest_path.exists():
        raise FileExistsError(
            f"CANN SDK retention destination already exists: {target}")
    inventory = _inventory(source)
    if not inventory["files"]:
        raise FileNotFoundError(
            f"CANN SDK output contains no data files: {source}")
    source_stat = source.stat()
    target.parent.mkdir(parents=True, exist_ok=True)
    config = metadata["config"]
    owned_root = _path(config["aclprof_output_root"]) if config.get(
        "aclprof_output_root") else None
    manifest = {
        "schema_version":
        1,
        "status":
        "complete",
        "backend":
        "cann",
        "metadata_path":
        metadata["metadata_path"],
        "metadata_sha256":
        metadata["metadata_sha256"],
        "source_configured_path":
        metadata["configured_path"],
        "source_capture_root":
        str(source),
        "source_owned_root":
        str(owned_root) if owned_root else None,
        "source_capture_identity": {
            "device": source_stat.st_dev,
            "inode": source_stat.st_ino
        },
        "temporary":
        _true(config.get("aclprof_output_path_temporary", False)),
        "bundle_capture_root":
        _TREE,
        "mapping": {
            "source": str(source),
            "bundle_relative": _TREE
        },
        "directories":
        inventory["directories"],
        "files": [{
            "source_relative": relative,
            "bundle_relative": f"{_TREE}/{relative}",
            **digest
        } for relative, digest in inventory["files"].items()],
    }
    if sum(row["bytes"]
           for row in inventory["files"].values()) >= _ARCHIVE_THRESHOLD_BYTES:
        return _retain_archive(source, output, inventory, manifest)
    with tempfile.TemporaryDirectory(prefix=".cann-sdk-copy-",
                                     dir=target.parent) as staging:
        staging = Path(staging)
        tree = staging / "tree"
        tree.mkdir()
        for relative in inventory["directories"]:
            (tree / relative).mkdir(parents=True, exist_ok=True)
        for relative in inventory["files"]:
            _copy_file(source / relative, tree / relative)
        _same_tree(tree, inventory)
        _same_tree(source, inventory)
        # mkdir is an exclusive claim, so even an empty existing destination is
        # never overwritten. Only a completed, verified tree receives a manifest.
        target.mkdir()
        for child in tree.iterdir():
            child.rename(target / child.name)
        _same_tree(target, inventory)
        staged_manifest = staging / "manifest.json"
        staged_manifest.write_text(json.dumps(manifest, indent=2) + "\n")
        os.link(staged_manifest, manifest_path)
    return manifest


def _expected_inventory(manifest):
    files = {}
    for row in manifest.get("files", []):
        relative = row["source_relative"]
        _safe_relative(relative)
        path = Path(relative)
        mapping_valid = (row.get("archive_member") == relative
                         if manifest.get("schema_version") == 2 else
                         row.get("bundle_relative") == f"{_TREE}/{relative}")
        if (not relative or path.is_absolute() or ".." in path.parts
                or path.as_posix() != relative or relative in files
                or not mapping_valid):
            raise ValueError(
                "Invalid relative CANN SDK retention file mapping")
        files[relative] = {"sha256": row["sha256"], "bytes": row["bytes"]}
    if not files:
        raise ValueError("CANN SDK retention manifest contains no files")
    directories = manifest.get("directories", [])
    if len(set(directories)) != len(directories):
        raise ValueError("Duplicate CANN SDK retention directory")
    for relative in directories:
        _safe_relative(relative)
    return {"directories": sorted(directories), "files": files}


def cleanup_retained_native_capture(base, output):
    """Remove only a verified, explicitly temporary CANN session directory.

    Return True when the source session was removed, False for captures that do
    not authorize cleanup or whose source has already gone. A failed retention
    verification raises before any source removal.
    """
    metadata = _metadata(base)
    if metadata is None:
        return False
    config = metadata["config"]
    if not _true(config.get("aclprof_output_path_temporary", False)):
        return False
    output = _path(output)
    manifest_path = _path(output / _MANIFEST)
    manifest = json.loads(manifest_path.read_text())
    version = manifest.get("schema_version")
    storage_path = _ARCHIVE if version == 2 else _TREE
    if (version not in (1, 2) or manifest.get("status") != "complete"
            or manifest.get("backend") != "cann"
            or manifest.get("temporary") is not True
            or manifest.get("bundle_capture_root") != storage_path
            or manifest.get("metadata_path") != metadata["metadata_path"]
            or manifest.get("metadata_sha256") != metadata["metadata_sha256"]):
        raise ValueError(
            "CANN SDK retention manifest does not match this capture")
    expected = _expected_inventory(manifest)
    if version == 2:
        archive = manifest.get('archive') or {}
        if (manifest.get('storage') != 'zip_deflate'
                or archive.get('bundle_relative') != _ARCHIVE
                or archive.get('compression') != 'ZIP_DEFLATED'):
            raise ValueError('Invalid CANN SDK archive representation')
        _verify_archive(output / _ARCHIVE, expected, {
            'bytes': archive['bytes'],
            'sha256': archive['sha256']
        })
    else:
        _same_tree(output / _TREE, expected)
    source = metadata["source"]
    if not config.get("aclprof_output_root"):
        raise ValueError(
            "Temporary CANN cleanup requires an explicit owned root")
    owned_root = _path(config["aclprof_output_root"])
    if (source.parent != owned_root or
            not re.fullmatch(r"flagtree_profiler_session_[0-9]+", source.name)
            or manifest.get("source_capture_root") != str(source)
            or manifest.get("source_owned_root") != str(owned_root)
            or manifest.get("mapping") != {
                "source": str(source),
                "bundle_relative": storage_path
            } or source == output or source in output.parents
            or output in source.parents):
        raise ValueError(
            "Temporary CANN cleanup requires its isolated session directory")
    if not source.exists():
        return False
    source_stat = source.stat()
    if manifest.get("source_capture_identity") != {
            "device": source_stat.st_dev,
            "inode": source_stat.st_ino
    }:
        raise ValueError("Temporary CANN session directory identity changed")
    _same_tree(source, expected)
    if not shutil.rmtree.avoids_symlink_attacks:
        raise RuntimeError(
            "Safe CANN temporary cleanup requires fd-based rmtree")
    shutil.rmtree(source)
    try:
        owned_root.rmdir()
    except OSError as error:
        if error.errno not in (errno.ENOTEMPTY, errno.EEXIST):
            raise
    return True
