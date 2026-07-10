"""The corpus REGISTRY — one declarative list of training sources, loaded on demand.

``corpus/sources.json`` is the single source of truth for what the creature reads:
each entry has a stable ``id`` and a ``kind`` — ``generated`` (a seeded synthetic
world with the picture/tap channel) or ``gutenberg`` (a public-domain book). This
module turns any entry into a list of ``{book, tokens, picture, marks}`` episodes,
fetching Gutenberg text on demand. Adding data is a one-line append to the JSON —
no code change — and the ledger on the creature (:attr:`Creature.read_sources`)
means a scheduled run ingests only the ids it has not seen yet.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import factsource, kidbooks, mathbooks, patternbooks, realbooks, sciencebooks

# generator name (as written in sources.json) -> module exposing generate()
_GENERATORS = {
    "patternbooks": patternbooks,
    "mathbooks": mathbooks,
    "kidbooks": kidbooks,
    "sciencebooks": sciencebooks,
}


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def registry_path(path: str | Path | None = None) -> Path:
    return Path(path) if path else _root() / "corpus" / "sources.json"


def raw_dir(path: str | Path | None = None) -> Path:
    return Path(path) if path else _root() / "corpus" / "raw"


def _doc(path: str | Path | None = None) -> dict:
    return json.loads(registry_path(path).read_text(encoding="utf-8"))


def load_registry(path: str | Path | None = None) -> list[dict]:
    """The ordered list of source entries from ``corpus/sources.json``."""
    return _doc(path)["sources"]


def load_stages(path: str | Path | None = None) -> list[dict]:
    """The graded curriculum stages (ordered) from ``corpus/sources.json``."""
    return _doc(path).get("stages", [])


def source_by_id(registry: list[dict], sid: str) -> dict | None:
    return next((s for s in registry if s["id"] == sid), None)


def source_episodes(entry: dict, *, raw: str | Path | None = None, fetch: bool = True) -> list[dict]:
    """Materialise one registry entry into training episodes.

    ``generated`` entries call the named generator with its params; ``gutenberg``
    entries read (fetching first if ``fetch`` and the raw file is absent) the book
    and segment it. Raises ``LookupError``/``FileNotFoundError`` on an unusable
    entry so the caller can skip it and move on.
    """
    kind = entry.get("kind")
    if kind == "generated":
        gen = _GENERATORS.get(entry["generator"])
        if gen is None:
            raise LookupError(f"unknown generator {entry['generator']!r} in source {entry['id']!r}")
        return gen.generate(**entry.get("params", {}))[0]

    if kind == "gutenberg":
        rawd = raw_dir(raw)
        path = rawd / f"{entry['ref']}.txt"
        if not path.exists() and fetch:
            realbooks.fetch_gutenberg(entry["ref"], path)
        if not path.exists():
            raise FileNotFoundError(f"{path} missing (fetch failed or disabled) for {entry['id']!r}")
        text = path.read_text(encoding="utf-8", errors="replace")
        return realbooks.episodes_from_text(text, entry.get("title", entry["id"]))

    if kind in ("wordnet", "wikidata"):
        triples = cached_triples(entry, raw=raw, fetch=fetch)
        n = entry.get("episodes") or max(6000, len(triples) * 40)
        return factsource.episodes_from_triples(
            triples, _entry_frames(entry), entry["id"], n_episodes=n, seed=entry.get("seed", 0))

    raise LookupError(f"unknown source kind {kind!r} in {entry.get('id')!r}")


# ------------------------------------------------------- external fact sources (cached)

def _entry_frames(entry: dict) -> list:
    """A fact source's paraphrase frames — ``frames`` (a list of constructions,
    the P9 label discipline) or the legacy single ``frame``."""
    return entry.get("frames") or [entry["frame"]]


def _triples_path(entry: dict, raw: str | Path | None = None) -> Path:
    return raw_dir(raw) / f"{entry['id']}.triples.json"


def cached_triples(entry: dict, *, raw: str | Path | None = None, fetch: bool = True) -> list[tuple[str, str]]:
    """Fetch a fact source's ``(subject, object)`` triples ONCE and cache them to
    ``corpus/raw/<id>.triples.json``; later reads (episodes AND worksheet) use the
    cache, so the two are consistent and the run works offline after first fetch.
    Raises on network/rate-limit errors so the caller can skip and retry later."""
    path = _triples_path(entry, raw)
    if path.exists():
        doc = json.loads(path.read_text(encoding="utf-8"))
        return [tuple(t) for t in doc["triples"]]
    if not fetch:
        raise FileNotFoundError(f"{path} missing (fetch disabled) for {entry['id']!r}")
    if entry["kind"] == "wordnet":
        triples = factsource.wordnet_triples(entry["root"], entry.get("max", 150))
    elif entry["kind"] == "wikidata":
        triples = factsource.wikidata_triples(entry["relation"], entry.get("max", 200))
    else:
        raise LookupError(f"{entry['kind']!r} is not a fact source")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"source": entry.get("title", entry["id"]),
                                "triples": [list(t) for t in triples]}), encoding="utf-8")
    return triples


def source_worksheet(entry: dict, *, raw: str | Path | None = None) -> list[tuple[str, str]]:
    """The gradable worksheet for a source (empty if it has no truth to grade — e.g.
    a gutenberg book). Grounded generators quiz their hidden world; fact sources
    blank the object of each cached triple."""
    kind = entry.get("kind")
    if kind == "generated":
        gen = _GENERATORS.get(entry["generator"])
        if gen is None or not hasattr(gen, "quiz"):
            return []
        p = entry.get("params", {})
        return list(gen.quiz(gen._world(p.get("seed", 0)), p.get("level", 2)))
    if kind in ("wordnet", "wikidata"):
        try:
            triples = cached_triples(entry, raw=raw, fetch=False)
        except FileNotFoundError:
            return []
        return factsource.worksheet_from_triples(triples, _entry_frames(entry))
    return []


def pending_sources(registry: list[dict], read_ids: set[str]) -> list[dict]:
    """The registry entries a creature has not ingested yet, in registry order."""
    return [s for s in registry if s["id"] not in read_ids]
