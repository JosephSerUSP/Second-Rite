"""Browse a Blender remote asset library without Blender, and without downloading an asset.

Blender 5.2 remote libraries are static JSON over HTTP: a `_asset-library-meta.json`
that names an index, an index that names pages, and pages that list assets with a
licence, an author, a catalogue and the hash of the `.blend` that holds them. This
reads that listing and answers the questions an agent has before it wants an asset:
what exists, under which licence, from whom, in which file, how big, for which Blender.

    python tools/blender/asset_library.py info
    python tools/blender/asset_library.py search brick --type MATERIAL --license CC0
    python tools/blender/asset_library.py show "Bricks - Regular"
    python tools/blender/asset_library.py provenance "Bricks - Regular"

Read-only by construction: it fetches listing files and nothing else. Thumbnails and
`.blend` files are reported as URLs and hashes, never requested. Every listing file is
verified against the SHA-256 its parent declares, and cached under that hash, so a
tampered or truncated file is an error and an unchanged one is not fetched twice.

Defaults to Blender's Online Essentials (CC0). `--url` takes any library root, so a
library we publish ourselves is browsed the same way. `--json` prints machine output.

The client Blender ships (`_bpy_internal.assets.remote_library`) is private and may move
between 5.2.x releases; the listing protocol is documented and static, so this talks to
it directly with the standard library only.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ONLINE_ESSENTIALS = "https://cdn.extensions.blender.org/asset-libraries/essentials/"
META_NAME = "_asset-library-meta.json"
SUPPORTED_API = "v1"
SCHEMES = ("https", "http", "file")
MAX_LISTING_BYTES = 64 * 1024 * 1024
TIMEOUT_SECONDS = 30
# Blender's CDN refuses urllib's default agent, so say plainly what this is.
USER_AGENT = "second-rite-asset-library-browser/1 (read-only listing reader)"
DEFAULT_CACHE = ROOT / "out" / "asset-library-cache"
PIN_PATH = ROOT / "tools" / "blender" / "blender-pin.json"


def pinned_blender() -> str:
    """The repository's Blender as major.minor: the version an asset must be shown in."""
    try:
        version = json.loads(PIN_PATH.read_text(encoding="utf-8"))["version"]
    except (OSError, KeyError, ValueError):
        return ""
    return ".".join(version.split(".")[:2])


class LibraryError(SystemExit):
    """A listing that cannot be trusted or read. Exits non-zero with the reason."""


