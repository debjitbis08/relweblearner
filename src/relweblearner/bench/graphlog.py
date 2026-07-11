"""GraphLog (external benchmark) through the transport core.

GraphLog [Sinha et al., ICML 2020] is a suite of 57 relation-prediction
worlds, each generated from its own set of BINARY composition rules
(``r1 ∘ r2 → r3``): an instance is a small graph plus a held-out query edge
``(u, v, ?)`` whose relation must be inferred compositionally. Two properties
make it the right external test here:

* the data contains **zero converse 2-cycles** (measured: 0/14,943 edges on
  rule_0), so every bit of structure RelWeb can discover must come through
  the 3-cycle composition evidence + defect gate added after the internal
  falsification run — this is that mechanism's external validation;
* GraphLog rule sets are arbitrary, while RelWeb's frozen algebra is abelian
  Z. A world's rules may force ``g(a) + g(b) = g(c)`` assignments that
  collide (two relations, one transport) or contradict outright. Where the
  Z-embedding is degenerate, transport prediction MUST degrade — a
  structural, pre-registered failure mode, diagnosed per world by
  :func:`z_diagnostic` from the ground-truth rules (which the learner never
  sees).

Honest scope: this evaluates the GEOMETRY CORE (discovery + transport) on
gold triples, bypassing the language pipeline (frames, k-witness commitment
— GraphLog states each edge once, as ground truth). Systems:

* ``transport`` — cmaps pooled from N training instances (nodes prefixed per
  instance, so triangles form only within an instance), ``TR.infer`` with
  the composition gate, then per-test-instance BFS potential: predict the
  relation whose learned transport equals phi(v) - phi(u).
* ``cyk-miner`` — the statistical competitor: the same triangle mining, then
  test-time path search u→v (length ≤ 5) with CYK reduction over the mined
  binary rules.
* ``cyk-oracle`` — CYK with the TRUE rules: the ceiling of path-reduction.
* ``majority`` — the floor.

Usage: relweb-graphlog [--worlds rule_0,rule_1,...] [--n-train 150]
Data: data/graphlog/graphlog_v1.1 (RELWEB_GRAPHLOG overrides).
"""

from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

from .. import transport as TR

DATA = Path(os.environ.get("RELWEB_GRAPHLOG", "data/graphlog/graphlog_v1.1"))
MAX_PATH = 5                 # generation config: max_path_len = 5
DEFAULT_WORLDS = ["rule_0", "rule_1", "rule_4", "rule_7", "rule_9", "rule_12"]


def load_world(name: str, n_train: int = 150) -> dict:
    base = DATA / "train" / name
    train = [json.loads(l) for l in
             (base / "train.jsonl").read_text().splitlines()[:n_train]]
    test = [json.loads(l) for l in (base / "test.jsonl").read_text().splitlines()]
    rules = json.loads((base / f"rules_{name.split('_')[1]}.json").read_text())
    return {"name": name, "train": train, "test": test,
            "rules": {tuple(k.split(",")): v for k, v in rules.items()}}


# ------------------------------------------------------------------ transport

def build_cmaps(graphs: list[dict]) -> dict[str, set]:
    """Pooled class maps with per-instance node prefixes: triangles (the 3-cycle
    evidence) can only form within one instance's graph, exactly as they
    should."""
    cmaps: dict[str, set] = defaultdict(set)
    for i, g in enumerate(graphs):
        for u, v, rel in g["edges"]:
            cmaps[rel].add((f"g{i}n{u}", f"g{i}n{v}"))
    return dict(cmaps)


def learn_transports(graphs: list[dict]) -> dict[str, int]:
    """Discovered transports: TR.infer (composition mining + defect gate) over
    the pooled maps; only classes CONSTRAINED into a multi-class component
    carry meaning (a lone class's gauge value says nothing about others)."""
    cmaps = build_cmaps(graphs)
    sectors, groups = TR.infer(cmaps)
    members = Counter(groups.values())
    return {r: s.transport for r, s in sectors.items()
            if s.transport is not None and members[groups[r]] > 1
            and s.sector in (TR.ANTISYMMETRIC, TR.SYMMETRIC)}


