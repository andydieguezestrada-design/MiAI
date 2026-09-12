
from __future__ import annotations
import argparse, json, math, re, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from python.rag.store import RAGStore

STOPWORDS = set("""
a al algo ante antes con como contra de del desde el ella ellas ellos en entre era es
esta estas este esto estos fue ha hasta la las le lo los más me mi mis muy no nos o
para pero por que se sin sobre su sus te tu tus un una uno unos unas y ya qué cómo
""".split())

TOKEN_RE = re.compile(r"[\wÀ-ÿ]{2,}", re.UNICODE)

def tokens(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text.lower(), re.UNICODE)) - STOPWORDS

def improved_lexical_search(store, project: str, query: str, limit: int, threshold: float):
    """V0.12-B1 experimental lexical scorer: stopwords + IDF-weighted overlap."""
    with store._connect() as conn:
        rows = conn.execute("SELECT * FROM chunks WHERE project = ?", (project,)).fetchall()
    qt = tokens(query)
    if not qt:
        return []
    n = len(rows)
    df = {t: sum(t in tokens(r["title"] + " " + r["content"]) for r in rows) for t in qt}
    weights = {t: 1.0 + math.log(n / max(1, df[t])) for t in qt}
    denom = max(1e-12, sum(weights.values()))
    scored = []
    qlow = query.lower()
    for r in rows:
        text = (r["title"] + " " + r["content"])
        rt = tokens(text)
        score = sum(weights[t] for t in qt if t in rt) / denom
        if qlow in text.lower():
            score = max(score, 0.90)
        if any(t in tokens(r["title"]) for t in qt):
            score = min(1.0, score + 0.12)
        if score >= threshold and score > 0:
            scored.append({
                "id": r["id"], "title": r["title"], "score": score
            })
    return sorted(scored, key=lambda x: x["score"], reverse=True)[:limit]

def expected_hit(item, results):
    gold = item["gold"]
    if gold is None:
        return len(results) == 0
    return any(gold in r["title"].lower().replace(" ", "_") or
               (gold == "vision" and "vision" in r["title"].lower()) or
               (gold == "streaming" and "streaming" in r["title"].lower()) or
               (gold == "arquitectura" and "arquitectura" in r["title"].lower()) or
               (gold == "memoria" and "memoria" in r["title"].lower()) or
               (gold == "herramientas" and "herramientas" in r["title"].lower()) or
               (gold == "seguridad" and "seguridad" in r["title"].lower())
               for r in results)

def evaluate(store, queries, search_fn, limit, threshold):
    positive = [q for q in queries if q["type"] == "positive"]
    negative = [q for q in queries if q["type"] == "negative"]
    details = []
    for q in queries:
        t0 = time.perf_counter()
        results = search_fn(store, "rag_quality_b1", q["text"], limit, threshold)
        latency_ms = (time.perf_counter() - t0) * 1000
        hit = expected_hit(q, results)
        details.append({
            "id": q["id"], "type": q["type"], "query": q["text"],
            "hit": hit, "results": [(r["title"], round(float(r["score"]), 6)) for r in results],
            "latency_ms": round(latency_ms, 3)
        })
    pp = sum(d["hit"] for d in details if d["type"] == "positive") / len(positive)
    nna = sum(d["hit"] for d in details if d["type"] == "negative") / len(negative)
    fpr = 1 - nna
    mrr_values = []
    for d, q in zip(details, queries):
        if q["type"] != "positive":
            continue
        rank = None
        for i, (title, _) in enumerate(d["results"], 1):
            if q["gold"] in title.lower():
                rank = i
                break
        mrr_values.append(0 if rank is None else 1/rank)
    return {
        "positive_hit_rate": round(pp, 4),
        "negative_rejection_rate": round(nna, 4),
        "false_positive_rate": round(fpr, 4),
        "mrr": round(sum(mrr_values)/len(mrr_values), 4),
        "avg_latency_ms": round(sum(d["latency_ms"] for d in details)/len(details), 3),
        "details": details
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["baseline","v12-lexical"], default="baseline")
    ap.add_argument("--threshold", type=float, default=0.08)
    ap.add_argument("--limit", type=int, default=3)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    data = json.loads((Path(__file__).parent/"dataset.json").read_text(encoding="utf-8"))
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        store = RAGStore(str(Path(td)/"rag.sqlite3"))
        for d in data["documents"]:
            store.add_document(data["project"], d["title"], d["content"])
        if args.mode == "baseline":
            fn = lambda s,p,q,l,t: s.search(p,q,limit=l)
        else:
            fn = improved_lexical_search
        result = evaluate(store, data["queries"], fn, args.limit, args.threshold)
    result["mode"] = args.mode
    result["threshold"] = args.threshold
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"mode={args.mode} threshold={args.threshold}")
        print(f"positive_hit_rate={result['positive_hit_rate']:.1%}")
        print(f"negative_rejection_rate={result['negative_rejection_rate']:.1%}")
        print(f"false_positive_rate={result['false_positive_rate']:.1%}")
        print(f"mrr={result['mrr']:.3f}")
        print(f"avg_latency_ms={result['avg_latency_ms']:.3f}")

if __name__ == "__main__":
    main()
