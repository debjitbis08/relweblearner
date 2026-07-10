"""Real-corpus loader — turn public-domain books into training episodes.

The synthetic firehoses (:mod:`patternbooks`, :mod:`mathbooks`, :mod:`kidbooks`)
manufacture a hidden functional world with a picture/tap channel. Real books have
no such channel: a page of a public-domain reader is just a *word sequence*. That
is enough to train this creature — frame induction works on sequences alone, and
a parsed frame's two fillers are oriented by token order when no picture is
present (``curriculum._orient``'s documented fallback). What real text does NOT
give is a grounding oracle, so there is no synthetic "truth" to score against —
which is correct: real reading is learning the actual relational structure of the
text, not recovering a generator's secret.

This module strips Project Gutenberg boilerplate and page furniture (lesson
headers, ``[Illustration: …]`` blocks, phonics/word-list drills, ALL-CAPS
headings), segments the body into sentences, and tokenises each into the same
``{book, tokens, picture, marks}`` episode dict the generators emit — so a real
corpus and a synthetic one flow through :meth:`Creature.ingest` identically.

``episodes_from_text`` is pure (no I/O) so it is unit-tested on inline samples;
``fetch_gutenberg`` downloads one public-domain book. Corpus assembly (which
sources, in what order) lives in :mod:`~relweblearner.datasets.registry`.
"""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

_UA = {"User-Agent": "relweblearner-corpus/0.1 (public-domain training corpus)"}


def gutenberg_urls(ref: int) -> list[str]:
    """Gutenberg serves plain text under a few stable layouts; try them in order."""
    return [
        f"https://www.gutenberg.org/cache/epub/{ref}/pg{ref}.txt",
        f"https://www.gutenberg.org/files/{ref}/{ref}-0.txt",
        f"https://www.gutenberg.org/files/{ref}/{ref}.txt",
    ]


def fetch_gutenberg(ref: int, dest: str | Path, *, force: bool = False) -> bool:
    """Download one Gutenberg source's plain text to ``dest`` (idempotent). Returns
    True if the file is present afterwards."""
    dest = Path(dest)
    if dest.exists() and not force:
        return True
    for url in gutenberg_urls(ref):
        try:
            data = urllib.request.urlopen(
                urllib.request.Request(url, headers=_UA), timeout=30
            ).read().decode("utf-8", "replace")
        except Exception:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(data, encoding="utf-8")
        return True
    return False

# --------------------------------------------------------------- boilerplate cut
_START = re.compile(r"\*\*\*\s*START OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.I)
_END = re.compile(r"\*\*\*\s*END OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.I)

# --------------------------------------------------------------- page furniture
_BRACKET = re.compile(r"\[(illustration|footnote|sidenote)[^\]]*\]", re.I | re.S)
_LESSON = re.compile(r"^\s*(lesson|exercise|story|chapter|section|part|no)\b.*$", re.I)
_ROMAN = re.compile(r"^\s*[ivxlcdm]+\.?\s*$", re.I)          # roman-numeral heading
_NUMHEAD = re.compile(r"^[\s\d.\-—]+$")                       # digits/rule only
_TERM = re.compile(r"[.!?;:]")                               # sentence terminals
_WORDCH = re.compile(r"[a-z']+")                             # a token = letters/apostrophe

# tokens that are legitimately one letter; every other single-letter token is
# phonics-drill residue and is dropped.
_KEEP_1 = {"a", "i", "o"}

MIN_TOKENS = 2
MAX_TOKENS = 16


def _strip_boilerplate(text: str) -> str:
    m1, m2 = _START.search(text), _END.search(text)
    start = m1.end() if m1 else 0
    end = m2.start() if m2 else len(text)
    return text[start:end]


def _is_furniture(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if _LESSON.match(s) or _ROMAN.match(s) or _NUMHEAD.match(s):
        return True
    # ALL-CAPS heading (a title line, not prose): letters present, none lowercase
    letters = [c for c in s if c.isalpha()]
    if letters and not any(c.islower() for c in letters):
        return True
    return False


def _tokenise(sentence: str) -> list[str]:
    toks = _WORDCH.findall(sentence.lower())
    toks = [t.strip("'") for t in toks]
    toks = [t for t in toks if t and (len(t) > 1 or t in _KEEP_1)]
    return toks


def episodes_from_text(text: str, book: str) -> list[dict]:
    """Segment one book's raw text into ``{book, tokens, picture, marks}`` episodes.

    Pure and deterministic. Boilerplate and page furniture are removed, the body is
    split into paragraphs (blank-line separated), each paragraph joined and split
    into sentences on terminal punctuation, and each sentence tokenised. Sentences
    outside ``[MIN_TOKENS, MAX_TOKENS]`` or dominated by single-letter drill tokens
    are dropped. ``picture``/``marks`` are ``None`` — real pages carry no tap.
    """
    body = _strip_boilerplate(text)
    body = _BRACKET.sub(" ", body)

    episodes: list[dict] = []
    for para in re.split(r"\n[ \t]*\n", body):
        lines = [ln for ln in para.splitlines() if not _is_furniture(ln)]
        if not lines:
            continue
        joined = " ".join(ln.strip() for ln in lines)
        # split into sentences; a terminal keeps its clause, a trailing clause with
        # no terminal (common in verse) is taken whole.
        for sent in re.split(r"(?<=[.!?;:])\s+", joined):
            toks = _tokenise(sent)
            if not (MIN_TOKENS <= len(toks) <= MAX_TOKENS):
                continue
            # a real utterance has >=2 real (multi-letter) words; this rejects the
            # phonics/letter-drill residue ("a o n d g r" -> "a o") that survives
            # tokenisation as a run of one-letter tokens.
            if sum(len(t) >= 2 for t in toks) < 2:
                continue
            episodes.append({"book": book, "tokens": toks, "picture": None, "marks": None})
    return episodes
