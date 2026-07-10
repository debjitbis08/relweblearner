"""Pre-fetch the Gutenberg sources in ``corpus/sources.json`` into ``corpus/raw/``.

Optional convenience: the registry fetches each book on demand at ingest time too
(``datasets.registry.source_episodes``), so training works without running this
first. Use it to warm the cache (e.g. before an offline stretch). Idempotent: a
present file is skipped unless ``--force``.

Run: poetry run python scripts/fetch_corpus.py [--force]
"""

from __future__ import annotations

import sys
import time

from relweblearner.datasets import realbooks as RB
from relweblearner.datasets import registry as R


def main() -> int:
    force = "--force" in sys.argv
    registry = R.load_registry()
    raw = R.raw_dir()
    raw.mkdir(parents=True, exist_ok=True)
    books = [s for s in registry if s.get("kind") == "gutenberg"]
    print(f"fetching {len(books)} public-domain books -> {raw}")
    ok = True
    for s in books:
        dest = raw / f"{s['ref']}.txt"
        if dest.exists() and not force:
            print(f"  skip {s['ref']} ({dest.stat().st_size // 1024}K)  {s.get('title','')[:40]}")
            continue
        got = RB.fetch_gutenberg(s["ref"], dest, force=force)
        print(f"  {'got ' if got else 'FAIL'} {s['ref']} -> {dest.name}  {s.get('title','')[:40]}")
        ok = ok and got
        time.sleep(1)   # be polite to Gutenberg
    print("done." if ok else "done WITH FAILURES.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
