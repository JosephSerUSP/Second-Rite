"""Shared physical authored-data storage semantics for repository tooling.

Thestra's runtime-owned ``runtime/engine/data/authored_storage_manifest.json`` is the authority for both
semantic kind and physical representation. This module deliberately mirrors the
physical storage contract used by LÖVE and Studio: monolith resources read only
their declared monolith, fragment resources reject a coexisting legacy
monolith, ordered collections use ``index.json``, keyed registries derive
identity from each record's ``id``, and semantic configs use their declared
module list.

Migration helpers such as ``load_registry_fragments`` remain available to tools
that are explicitly constructing a new representation, but ordinary readers
should use ``load_resource`` / ``load_ordered_collection`` / ``load_registry``
so representation choice comes from the shared manifest rather than from file
existence heuristics.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_PATH = ROOT / "runtime" / "engine" / "data" / "authored_storage_manifest.json"
VALID_KINDS = {"document", "ordered_collection", "keyed_registry", "semantic_config"}
VALID_REPRESENTATIONS = {"monolith", "fragments"}


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"authored JSON file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc


def validate_spec(stem: str, spec: Any, source: Path | str = "<authored storage manifest>") -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise ValueError(f"authored resource '{stem}' has no storage metadata: {source}")
    kind = spec.get("kind")
    representation = spec.get("representation")
    if kind not in VALID_KINDS:
        raise ValueError(f"authored resource '{stem}' has unknown kind '{kind}': {source}")
    if representation not in VALID_REPRESENTATIONS:
        raise ValueError(
            f"authored resource '{stem}' has unknown representation '{representation}': {source}"
        )
    if kind == "document" and representation != "monolith":
        raise ValueError(f"document resource '{stem}' must use monolith representation: {source}")
    if kind == "semantic_config":
        modules = spec.get("modules")
        if representation != "fragments" or not isinstance(modules, list) or not modules:
            raise ValueError(
                f"semantic config '{stem}' must declare non-empty fragment modules: {source}"
            )
        seen: set[str] = set()
        for module in modules:
            if (
                not isinstance(module, str)
                or not re.fullmatch(r"[A-Za-z0-9_-]+", module)
                or module in seen
            ):
                raise ValueError(
                    f"semantic config '{stem}' has invalid or duplicate module '{module}': {source}"
                )
            seen.add(module)
    return spec


def load_manifest(manifest_path: Path = DEFAULT_MANIFEST_PATH) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("resources"), dict):
        raise ValueError(
            f"authored storage manifest must contain a resources object: {manifest_path}"
        )
    for stem, spec in manifest["resources"].items():
        validate_spec(stem, spec, manifest_path)
    return manifest


def resource_spec(
    stem: str, manifest: dict[str, Any] | None = None
) -> dict[str, Any]:
    manifest = manifest or load_manifest()
    spec = manifest["resources"].get(stem)
    if spec is None:
        raise ValueError(f"authored resource '{stem}' is not declared in the storage manifest")
    return validate_spec(stem, spec)


def bulk_editable_resources(manifest: dict[str, Any] | None = None) -> list[str]:
    manifest = manifest or load_manifest()
    return [
        stem
        for stem, spec in manifest["resources"].items()
        if spec.get("bulkEditable") is True
    ]


def validate_ordered(entries: Any, stem: str, source: Path | str) -> list[dict[str, Any]]:
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"ordered collection '{stem}' must be a non-empty array: {source}")

    seen: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict) or "id" not in entry:
            raise ValueError(f"ordered collection '{stem}' entry {index} has no id: {source}")
        key = str(entry["id"])
        if key in seen:
            raise ValueError(f"ordered collection '{stem}' has duplicate id '{key}': {source}")
        seen.add(key)
    return entries


def validate_registry_record(record: Any, stem: str, source: Path | str) -> str:
    if not isinstance(record, dict):
        raise ValueError(f"registry '{stem}' record is not an object: {source}")
    record_id = record.get("id")
    if not isinstance(record_id, str) or not record_id:
        raise ValueError(
            f"registry '{stem}' record must own a non-empty string id: {source}"
        )
    return record_id


def validate_registry_monolith(
    value: Any, stem: str, source: Path | str
) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"registry '{stem}' must be a non-empty object: {source}")

    out: dict[str, dict[str, Any]] = {}
    for key, record in value.items():
        record_id = validate_registry_record(record, stem, source)
        if key != record_id:
            raise ValueError(
                f"registry '{stem}' key '{key}' disagrees with record.id '{record_id}': {source}"
            )
        if record_id in out:
            raise ValueError(f"registry '{stem}' has duplicate id '{record_id}': {source}")
        out[record_id] = record
    return out


def validate_resource(value: Any, stem: str, spec: dict[str, Any], source: Path | str) -> Any:
    validate_spec(stem, spec)
    if spec["kind"] == "ordered_collection":
        return validate_ordered(value, stem, source)
    if spec["kind"] == "keyed_registry":
        return validate_registry_monolith(value, stem, source)
    if spec["kind"] == "semantic_config":
        if not isinstance(value, dict):
            raise ValueError(f"semantic config '{stem}' must be an object: {source}")
        expected = set(spec["modules"])
        for module, module_value in value.items():
            if module not in expected or not isinstance(module_value, dict):
                raise ValueError(
                    f"semantic config '{stem}' has invalid module '{module}': {source}"
                )
            expected.remove(module)
        if expected:
            missing = next(iter(expected))
            raise ValueError(f"semantic config '{stem}' is missing module '{missing}': {source}")
    return value


def _validate_fragment_name(stem: str, name: Any, seen: set[str]) -> str:
    if not isinstance(name, str) or not name:
        raise ValueError(f"{stem}/index.json entries must be non-empty filenames")
    if (
        ".." in name
        or name.startswith("/")
        or name.startswith("\\")
        or "/" in name
        or "\\" in name
    ):
        raise ValueError(f"{stem}/index.json contains an unsafe fragment path: {name}")
    if not name.lower().endswith(".json"):
        raise ValueError(f"{stem}/index.json fragment must end in .json: {name}")
    folded = name.lower()
    if folded in seen:
        raise ValueError(f"{stem}/index.json lists the same fragment twice: {name}")
    seen.add(folded)
    return name


def _ordered_manifest_files(manifest: Any, stem: str) -> list[str]:
    files = manifest.get("files") if isinstance(manifest, dict) else manifest
    if not isinstance(files, list) or not files:
        raise ValueError(f"{stem}/index.json must be an array or {{ files = [...] }}")

    seen: set[str] = set()
    return [_validate_fragment_name(stem, name, seen) for name in files]


def ordered_fragment_files(directory: Path, stem: str) -> list[Path]:
    index_path = directory / "index.json"
    files = _ordered_manifest_files(read_json(index_path), stem)
    paths: list[Path] = []
    for name in files:
        path = directory / name
        if not path.is_file():
            raise ValueError(f"{stem}/index.json references a missing fragment: {path}")
        paths.append(path)
    return paths


def registry_files(directory: Path, stem: str | None = None) -> list[Path]:
    stem = stem or directory.name
    if not directory.is_dir():
        raise ValueError(f"registry directory does not exist: {directory}")
    entries = [path for path in directory.iterdir() if path.is_file()]
    if any(path.name.lower() == "index.json" for path in entries):
        raise ValueError(f"registry '{stem}' must not use a shared index.json")
    # Registry order is storage-only but feeds the compound version token. Use
    # explicit UTF-8 byte ordering so host locale and filesystem enumeration
    # cannot make repository tooling disagree with Studio/LÖVE.
    files = sorted(
        (path for path in entries if path.name.lower().endswith(".json")),
        key=lambda path: path.name.encode("utf-8"),
    )
    if not files:
        raise ValueError(f"registry '{stem}' has no JSON fragments: {directory}")
    return files


def load_ordered_fragments(directory: Path, stem: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in ordered_fragment_files(directory, stem):
        value = read_json(path)
        if isinstance(value, list):
            if not value or not all(isinstance(entry, dict) for entry in value):
                raise ValueError(f"ordered fragment contains a non-object: {path}")
            out.extend(value)
        elif isinstance(value, dict):
            out.append(value)
        else:
            raise ValueError(
                f"ordered fragment is neither an object with id nor a non-empty array: {path}"
            )
    return validate_ordered(out, stem, directory / "index.json")


def load_registry_fragments(
    directory: Path, stem: str | None = None
) -> dict[str, dict[str, Any]]:
    stem = stem or directory.name
    out: dict[str, dict[str, Any]] = {}
    for path in registry_files(directory, stem):
        record = read_json(path)
        record_id = validate_registry_record(record, stem, path)
        if record_id in out:
            raise ValueError(f"registry '{stem}' has duplicate id '{record_id}': {path}")
        out[record_id] = record
    return out


def reject_legacy_monolith(root: Path, stem: str) -> None:
    monolith = root / f"{stem}.json"
    if monolith.exists():
        raise ValueError(
            f"authored resource '{stem}' has both fragment storage and legacy monolith: {monolith}"
        )


def semantic_module_files(directory: Path, stem: str, spec: dict[str, Any]) -> list[Path]:
    if not directory.is_dir():
        raise ValueError(f"semantic config directory does not exist: {directory}")
    expected = {f"{module}.json" for module in spec["modules"]}
    for path in directory.iterdir():
        if path.is_file() and path.suffix.lower() == ".json" and path.name not in expected:
            raise ValueError(f"semantic config '{stem}' has undeclared module: {path}")
    paths: list[Path] = []
    for module in spec["modules"]:
        path = directory / f"{module}.json"
        if not path.is_file():
            raise ValueError(f"semantic config '{stem}' is missing module: {path}")
        paths.append(path)
    return paths


def authoritative_files(
    root: Path, stem: str, spec: dict[str, Any] | None = None
) -> list[Path]:
    spec = spec or resource_spec(stem)
    validate_spec(stem, spec)
    if spec["representation"] == "monolith":
        path = root / f"{stem}.json"
        if not path.is_file():
            raise ValueError(f"authored JSON file does not exist: {path}")
        return [path]

    reject_legacy_monolith(root, stem)
    directory = root / stem
    if spec["kind"] == "ordered_collection":
        index_path = directory / "index.json"
        if not index_path.is_file():
            raise ValueError(f"authored JSON file does not exist: {index_path}")
        return [index_path, *ordered_fragment_files(directory, stem)]
    if spec["kind"] == "keyed_registry":
        return registry_files(directory, stem)
    if spec["kind"] == "semantic_config":
        return semantic_module_files(directory, stem, spec)
    raise ValueError(f"resource '{stem}' cannot use fragmented document storage")


def load_resource(
    root: Path, stem: str, spec: dict[str, Any] | None = None
) -> tuple[Any, str]:
    spec = spec or resource_spec(stem)
    validate_spec(stem, spec)
    if spec["representation"] == "monolith":
        source = root / f"{stem}.json"
        return validate_resource(read_json(source), stem, spec, source), "monolith"

    reject_legacy_monolith(root, stem)
    directory = root / stem
    if spec["kind"] == "ordered_collection":
        return load_ordered_fragments(directory, stem), "fragments"
    if spec["kind"] == "keyed_registry":
        value = load_registry_fragments(directory, stem)
        return validate_resource(value, stem, spec, directory), "fragments"
    if spec["kind"] == "semantic_config":
        value = {
            module: read_json(directory / f"{module}.json")
            for module in spec["modules"]
        }
        return validate_resource(value, stem, spec, directory), "fragments"
    raise ValueError(f"resource '{stem}' cannot use fragmented document storage")


def load_ordered_collection(
    root: Path, stem: str, spec: dict[str, Any] | None = None
) -> tuple[list[dict[str, Any]], str]:
    spec = spec or resource_spec(stem)
    if spec["kind"] != "ordered_collection":
        raise ValueError(f"authored resource '{stem}' is not an ordered collection")
    value, storage = load_resource(root, stem, spec)
    return value, storage


def load_registry(
    root: Path, stem: str, spec: dict[str, Any] | None = None
) -> tuple[dict[str, dict[str, Any]], str]:
    spec = spec or resource_spec(stem)
    if spec["kind"] != "keyed_registry":
        raise ValueError(f"authored resource '{stem}' is not a keyed registry")
    value, storage = load_resource(root, stem, spec)
    return value, storage


def registry_fragment_names(records: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Return filenames using Studio/LÖVE's fragment-candidate algorithm.

    IDs are semantic identity; filenames are only deterministic storage names.
    Existing writers prefer a readable ``<id>.json`` when it is safe and does
    not lowercase-collide with a previously reserved filename, otherwise they
    append the full UTF-8 id encoded as lowercase hexadecimal.
    """

    names: dict[str, str] = {}
    reserved: list[str] = []
    for record_id in sorted(records, key=lambda value: str(value).encode("utf-8")):
        value = str(record_id)
        folded = {name.lower() for name in reserved}
        candidate = (
            f"{value}.json"
            if re.fullmatch(r"[A-Za-z0-9._-]+", value)
            and value not in {".", ".."}
            and value.lower() != "index"
            else None
        )
        if candidate is None or candidate.lower() in folded:
            slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "record"
            candidate = f"{slug}--{value.encode('utf-8').hex()}.json"
            if candidate.lower() in folded:
                raise ValueError(
                    f"registry filename collision for id '{record_id}': {candidate}"
                )
        reserved.append(candidate)
        names[record_id] = candidate
    return names


def _hash_file(hasher: Any, root: Path, path: Path) -> None:
    relative = path.relative_to(root).as_posix().encode("utf-8")
    payload = path.read_bytes()
    hasher.update(len(relative).to_bytes(8, "big"))
    hasher.update(relative)
    hasher.update(len(payload).to_bytes(8, "big"))
    hasher.update(payload)


def version_token(
    root: Path, stem: str, spec: dict[str, Any] | None = None
) -> str:
    """Return the same compound token as Studio's physical storage layer."""

    spec = spec or resource_spec(stem)
    validate_spec(stem, spec)
    hasher = hashlib.sha256()
    hasher.update(
        (
            f"authored-resource\0{stem}\0{spec['kind']}\0"
            f"{spec['representation']}\0"
        ).encode("utf-8")
    )
    for path in authoritative_files(root, stem, spec):
        _hash_file(hasher, root, path)
    return hasher.hexdigest()
