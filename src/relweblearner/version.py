"""Creature versioning — tag, list, diff, roll back a mind's state.

A creature's whole state is on disk as three artefacts: the JSON checkpoint (a
projection), the append-only episode log (the belief source), and — under a
durable store — the edge database files. A VERSION is a consistent copy of the
three, taken under the creature lock, plus a manifest saying when it was taken
and what code/curriculum produced it. Because the log is the source of truth,
restoring a version is a *real* rollback: the current log is rotated aside
(never deleted — the usual invariant) and the tagged log restored, so a later
``load`` cannot replay the rolled-back tail on top of the old checkpoint.

    relweb-version --tag before-wikidata          # snapshot the current state
    relweb-version --list                         # what versions exist?
    relweb-version --diff before-wikidata         # belief diff: version vs now
    relweb-version --diff v1 v2                   # belief diff: version vs version
    relweb-version --rollback before-wikidata     # restore (current state rotated aside)

The training tick also snapshots automatically after each stage it advances
(``auto-<log position>`` tags, pruned to the newest ``RELWEB_AUTOSNAP_KEEP``;
``RELWEB_AUTOSNAP=0`` disables) — so "the state before last night's run" is
always one ``--rollback`` away, replacing the old hand-copied ``.bak`` ritual.

Every checkpoint save is additionally STAMPED (:func:`stamp`) with the git
commit and a hash of ``corpus/sources.json``, so any state file — versioned or
not — is traceable to the exact code and syllabus that produced it.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path

from .store import open_store, store_files

_TS = "%Y%m%d-%H%M%S"


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


# ============================================================= provenance stamp

_code_sha: str | None | bool = False        # False = not computed yet (cached per process)


def stamp() -> dict:
    """What produced this state: save time, git commit (``-dirty`` when the
    tree has uncommitted changes), and a short hash of the curriculum registry.
    Every field is fail-soft (``None`` outside a git checkout, etc.) — the
    stamp must never be the reason a save fails."""
    return {"saved": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "code": _git_sha(), "curriculum": _curriculum_hash()}


def _git_sha() -> str | None:
    global _code_sha
    if _code_sha is False:
        try:
            head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=_root(),
                                  capture_output=True, text=True, timeout=5)
            sha = head.stdout.strip() if head.returncode == 0 and head.stdout.strip() else None
            if sha:
                dirty = subprocess.run(["git", "status", "--porcelain"], cwd=_root(),
                                       capture_output=True, text=True, timeout=5)
                if dirty.returncode == 0 and dirty.stdout.strip():
                    sha += "-dirty"
            _code_sha = sha
        except Exception:
            _code_sha = None
    return _code_sha


def _curriculum_hash() -> str | None:
    reg = _root() / "corpus" / "sources.json"
    try:
        return hashlib.sha256(reg.read_bytes()).hexdigest()[:12]
    except OSError:
        return None


# ============================================================= paths & manifest


def _paths(name: str) -> dict:
    """Every disk location one creature owns (mirrors train.py's layout)."""
    from .creature import _slug

    slug = _slug(name)
    d = _root() / "data" / "creatures"
    return {"slug": slug, "dir": d,
            "checkpoint": d / f"{slug}.json",
            "log": d / f"{slug}.episodes.jsonl",
            "edges_base": d / f"{slug}.edges",
            "versions": d / f"{slug}.versions"}


def _spec_of(checkpoint: dict) -> str | None:
    cw = checkpoint["geometry"]["concept_web"]
    return cw["external"] if "external" in cw else None


def _manifests(name: str) -> list[dict]:
    vd = _paths(name)["versions"]
    out = []
    if vd.exists():
        for m in vd.glob("*/manifest.json"):
            try:
                out.append(json.loads(m.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
    # the time stamp has 1s resolution — break ties by how far into the log the
    # snapshot reaches, so back-to-back auto tags keep their true order
    return sorted(out, key=lambda r: (r["time"], r.get("log_position", 0), r["tag"]))


# ============================================================= tag


def tag(name: str, label: str, note: str = "", auto: bool = False,
        take_lock: bool = True) -> dict:
    """Snapshot the creature's current on-disk state as version ``label``.

    Copies the checkpoint, the episode log (gzipped — a version must survive
    any later history, including other rollbacks), and the durable store's
    database files, all under the creature lock so no writer is mid-save.
    Returns the manifest. Tagging an existing label is refused, except that an
    ``auto`` re-tag of an identical label is a silent no-op (the tick advanced
    nothing new)."""
    if "/" in label or label in ("", ".", ".."):
        raise ValueError(f"bad version label {label!r}")
    p = _paths(name)
    if not p["checkpoint"].exists():
        raise FileNotFoundError(f"no creature checkpoint at {p['checkpoint']}")
    if take_lock:
        from .episodelog import creature_lock
        with creature_lock(p["dir"]):
            return tag(name, label, note=note, auto=auto, take_lock=False)

    vdir = p["versions"] / label
    if vdir.exists():
        if auto:
            return json.loads((vdir / "manifest.json").read_text(encoding="utf-8"))
        raise FileExistsError(f"version {label!r} already exists")
    vdir.mkdir(parents=True)

    chk = json.loads(p["checkpoint"].read_text(encoding="utf-8"))
    shutil.copy2(p["checkpoint"], vdir / "checkpoint.json")
    log_bytes = 0
    if p["log"].exists():
        log_bytes = p["log"].stat().st_size
        with p["log"].open("rb") as src, gzip.open(vdir / "log.jsonl.gz", "wb") as dst:
            shutil.copyfileobj(src, dst)
    spec = _spec_of(chk)
    copied = []
    for f in store_files(spec, p["edges_base"]):
        if f.name.endswith("-shm"):        # shared-memory index: rebuilt on open, never copied
            continue
        dest = vdir / "store" / f.relative_to(p["dir"])
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dest)
        copied.append(str(f.relative_to(p["dir"])))

    manifest = {
        "tag": label, "note": note, "auto": auto, "name": name, "slug": p["slug"],
        "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "log_position": chk.get("log_position", 0), "log_bytes": log_bytes,
        "episodes_seen": chk.get("counters", {}).get("episodes_seen", 0),
        "stages": len(chk.get("ledger", {}).get("passed_stages", [])),
        "store_spec": spec, "store_files": copied,
        "provenance": chk.get("provenance") or stamp(),
    }
    (vdir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def autosnap(name: str, position: int, keep: int = 5, take_lock: bool = True) -> dict | None:
    """The training tick's snapshot: tag ``auto-<log position>`` and prune old
    auto tags down to ``keep``. Never raises — a failed snapshot must not fail
    the training run it rides on."""
    try:
        m = tag(name, f"auto-{position}", note="training tick", auto=True, take_lock=take_lock)
        autos = [r for r in _manifests(name) if r.get("auto")]
        for old in autos[:-keep] if keep > 0 else autos:
            shutil.rmtree(_paths(name)["versions"] / old["tag"], ignore_errors=True)
        return m
    except Exception as e:
        print(f"   (auto-snapshot skipped: {e})")
        return None


# ============================================================= rollback


def rollback(name: str, label: str, take_lock: bool = True) -> dict:
    """Restore version ``label``: rotate the CURRENT checkpoint, log and store
    files aside (``.<timestamp>.bak`` — nothing is deleted), then copy the
    tagged state back into place. Restoring the log too is what makes this a
    genuine rollback — otherwise the next ``load`` would replay the abandoned
    tail right back over the old checkpoint."""
    p = _paths(name)
    vdir = p["versions"] / label
    manifest_path = vdir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"no version {label!r} for '{name}' (see --list)")
    if take_lock:
        from .episodelog import creature_lock
        with creature_lock(p["dir"]):
            return rollback(name, label, take_lock=False)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ts = time.strftime(_TS)
    live_spec = _spec_of(json.loads(p["checkpoint"].read_text(encoding="utf-8"))) \
        if p["checkpoint"].exists() else manifest["store_spec"]
    rotated = []
    for f in [p["checkpoint"], p["log"], *store_files(live_spec, p["edges_base"])]:
        if f.exists():
            f.rename(f.with_name(f"{f.name}.{ts}.bak"))
            rotated.append(f.name)

    shutil.copy2(vdir / "checkpoint.json", p["checkpoint"])
    if (vdir / "log.jsonl.gz").exists():
        with gzip.open(vdir / "log.jsonl.gz", "rb") as src, p["log"].open("wb") as dst:
            shutil.copyfileobj(src, dst)
    for rel in manifest.get("store_files", []):
        shutil.copy2(vdir / "store" / rel, p["dir"] / rel)
    return {"restored": label, "rotated_aside": rotated, "timestamp": ts,
            "note": "restart relweb-serve if it is running — its open log handle is now stale"}


# ============================================================= diff


def _committed_facts(checkpoint: dict, store_base: Path | None) -> dict[tuple[str, str], list[str]]:
    """The committed belief set a checkpoint (plus its store files) holds:
    ``(src, tgt) -> relation frames`` for every edge with >= commit_k witnesses."""
    k = checkpoint["params"]["commit_k"]
    cw = checkpoint["geometry"]["concept_web"]
    if "external" not in cw:
        return {(e["src"], e["tgt"]): sorted(e["rel"]) for e in cw["edges"]
                if len(e["sources"]) >= k}
    if store_base is None:
        raise FileNotFoundError("external concept web, but no store files to read")
    st = open_store(cw["external"], store_base)
    try:
        return {(s, t): sorted(ev["frames"]) for s, t, ev in st.committed(k)}
    finally:
        st.close()


def _version_state(name: str, label: str | None) -> tuple[dict, Path | None, str]:
    """(checkpoint dict, store base path, description) for a tag — or for the
    live state when ``label`` is None."""
    p = _paths(name)
    if label is None:
        chk = json.loads(p["checkpoint"].read_text(encoding="utf-8"))
        return chk, p["edges_base"], "current"
    vdir = p["versions"] / label
    if not (vdir / "checkpoint.json").exists():
        raise FileNotFoundError(f"no version {label!r} for '{name}' (see --list)")
    chk = json.loads((vdir / "checkpoint.json").read_text(encoding="utf-8"))
    return chk, vdir / "store" / f"{p['slug']}.edges", label


def diff(name: str, a: str, b: str | None = None) -> dict:
    """The BELIEF DIFF between two versions (or a version and now): committed
    facts gained, lost, and re-expressed, plus the counters' drift. This is the
    payoff of belief-as-projection: two states diff as fact sets, not as bytes."""
    chk_a, base_a, label_a = _version_state(name, a)
    chk_b, base_b, label_b = _version_state(name, b)
    facts_a = _committed_facts(chk_a, base_a)
    facts_b = _committed_facts(chk_b, base_b)
    gained = sorted(set(facts_b) - set(facts_a))
    lost = sorted(set(facts_a) - set(facts_b))
    reexpressed = sorted(kk for kk in set(facts_a) & set(facts_b) if facts_a[kk] != facts_b[kk])
    ca, cb = chk_a.get("counters", {}), chk_b.get("counters", {})
    return {
        "from": label_a, "to": label_b,
        "gained": [{"src": s, "tgt": t, "rel": facts_b[(s, t)]} for s, t in gained],
        "lost": [{"src": s, "tgt": t, "rel": facts_a[(s, t)]} for s, t in lost],
        "reexpressed": [{"src": s, "tgt": t, "rel_from": facts_a[(s, t)],
                         "rel_to": facts_b[(s, t)]} for s, t in reexpressed],
        "committed": {"from": len(facts_a), "to": len(facts_b)},
        "episodes_seen": {"from": ca.get("episodes_seen", 0), "to": cb.get("episodes_seen", 0)},
        "stages": {"from": len(chk_a.get("ledger", {}).get("passed_stages", [])),
                   "to": len(chk_b.get("ledger", {}).get("passed_stages", []))},
    }


# ============================================================= CLI


def main() -> int:
    ap = argparse.ArgumentParser(description="Tag, list, diff and roll back creature versions.")
    ap.add_argument("--name", default="scholar")
    ap.add_argument("--tag", metavar="LABEL", help="snapshot the current state as LABEL")
    ap.add_argument("--note", default="", help="free-text note stored with --tag")
    ap.add_argument("--list", action="store_true", help="list versions")
    ap.add_argument("--rollback", metavar="LABEL", help="restore LABEL (current state rotated aside)")
    ap.add_argument("--diff", nargs="+", metavar="LABEL",
                    help="belief diff: one LABEL diffs against the current state, two diff each other")
    args = ap.parse_args()

    if args.tag:
        m = tag(args.name, args.tag, note=args.note)
        print(f"tagged '{m['tag']}' — {m['episodes_seen']} episodes, "
              f"{m['stages']} stage(s), log at {m['log_position']} "
              f"(code {m['provenance'].get('code') or '?'})")
        return 0
    if args.list:
        rows = _manifests(args.name)
        if not rows:
            print(f"(no versions for '{args.name}' yet — create one with --tag)")
            return 0
        print(f"versions of '{args.name}':")
        for r in rows:
            kind = "auto" if r.get("auto") else "tag "
            print(f"   [{kind}] {r['tag']:24s} {r['time']}  episodes={r['episodes_seen']:<7d} "
                  f"stages={r['stages']:<2d} code={r['provenance'].get('code') or '?'}"
                  + (f"  — {r['note']}" if r.get("note") else ""))
        return 0
    if args.rollback:
        r = rollback(args.name, args.rollback)
        print(f"restored '{r['restored']}'; rotated aside: {', '.join(r['rotated_aside']) or '(nothing)'}")
        print(f"note: {r['note']}")
        return 0
    if args.diff:
        if len(args.diff) > 2:
            ap.error("--diff takes one or two labels")
        d = diff(args.name, args.diff[0], args.diff[1] if len(args.diff) == 2 else None)
        print(f"belief diff {d['from']} -> {d['to']}: "
              f"{d['committed']['from']} -> {d['committed']['to']} committed facts, "
              f"{d['episodes_seen']['from']} -> {d['episodes_seen']['to']} episodes, "
              f"{d['stages']['from']} -> {d['stages']['to']} stages")
        for row in d["gained"]:
            print(f"   + {row['src']} -> {row['tgt']}  [{', '.join(row['rel'])}]")
        for row in d["lost"]:
            print(f"   - {row['src']} -> {row['tgt']}  [{', '.join(row['rel'])}]")
        for row in d["reexpressed"]:
            print(f"   ~ {row['src']} -> {row['tgt']}  [{', '.join(row['rel_from'])}] -> [{', '.join(row['rel_to'])}]")
        if not (d["gained"] or d["lost"] or d["reexpressed"]):
            print("   (no committed-fact changes)")
        return 0
    ap.error("give --tag, --list, --rollback, or --diff")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
