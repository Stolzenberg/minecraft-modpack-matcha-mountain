#!/usr/bin/env python3
"""Baut die Matcha-Mountain-Jar aus drei Ebenen: upstream < overrides < additions.

Befehle:
  fetch <version>   Matcha-Datapack und -Ressourcenpack von Modrinth nach
                    datapack/upstream/matcha-<version>/ entpacken
  build             Jar bauen (build/matcha-mountain-<version>.jar)
  check             nur prüfen: welche überschriebenen Dateien hat Matcha seit
                    dem letzten "accept" geändert?
  accept [pfad...]  aktuellen Upstream-Stand der Overrides als geprüft
                    festhalten (ohne Pfade: alle)

Ebenen (jeweils mit data/ und/oder assets/):
  datapack/upstream/matcha-<v>/datapack/       unverändert
  datapack/upstream/matcha-<v>/resourcepack/   unverändert
  datapack/overrides/   ersetzt gleichnamige Dateien aus upstream
  datapack/additions/   eigener Namespace "matchamountain"

Zusätzlich in datapack/overrides/:
  pack.mcmeta     optional; "filter.block" wird angehängt,
                  "matchamountain:unblock" entfernt Einträge aus Matchas Filter
  removals.txt    optional; ein Pfad (glob) pro Zeile, der aus upstream entfällt
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import io
import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DP = ROOT / "datapack"
UPSTREAM = DP / "upstream"
OVERRIDES = DP / "overrides"
ADDITIONS = DP / "additions"
LOCK = DP / "overrides.lock.json"
BUILD = ROOT / "build"
CONFIG = ROOT / "pack.json"

MODRINTH = "https://api.modrinth.com/v2/project/matcha-flavoured/version"
USER_AGENT = "matcha-mountain-build (github.com/Stolzenberg/minecraft-modpack-matcha-mountain)"
CONTENT_DIRS = ("data", "assets")
EXTRA_FILES = ("CREDITS.md", "translation_credits.md", "pack.png")


# --------------------------------------------------------------------------- #
# Hilfen

def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def upstream_dir(cfg: dict) -> Path:
    d = UPSTREAM / f"matcha-{cfg['matcha_version']}"
    if not d.is_dir():
        sys.exit(f"Upstream fehlt: {d.relative_to(ROOT)} (erst `fetch {cfg['matcha_version']}`)")
    return d


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def files_of(layer: Path) -> dict[str, Path]:
    """Alle Inhaltsdateien einer Ebene, Schlüssel = Pfad relativ zur Ebene (posix)."""
    out: dict[str, Path] = {}
    for sub in CONTENT_DIRS:
        base = layer / sub
        if base.is_dir():
            for f in base.rglob("*"):
                if f.is_file() and not f.name.startswith("."):
                    out[f.relative_to(layer).as_posix()] = f
    return out


def upstream_files(up: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for part in ("resourcepack", "datapack"):
        for rel, f in files_of(up / part).items():
            if rel in files:
                sys.exit(f"Upstream-Konflikt zwischen Daten- und Ressourcenpack: {rel}")
            files[rel] = f
    return files


def read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def removals() -> list[str]:
    p = OVERRIDES / "removals.txt"
    if not p.is_file():
        return []
    return [l.strip() for l in p.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.lstrip().startswith("#")]


# --------------------------------------------------------------------------- #
# fetch

def http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def cmd_fetch(args) -> None:
    versions = json.loads(http_get(MODRINTH))
    wanted = {"dp": "datapack", "rp": "resourcepack"}
    target = UPSTREAM / f"matcha-{args.version}"
    if target.exists() and not args.force:
        sys.exit(f"{target.relative_to(ROOT)} existiert schon (--force zum Überschreiben)")
    found = {}
    for v in versions:
        num = v["version_number"]
        for suffix, part in wanted.items():
            if num.split("+")[0] == args.version and num.endswith("+" + suffix):
                found[part] = v
    if set(found) != set(wanted.values()):
        sys.exit(f"Matcha {args.version}: Daten- und Ressourcenpack nicht beide auf Modrinth gefunden")
    if target.exists():
        shutil.rmtree(target)
    for part, v in found.items():
        f = next(x for x in v["files"] if x["primary"]) if any(x["primary"] for x in v["files"]) else v["files"][0]
        print(f"lade {f['filename']} …")
        blob = http_get(f["url"])
        if hashlib.sha512(blob).hexdigest() != f["hashes"]["sha512"]:
            sys.exit(f"Prüfsumme falsch: {f['filename']}")
        dest = target / part
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            for info in z.infolist():
                p = Path(info.filename)
                if p.is_absolute() or ".." in p.parts:
                    sys.exit(f"unsicherer Pfad im Archiv: {info.filename}")
            z.extractall(dest)
        (target / f"{part}.source.json").write_text(json.dumps({
            "version_number": v["version_number"], "name": v["name"],
            "date_published": v["date_published"], "game_versions": v["game_versions"],
            "file": f["filename"], "url": f["url"], "sha512": f["hashes"]["sha512"],
        }, indent=2) + "\n", encoding="utf-8")
    print(f"entpackt nach {target.relative_to(ROOT)}")
    cfg = load_config()
    if cfg["matcha_version"] != args.version:
        print(f"Hinweis: pack.json zeigt noch auf {cfg['matcha_version']}. "
              f"Umstellen, dann `check` laufen lassen.")


# --------------------------------------------------------------------------- #
# Upstream-Änderungen an überschriebenen Dateien

def drift(cfg: dict, up_files: dict[str, Path]) -> list[str]:
    lock = read_json(LOCK)
    msgs = []
    for rel in sorted(files_of(OVERRIDES)):
        cur = sha256(up_files[rel]) if rel in up_files else None
        entry = lock.get(rel)
        if entry is None:
            msgs.append(f"NEU     {rel}  (noch nicht mit `accept` erfasst)")
        elif entry["sha256"] != cur:
            what = "ENTFERNT" if cur is None else "GEÄNDERT"
            msgs.append(f"{what} {rel}  (Matcha {entry['matcha']} -> {cfg['matcha_version']})")
    for rel in sorted(set(lock) - set(files_of(OVERRIDES))):
        msgs.append(f"VERWAIST {rel}  (im Lock, aber kein Override mehr; `accept` räumt auf)")
    return msgs


def cmd_check(_args) -> int:
    cfg = load_config()
    msgs = drift(cfg, upstream_files(upstream_dir(cfg)))
    for m in msgs:
        print(m)
    if not msgs:
        print("Overrides passen zum aktuellen Upstream.")
    return 1 if msgs else 0


def cmd_accept(args) -> None:
    cfg = load_config()
    up_files = upstream_files(upstream_dir(cfg))
    over = files_of(OVERRIDES)
    lock = read_json(LOCK)
    targets = args.paths or list(over)
    for rel in targets:
        if rel not in over:
            sys.exit(f"kein Override: {rel}")
        lock[rel] = {"matcha": cfg["matcha_version"],
                     "sha256": sha256(up_files[rel]) if rel in up_files else None}
    if not args.paths:
        lock = {k: v for k, v in lock.items() if k in over}
    LOCK.write_text(json.dumps(dict(sorted(lock.items())), indent=2) + "\n", encoding="utf-8")
    print(f"{len(targets)} Override(s) für Matcha {cfg['matcha_version']} festgehalten")


# --------------------------------------------------------------------------- #
# build

def merged_mcmeta(cfg: dict, up: Path) -> dict:
    meta = read_json(up / "datapack" / "pack.mcmeta")
    rp_meta = read_json(up / "resourcepack" / "pack.mcmeta")
    blocks: list[dict] = []
    for m in (meta, rp_meta):
        blocks += m.get("filter", {}).get("block", [])

    over_meta = read_json(OVERRIDES / "pack.mcmeta")
    add_meta = read_json(ADDITIONS / "pack.mcmeta")
    unblock = over_meta.get("matchamountain:unblock", [])
    for u in unblock:
        if u not in blocks:
            sys.exit(f"unblock-Eintrag steht nicht in Matchas Filter: {u}")
    blocks = [b for b in blocks if b not in unblock]
    for m in (over_meta, add_meta):
        for b in m.get("filter", {}).get("block", []):
            if b not in blocks:
                blocks.append(b)

    pack = meta["pack"]
    out = {
        "pack": {
            "min_format": pack["min_format"],
            "max_format": pack["max_format"],
            "description": [
                {"text": "Matcha Mountain", "color": "#56be4e"},
                {"text": "\n"},
                {"text": f"{cfg['version']} · Matcha {cfg['matcha_version']}", "color": "#908b8b"},
            ],
        },
        "filter": {"block": blocks},
    }
    return out


def fabric_mod_json(cfg: dict) -> dict:
    return {
        "schemaVersion": 1,
        "id": "matchamountain",
        "version": cfg["version"],
        "name": "Matcha Mountain",
        "description": f"Fork von Matcha Flavoured {cfg['matcha_version']} (Klei_Wright) für Matcha Mountain",
        "authors": ["Stolzenberg"],
        "contributors": ["klei_wright (Matcha Flavoured)"],
        "contact": {
            "sources": "https://github.com/Stolzenberg/minecraft-modpack-matcha-mountain",
            "homepage": "https://modrinth.com/datapack/matcha-flavoured",
        },
        "license": "CC-BY-NC-SA-4.0",
        "icon": "pack.png",
        "environment": "*",
        "depends": {"fabric-resource-loader-v0": "*", "minecraft": cfg["minecraft"]},
        "breaks": {"mr_matcha_flavoured": "*"},
    }


def cmd_build(args) -> None:
    cfg = load_config()
    up = upstream_dir(cfg)
    up_files = upstream_files(up)

    # Drift zuerst melden, damit es niemand übersieht
    msgs = drift(cfg, up_files)
    if msgs:
        print("Achtung, Overrides prüfen (danach `accept`):")
        for m in msgs:
            print("  " + m)
        if args.strict:
            sys.exit(1)

    files = dict(up_files)
    removed = 0
    for pattern in removals():
        hits = [k for k in files if fnmatch.fnmatchcase(k, pattern)]
        if not hits:
            print(f"Warnung: removals.txt trifft nichts: {pattern}")
        for k in hits:
            del files[k]
            removed += 1

    over = files_of(OVERRIDES)
    replaced = sum(1 for k in over if k in up_files)
    files.update(over)

    add = files_of(ADDITIONS)
    for rel in add:
        ns = rel.split("/")[1]
        if ns != "matchamountain":
            sys.exit(f"additions/ darf nur den Namespace matchamountain enthalten: {rel}")
        if rel in files:
            sys.exit(f"additions/ kollidiert mit vorhandener Datei: {rel}")
    files.update(add)

    # JSON-Dateien aus unseren Ebenen auf Syntax prüfen
    for rel, f in {**over, **add}.items():
        if f.suffix in (".json", ".mcmeta"):
            try:
                json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                sys.exit(f"ungültiges JSON in {f.relative_to(ROOT)}: {e}")

    BUILD.mkdir(exist_ok=True)
    jar = BUILD / f"matcha-mountain-{cfg['version']}.jar"
    with zipfile.ZipFile(jar, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr("pack.mcmeta", json.dumps(merged_mcmeta(cfg, up), indent=2))
        z.writestr("fabric.mod.json", json.dumps(fabric_mod_json(cfg), indent=2))
        icon = ADDITIONS / "pack.png"
        z.write(icon if icon.is_file() else up / "datapack" / "pack.png", "pack.png")
        for name in EXTRA_FILES[:2]:
            for part in ("datapack", "resourcepack"):
                if (up / part / name).is_file():
                    z.write(up / part / name, f"matcha/{name}")
        z.write(ROOT / "LICENSE.md", "LICENSE.md")
        for rel in sorted(files):
            z.write(files[rel], rel)

    print(f"{jar.relative_to(ROOT)}: {len(files)} Dateien "
          f"({replaced} überschrieben, {len(over) - replaced} neu in overrides, "
          f"{removed} entfernt, {len(add)} eigene)")

    if args.install:
        mods = Path(cfg["test_instance"]).expanduser() / "minecraft" / "mods"
        if not mods.is_dir():
            sys.exit(f"Testinstanz nicht gefunden: {mods}")
        for old in mods.glob("matcha-mountain-*.jar"):
            old.unlink()
        shutil.copy2(jar, mods / jar.name)
        print(f"installiert nach {mods}")


# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("fetch"); p.add_argument("version"); p.add_argument("--force", action="store_true")
    p = sub.add_parser("build")
    p.add_argument("--install", action="store_true", help="Jar in die Prism-Testinstanz kopieren")
    p.add_argument("--strict", action="store_true", help="bei Upstream-Änderungen abbrechen")
    sub.add_parser("check")
    p = sub.add_parser("accept"); p.add_argument("paths", nargs="*")
    args = ap.parse_args()
    return {"fetch": cmd_fetch, "build": cmd_build, "check": cmd_check,
            "accept": cmd_accept}[args.cmd](args) or 0


if __name__ == "__main__":
    sys.exit(main())