def transport_predict(rec: dict, g_of: dict[str, int], majority: str) -> str:
    """BFS potential over the instance edges whose class has a learned
    transport; predict the relation sitting exactly at phi(v) - phi(u).
    Sign and scale are internally consistent by construction, so the global
    gauge choice cancels. Ties break by training frequency via ``majority``
    ordering being used only as the final fallback."""
    u0, v0, _ = rec["query"]
    adj: dict[int, list] = defaultdict(list)
    for u, v, rel in rec["edges"]:
        g = g_of.get(rel)
        if g is None:
            continue
        adj[u].append((v, g))
        adj[v].append((u, -g))
    phi = {u0: 0}
    frontier = [u0]
    while frontier:
        nxt = []
        for x in frontier:
            for y, g in adj[x]:
                if y not in phi:
                    phi[y] = phi[x] + g
                    nxt.append(y)
        frontier = nxt
    if v0 not in phi:
        return majority
    val = phi[v0]
    hits = sorted(r for r, g in g_of.items() if g == val)
    return hits[0] if hits else majority


# ------------------------------------------------------------------ CYK miner

def mine_rules(graphs: list[dict], min_support: int = 2,
               min_conf: float = 0.5) -> dict[tuple, str]:
    """The statistical competitor's rule induction: for every 2-path
    ``(s -r1-> m -r2-> t)`` with a direct edge ``(s -r3-> t)``, count
    ``(r1, r2) -> r3``; keep the majority head at support and confidence
    floors. This is the same triangle evidence the transport learner mines —
    consumed as rewrite rules instead of algebra constraints."""
    votes: dict[tuple, Counter] = defaultdict(Counter)
    for g in graphs:
        out_idx: dict[int, list] = defaultdict(list)
        direct: dict[tuple, list] = defaultdict(list)
        for u, v, rel in g["edges"]:
            out_idx[u].append((v, rel))
            direct[(u, v)].append(rel)
        for u, v, rel in g["edges"]:
            for m, r2 in out_idx[v]:
                for r3 in direct.get((u, m), ()):
                    if m != u:
                        votes[(rel, r2)][r3] += 1
    rules: dict[tuple, str] = {}
    for body, heads in votes.items():
        head, n = heads.most_common(1)[0]
        if n >= min_support and n / sum(heads.values()) >= min_conf:
            rules[body] = head
    return rules


def cyk_predict(rec: dict, rules: dict[tuple, str], majority: str,
                max_len: int = MAX_PATH) -> str:
    """Path search u→v (length ≤ max_len), CYK reduction of each label
    sequence over the binary rules; predict the most common single-relation
    reduction across found paths."""
    u0, v0, _ = rec["query"]
    out_idx: dict[int, list] = defaultdict(list)
    for u, v, rel in rec["edges"]:
        out_idx[u].append((v, rel))
    results: Counter = Counter()
    stack = [(u0, [])]
    while stack:
        node, labels = stack.pop()
        if node == v0 and labels:
            for r in _reduce(tuple(labels), rules):
                results[r] += 1
            continue
        if len(labels) >= max_len:
            continue
        for y, rel in out_idx[node]:
            stack.append((y, labels + [rel]))
    return results.most_common(1)[0][0] if results else majority


def _reduce(labels: tuple, rules: dict[tuple, str], _memo=None) -> set:
    """All single relations a label sequence can reduce to (CYK over spans)."""
    if _memo is None:
        _memo = {}
    if labels in _memo:
        return _memo[labels]
    if len(labels) == 1:
        return {labels[0]}
    out: set = set()
    for i in range(1, len(labels)):
        for a in _reduce(labels[:i], rules, _memo):
            for b in _reduce(labels[i:], rules, _memo):
                h = rules.get((a, b))
                if h is not None:
                    out.add(h)
    _memo[labels] = out
    return out


# ------------------------------------------------------------------ diagnostic

