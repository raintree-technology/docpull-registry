"""Validate index.json and every recipe it lists. Standard library only.

Run `python tools/check.py` before opening a pull request. Pass `--write` to
rewrite index.json from the recipe files, recomputing every sha256 and setting
each pack's `latest` to its highest version in sort order.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
PACK_NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
PACK_VERSION = re.compile(r"[A-Za-z0-9._-]{1,32}")
CRAWL_TYPES = {"auto", "html", "pdf", "markdown", "github", "sitemap"}
RECIPE_KEYS = {"schema_version", "name", "version", "description", "docpull_version", "sources", "expected"}
MAX_RECIPE_BYTES = 10_000_000


def _https(url: object) -> bool:
    if not isinstance(url, str):
        return False
    parsed = urlsplit(url)
    return parsed.scheme == "https" and bool(parsed.netloc) and not parsed.username and not parsed.password


def check_recipe(path: Path, name: str, version: str) -> list[str]:
    where = path.relative_to(ROOT)
    if path.stat().st_size > MAX_RECIPE_BYTES:
        return [f"{where}: larger than {MAX_RECIPE_BYTES} bytes"]
    try:
        recipe = json.loads(path.read_bytes())
    except json.JSONDecodeError as err:
        return [f"{where}: invalid JSON: {err}"]
    errors = []
    if not isinstance(recipe, dict) or set(recipe) - RECIPE_KEYS:
        return [f"{where}: unexpected keys {sorted(set(recipe) - RECIPE_KEYS) if isinstance(recipe, dict) else ''}"]
    if recipe.get("schema_version") != 1:
        errors.append(f"{where}: schema_version must be 1")
    if (recipe.get("name"), recipe.get("version")) != (name, version):
        errors.append(f"{where}: recipe says {recipe.get('name')}@{recipe.get('version')}, path says {name}@{version}")
    sources = recipe.get("sources")
    if not isinstance(sources, list) or not sources:
        return [*errors, f"{where}: needs at least one source"]
    names = set()
    for source in sources:
        label = source.get("name") if isinstance(source, dict) else source
        if not isinstance(source, dict) or set(source) - {"name", "url", "type", "discovered_urls"}:
            errors.append(f"{where}: source {label!r} has unexpected fields")
            continue
        names.add(source.get("name"))
        if not _https(source.get("url")):
            errors.append(f"{where}: source {label!r} must use an https URL")
        if source.get("type", "auto") not in CRAWL_TYPES:
            errors.append(f"{where}: source {label!r} must use a crawl type: {sorted(CRAWL_TYPES)}")
        if not all(_https(url) for url in source.get("discovered_urls", [])):
            errors.append(f"{where}: source {label!r} has non-https discovered_urls")
    expected = recipe.get("expected")
    if not isinstance(expected, dict) or set(expected) != names:
        errors.append(f"{where}: expected must have one entry per source name")
    else:
        for source_name, pages in expected.items():
            for url, digest in (pages or {}).items():
                if not _https(url) or not re.fullmatch(r"[0-9a-f]{64}", str(digest)):
                    errors.append(f"{where}: {source_name} has an invalid page entry for {url}")
    return errors


def build_index() -> dict:
    packs: dict = {}
    for path in sorted(ROOT.glob("packs/*/*.json")):
        name, version = path.parent.name, path.stem
        entry = {"path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        packs.setdefault(name, {"versions": {}})["versions"][version] = entry
    for pack in packs.values():
        pack["latest"] = max(pack["versions"])
    return {"schema_version": 1, "packs": packs}


def main() -> int:
    if "--write" in sys.argv[1:]:
        (ROOT / "index.json").write_text(json.dumps(build_index(), indent=2, sort_keys=True) + "\n")
    index = json.loads((ROOT / "index.json").read_text())
    errors = []
    if index != build_index():
        errors.append("index.json is out of date; run `python tools/check.py --write`")
    for name, pack in index.get("packs", {}).items():
        if not PACK_NAME.fullmatch(name):
            errors.append(f"invalid pack name {name!r}")
        for version, entry in pack.get("versions", {}).items():
            if not PACK_VERSION.fullmatch(version):
                errors.append(f"{name}: invalid version {version!r}")
                continue
            errors.extend(check_recipe(ROOT / entry["path"], name, version))
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if not errors:
        print(f"ok: {sum(len(p['versions']) for p in index['packs'].values())} recipe(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
