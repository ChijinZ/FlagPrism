"""Re-read build, source and external resource identities before source mutation."""
import hashlib
import json
from pathlib import Path

SOURCE = "bishengir/lib/Dialect/HIVM/Transforms/TileAndBindSubBlock.cpp"
SOURCE_SHA = "c33d6effd6a128a16126a4ee1f1c511754d1b045157133a664baa63607ad4d11"
TEMPLATES = {"meta_op.aic.bc", "meta_op.aiv.bc", "meta_op.mix.aic.bc", "meta_op.mix.aiv.bc", "host.bc"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def validate(prefix, replay):
    source = prefix / "source/AscendNPU-IR"
    compiler = prefix / "install-unmodified/bin/bishengir-compile"
    original_path = prefix / "build-receipt.json"
    original = json.loads(original_path.read_text())
    compat_path = prefix / "build-compat-receipt.json"
    build = json.loads(compat_path.read_text()) if compat_path.exists() else original
    require(build["state"] in ("unmodified-tool-ready", "legality-unmodified-tool-ready"), "Build is not a legality-unmodified baseline")
    require(Path(build["compiler"]).resolve() == compiler.resolve() and
            build["compiler_sha256"] == sha(compiler) == replay["compiler_sha256"],
            "Actual build/compiler/replay identity mismatch")
    require(sha(source / SOURCE) == SOURCE_SHA, "Legality source changed before repair")
    if "utils_compat_sha256" in build:
        require(sha(source / "bishengir/lib/Dialect/Tensor/Transforms/PropagateReshape/Utils.cpp") == build["utils_compat_sha256"], "Compatibility source changed")
    if compat_path.exists():
        require(sha(original_path) == build["original_failed_receipt_sha256"], "Original build receipt changed")
        require(sha(source / "bishengir/lib/Dialect/Tensor/Transforms/PropagateReshape/Utils.cpp") == build["utils_compat_sha256"], "Compatibility source changed")
    for name, item in original["sources"].items():
        require(sha(item["archive"]) == item["archive_sha256"], "Source archive changed: " + name)
    templates = json.loads((prefix / "templates-receipt.json").read_text())
    require(templates["state"] == "templates-ready" and templates["compiler_before_sha256"] == sha(compiler) == templates["compiler_after_sha256"], "Template build/compiler identity mismatch")
    require(set(templates["public_template_resources"]) == TEMPLATES and
            set(replay["compiler_prefix_templates"]) == TEMPLATES, "Incomplete template set")
    for name, item in templates["public_template_resources"].items():
        recorded = replay["compiler_prefix_templates"][name]
        expected = (compiler.parent.parent / "lib" / name).resolve()
        require(Path(item["installed"]).resolve() == expected == Path(recorded["path"]).resolve(), "Template resolved path mismatch")
        require(sha(expected) == item["sha256"] == recorded["sha256"] == sha(item["generated"]), "Generated/installed/replay template mismatch")
    for name, expected in templates["template_sources"].items():
        require(sha(source / name) == expected, "Public template source changed: " + name)
    require(replay["external_observation"]["hivmc"] and replay["external_observation"]["bisheng"], "Missing actual external compiler observation")
    identities = replay["external_executables"] + replay["observed_argument_resources"]
    require(bool(identities), "Missing external identity manifest")
    for item in identities:
        require(Path(item["path"]).resolve() == Path(item["path"]) and sha(item["path"]) == item["sha256"], "Actual external tool/resource changed: " + item["path"])
    return {"build_receipt_sha256": sha(compat_path if compat_path.exists() else original_path),
            "templates_receipt_sha256": sha(prefix / "templates-receipt.json"),
            "source_sha256": SOURCE_SHA, "compiler_sha256": sha(compiler)}