def z_diagnostic(rules: dict[tuple, str]) -> dict:
    """Can the TRUE rule set live in abelian Z at all? Solve the homogeneous
    system g(a) + g(b) - g(c) = 0 over Q by elimination and report how
    separable a generic solution is: ``collisions`` counts relation pairs
    FORCED to share a transport (indistinguishable to any abelian embedding,
    however clever). The learner never sees this — it is the pre-registered
    structural bound on what transport prediction can reach."""
    rels = sorted({x for k, v in rules.items() for x in (*k, v)})
    idx = {r: i for i, r in enumerate(rels)}
    rows = []
    for (a, b), c in sorted(rules.items()):
        row = [Fraction(0)] * len(rels)
        row[idx[a]] += 1
        row[idx[b]] += 1
        row[idx[c]] -= 1
        rows.append(row)
    # Gaussian elimination to reduced row echelon form
    pivots = []
    r = 0
    for col in range(len(rels)):
        piv = next((i for i in range(r, len(rows)) if rows[i][col] != 0), None)
        if piv is None:
            continue
        rows[r], rows[piv] = rows[piv], rows[r]
        rows[r] = [x / rows[r][col] for x in rows[r]]
        for i in range(len(rows)):
            if i != r and rows[i][col] != 0:
                f = rows[i][col]
                rows[i] = [x - f * y for x, y in zip(rows[i], rows[r])]
        pivots.append(col)
        r += 1
    free = [c for c in range(len(rels)) if c not in pivots]
    # basis of the solution space: one vector per free variable
    basis = []
    for fc in free:
        vec = [Fraction(0)] * len(rels)
        vec[fc] = Fraction(1)
        for i, pc in enumerate(pivots):
            vec[pc] = -rows[i][fc]
        basis.append(vec)
    collisions = sum(
        1 for i in range(len(rels)) for j in range(i + 1, len(rels))
        if all(v[i] == v[j] for v in basis))
    return {"n_rels": len(rels), "dof": len(free), "collisions": collisions}


# ------------------------------------------------------------------ runner

def run_world(name: str, n_train: int) -> dict:
    w = load_world(name, n_train)
    majority = Counter(r["target"] for r in w["train"]).most_common(1)[0][0]
    g_of = learn_transports(w["train"])
    mined = mine_rules(w["train"])
    systems = {
        "majority": lambda rec: majority,
        "transport": lambda rec: transport_predict(rec, g_of, majority),
        "cyk-miner": lambda rec: cyk_predict(rec, mined, majority),
        "cyk-oracle": lambda rec: cyk_predict(rec, w["rules"], majority),
    }
    acc = {s: sum(fn(rec) == rec["query"][2] for rec in w["test"]) / len(w["test"])
           for s, fn in systems.items()}
    diag = z_diagnostic(w["rules"])
    return {"world": name, "n_train": n_train, "n_test": len(w["test"]),
            "accuracy": {s: round(a, 4) for s, a in acc.items()},
            "z_diagnostic": diag,
            "learned_transports": {r: g_of[r] for r in sorted(g_of)},
            "mined_rules": len(mined), "true_rules": len(w["rules"])}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--worlds", default=",".join(DEFAULT_WORLDS))
    ap.add_argument("--n-train", type=int, default=150)
    ap.add_argument("--out", default="results/graphlog")
    args = ap.parse_args()
    t0 = time.time()
    results = []
    for name in args.worlds.split(","):
        r = run_world(name.strip(), args.n_train)
        print(f"{r['world']}: " + "  ".join(
            f"{s}={a:.3f}" for s, a in r["accuracy"].items())
            + f"  (collisions={r['z_diagnostic']['collisions']}, "
              f"transports={len(r['learned_transports'])}/{r['z_diagnostic']['n_rels']},"
              f" {time.time() - t0:.0f}s)")
        results.append(r)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(results, indent=1))
    lines = ["# GraphLog (external): transport core vs rule mining", "",
             f"{len(results)} worlds, {args.n_train} training instances each, "
             f"full test splits; {time.time() - t0:.0f}s.", "",
             "| world | majority | transport | cyk-miner | cyk-oracle | "
             "Z-collisions | transports learned |", "|---|---|---|---|---|---|---|"]
    for r in results:
        a = r["accuracy"]
        lines.append(
            f"| {r['world']} | {a['majority']:.3f} | {a['transport']:.3f} | "
            f"{a['cyk-miner']:.3f} | {a['cyk-oracle']:.3f} | "
            f"{r['z_diagnostic']['collisions']} | "
            f"{len(r['learned_transports'])}/{r['z_diagnostic']['n_rels']} |")
    (out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