def _normalise_root(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in SCHEMES:
        raise LibraryError(f"unsupported URL scheme {parsed.scheme!r}; use one of {SCHEMES}")
    return url if url.endswith("/") else url + "/"


def _with_hash(url: str, declared: str) -> str:
    """`url?hash=HEX`, the cache-busting form the protocol asks for (type prefix dropped)."""
    if not declared:
        return url
    value = declared.split(":", 1)[-1]
    separator = "&" if "?" in url else "?"
    return url + separator + "hash=" + urllib.parse.quote(value)


def _sha256(data: bytes) -> str:
    return "SHA256:" + hashlib.sha256(data).hexdigest()


class Library:
    """A remote asset library's listing, loaded and verified. Never touches an asset file."""

    def __init__(self, url: str, cache: Path | None = None, offline: bool = False,
                 refresh: bool = False):
        self.root = _normalise_root(url)
        self.offline = offline
        self.refresh = refresh
        slug = re.sub(r"[^A-Za-z0-9]+", "_", urllib.parse.urlparse(self.root).netloc
                      + urllib.parse.urlparse(self.root).path).strip("_") or "library"
        self.cache = (Path(cache) if cache else DEFAULT_CACHE) / slug
        self.requests: list[str] = []  # every URL fetched, for the read-only test
        self._load()

    # -- fetching ---------------------------------------------------------------

    def resolve(self, relative: str) -> str:
        return urllib.parse.urljoin(self.root, relative)

    def _fetch(self, url: str) -> bytes:
        if self.offline:
            raise LibraryError(f"offline: {url} is not in the cache")
        fetch = url
        if urllib.parse.urlparse(url).scheme == "file":
            fetch = url.split("?", 1)[0]  # a file URL has no query string to honour
        self.requests.append(url)
        try:
            request = urllib.request.Request(fetch, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                data = response.read(MAX_LISTING_BYTES + 1)
        except (urllib.error.URLError, OSError) as error:
            raise LibraryError(f"could not read {url}: {error}")
        if len(data) > MAX_LISTING_BYTES:
            raise LibraryError(f"{url} is larger than {MAX_LISTING_BYTES} bytes")
        return data

    def _listing(self, relative: str, declared: str) -> dict:
        """A listing file whose content must match the hash its parent declared."""
        cached = self.cache / (declared.split(":", 1)[-1] + ".json")
        if cached.is_file() and not self.refresh:
            data = cached.read_bytes()
            if _sha256(data) == declared:
                return json.loads(data)
        data = self._fetch(_with_hash(self.resolve(relative), declared))
        actual = _sha256(data)
        if declared and actual != declared:
            raise LibraryError(f"{relative}: hash mismatch (declared {declared}, got {actual}); "
                               "refusing an untrusted listing")
        self.cache.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(data)
        return json.loads(data)

    def _load(self) -> None:
        meta_cache = self.cache / "meta.json"
        try:
            meta_bytes = self._fetch(self.resolve(META_NAME))
            self.cache.mkdir(parents=True, exist_ok=True)
            meta_cache.write_bytes(meta_bytes)
        except LibraryError:
            if not meta_cache.is_file():
                raise
            meta_bytes = meta_cache.read_bytes()  # offline: the last listing we saw
            self.offline = True
        self.meta = json.loads(meta_bytes)
        versions = self.meta.get("api_versions", {})
        if SUPPORTED_API not in versions:
            raise LibraryError(f"library offers API versions {sorted(versions)}; "
                               f"this reader supports {SUPPORTED_API}")
        entry = versions[SUPPORTED_API]
        self.index_hash = entry["hash"]
        self.index = self._listing(entry["url"], entry["hash"])

        self.assets: list[dict] = []
        self.files: dict[str, dict] = {}
        for page in self.index.get("pages", []):
            data = self._listing(page["url"], page["hash"])
            for file in data.get("files", []):
                self.files[file["path"]] = file
            self.assets.extend(data.get("assets", []))
        if len(self.assets) != self.index.get("asset_count", len(self.assets)):
            raise LibraryError(f"index declares {self.index['asset_count']} assets, "
                               f"pages hold {len(self.assets)}")

        self.catalogs: dict[str, str] = {}
        for catalog in self.index.get("catalogs", []):
            for uuid in catalog.get("uuids", []):
                self.catalogs[uuid] = catalog["path"]

    # -- queries ----------------------------------------------------------------

    def catalog_of(self, asset: dict) -> str:
        return self.catalogs.get(asset.get("meta", {}).get("catalog_id", ""), "")

    def search(self, query: str = "", types=(), license: str = "", catalog: str = "",
               tag: str = "", author: str = "", blender: str = "") -> list[dict]:
        words = query.lower().split()
        wanted = {t.upper() for t in types}
        results = []
        for asset in self.assets:
            meta = asset.get("meta", {})
            if wanted and asset["id_type"].upper() not in wanted:
                continue
            if license and license.lower() not in meta.get("license", "").lower():
                continue
            if author and author.lower() not in meta.get("author", "").lower():
                continue
            if tag and tag.lower() not in [t.lower() for t in meta.get("tags", [])]:
                continue
            path = self.catalog_of(asset)
            if catalog and not path.lower().startswith(catalog.lower()):
                continue
            if blender and not _shown_in(asset, blender):
                continue
            haystack = " ".join([asset["name"], meta.get("description", ""), path,
                                 " ".join(meta.get("tags", []))]).lower()
            if all(word in haystack for word in words):
                results.append(asset)
        return sorted(results, key=lambda a: (a["id_type"], a["name"].lower()))

    def find(self, name: str, id_type: str = "", blender: str = "") -> list[dict]:
        return [a for a in self.assets if a["name"].lower() == name.lower()
                and (not id_type or a["id_type"].upper() == id_type.upper())
                and (not blender or _shown_in(a, blender))]

    def record(self, asset: dict) -> dict:
        """Everything known about an asset, with URLs resolved and nothing fetched."""
        meta = asset.get("meta", {})
        files = []
        for path in asset["files"]:
            info = self.files.get(path, {})
            files.append({"path": path, "url": self.resolve(info.get("url") or path),
                          "sizeInBytes": info.get("size_in_bytes"), "hash": info.get("hash"),
                          "blenderVersion": info.get("blender_version")})
        thumbnail = asset.get("thumbnail")
        return {
            "name": asset["name"], "idType": asset["id_type"],
            "catalog": self.catalog_of(asset), "tags": meta.get("tags", []),
            "license": meta.get("license"), "author": meta.get("author"),
            "copyright": meta.get("copyright"), "description": meta.get("description"),
            "preferredImportMethod": meta.get("preferred_import_method"),
            "blenderVersions": asset.get("bl_versions", {}),
            "files": files,
            "thumbnail": ({"url": self.resolve(thumbnail["url"]), "hash": thumbnail.get("hash")}
                          if thumbnail else None),
        }

    def provenance(self, asset: dict) -> dict:
        """A record fit for an asset inventory: where it came from and how to verify it."""
        record = self.record(asset)
        return {
            "library": self.meta.get("name"), "libraryUrl": self.root,
            "libraryContact": self.meta.get("contact", {}).get("name"),
            "listingIndexHash": self.index_hash,
            "asset": record["name"], "idType": record["idType"],
            "license": record["license"], "author": record["author"],
            "copyright": record["copyright"],
            "file": record["files"][0] if record["files"] else None,
            "requiresBlender": record["blenderVersions"].get("min"),
            "retrievedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }


def _version(text: str) -> tuple:
    return tuple(int(part) for part in re.findall(r"\d+", text)[:2])


def _shown_in(asset: dict, blender: str) -> bool:
    """`min <= blender < until`, the interval Blender itself uses."""
    versions = asset.get("bl_versions", {})
    current = _version(blender)
    if "min" in versions and current < _version(versions["min"]):
        return False
    if versions.get("until") and current >= _version(versions["until"]):
        return False
    return True


# -- command line ------------------------------------------------------------------

def _size(bytes_: int | None) -> str:
    if bytes_ is None:
        return "-"
    for unit in ("B", "KiB", "MiB", "GiB"):
        if bytes_ < 1024 or unit == "GiB":
            return f"{bytes_:.0f} {unit}" if unit == "B" else f"{bytes_:.1f} {unit}"
        bytes_ /= 1024


def _interval(asset: dict) -> str:
    versions = asset.get("bl_versions", {})
    return f"{versions.get('min', '?')}" + (f"-<{versions['until']}" if versions.get("until") else "+")


def _one(library: Library, name: str, id_type: str, blender: str) -> dict:
    matches = library.find(name, id_type, blender)
    if not matches:
        near = [a["name"] for a in library.search(name, blender=blender)][:8]
        hint = f" Did you mean: {', '.join(near)}?" if near else ""
        shown = f" shown in Blender {blender}" if blender else ""
        raise LibraryError(f"no asset named {name!r}{shown}.{hint}")
    if len(matches) > 1:
        kinds = sorted({f"{a['id_type']} ({_interval(a)})" for a in matches})
        raise LibraryError(f"{name!r} is ambiguous ({len(matches)} assets: {', '.join(kinds)}); "
                           "add --type or --blender")
    return matches[0]


def _catalog_tree(library: Library) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for asset in library.assets:
        counts[library.catalog_of(asset)] = counts.get(library.catalog_of(asset), 0) + 1
    paths = sorted(set(library.catalogs.values()))
    return [(path, sum(n for p, n in counts.items() if p == path or p.startswith(path + "/")))
            for path in paths]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="asset_library", description=__doc__.split("\n\n")[0])
    parser.add_argument("--url", default=ONLINE_ESSENTIALS,
                        help="library root URL (default: Blender's Online Essentials)")
    parser.add_argument("--cache", type=Path, default=None,
                        help=f"listing cache (default: {DEFAULT_CACHE})")
    parser.add_argument("--offline", action="store_true", help="use the cache only")
    parser.add_argument("--refresh", action="store_true", help="ignore cached listing files")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--blender", default=pinned_blender(), metavar="M.N",
                        help="only assets shown in this Blender (default: the repository pin, "
                             "%(default)s). An asset can ship one variant per Blender range")
    parser.add_argument("--any-blender", action="store_true",
                        help="do not filter by Blender version")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("info", help="library name, counts, size, types and licences")
    catalogs = commands.add_parser("catalogs", help="the catalogue tree with counts")
    catalogs.add_argument("prefix", nargs="?", default="")
    search = commands.add_parser("search", help="find assets")
    search.add_argument("query", nargs="?", default="", help="words matched against name, "
                        "description, tags and catalogue")
    search.add_argument("--type", action="append", default=[], dest="types",
                        help="id type, e.g. MATERIAL, WORLD, OBJECT (repeatable)")
    search.add_argument("--license", default="", help="substring of the licence, e.g. CC0")
    search.add_argument("--catalog", default="", help="catalogue path prefix")
    search.add_argument("--tag", default="")
    search.add_argument("--author", default="")
    search.add_argument("--limit", type=int, default=0)
    show = commands.add_parser("show", help="one asset in full")
    show.add_argument("name")
    show.add_argument("--type", default="")
    provenance = commands.add_parser("provenance", help="an inventory record for one asset")
    provenance.add_argument("name")
    provenance.add_argument("--type", default="")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    library = Library(args.url, args.cache, args.offline, args.refresh)
    blender = "" if args.any_blender else args.blender

    def emit(payload, text):
        print(json.dumps(payload, indent=2, ensure_ascii=False) if args.json else text)

    if args.command == "info":
        by_type: dict[str, int] = {}
        by_license: dict[str, int] = {}
        for asset in library.assets:
            by_type[asset["id_type"]] = by_type.get(asset["id_type"], 0) + 1
            licence = asset.get("meta", {}).get("license") or "(none)"
            by_license[licence] = by_license.get(licence, 0) + 1
        payload = {"name": library.meta.get("name"), "url": library.root,
                   "contact": library.meta.get("contact"),
                   "assets": len(library.assets), "files": len(library.files),
                   "sizeInBytes": library.index.get("asset_size_bytes"),
                   "byType": by_type, "byLicense": by_license, "indexHash": library.index_hash}
        emit(payload, "\n".join([
            f"{payload['name']}  {library.root}",
            f"{payload['assets']} assets in {payload['files']} files, "
            f"{_size(payload['sizeInBytes'])}",
            "types:    " + ", ".join(f"{k} {v}" for k, v in sorted(by_type.items())),
            "licences: " + ", ".join(f"{k} {v}" for k, v in sorted(by_license.items()))]))
    elif args.command == "catalogs":
        rows = [(p, n) for p, n in _catalog_tree(library)
                if p.lower().startswith(args.prefix.lower())]
        emit([{"path": p, "assets": n} for p, n in rows],
             "\n".join(f"{'  ' * p.count('/')}{p.split('/')[-1]}  ({n})" for p, n in rows))
    elif args.command == "search":
        found = library.search(args.query, args.types, args.license, args.catalog, args.tag,
                               args.author, blender)
        total = len(found)
        if args.limit:
            found = found[:args.limit]
        rows = [{"name": a["name"], "idType": a["id_type"], "catalog": library.catalog_of(a),
                 "license": a.get("meta", {}).get("license"), "author": a.get("meta", {}).get("author"),
                 "sizeInBytes": library.files.get(a["files"][0], {}).get("size_in_bytes"),
                 "blender": _interval(a)} for a in found]
        text = "\n".join(f"{r['idType']:10s} {r['name']:36s} {r['catalog']:34s} "
                         f"{(r['license'] or '-'):22s} {_size(r['sizeInBytes']):>9s} "
                         f"{r['blender']:>7s}  {r['author'] or '-'}" for r in rows)
        emit(rows if args.json else None,
             text + (f"\n{len(rows)} of {total} shown" if args.limit and total > len(rows)
                     else f"\n{total} asset(s)"))
    elif args.command == "show":
        record = library.record(_one(library, args.name, args.type, blender))
        lines = [f"{record['name']}  [{record['idType']}]", f"catalogue:   {record['catalog'] or '-'}",
                 f"licence:     {record['license'] or '-'}", f"author:      {record['author'] or '-'}",
                 f"description: {record['description'] or '-'}",
                 f"tags:        {', '.join(record['tags']) or '-'}",
                 f"blender:     {record['blenderVersions']}",
                 f"import:      {record['preferredImportMethod'] or '-'}"]
        for file in record["files"]:
            lines.append(f"file:        {file['url']}  {_size(file['sizeInBytes'])}  {file['hash']}  "
                         f"(saved by Blender {file['blenderVersion']})")
        if record["thumbnail"]:
            lines.append(f"thumbnail:   {record['thumbnail']['url']}")
        emit(record, "\n".join(lines))
    elif args.command == "provenance":
        record = library.provenance(_one(library, args.name, args.type, blender))
        print(json.dumps(record, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
