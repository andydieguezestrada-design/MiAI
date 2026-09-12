# V0.12-B2 Report

## Scope

Evaluation-only benchmark against the frozen V0.11.1 RAG implementation. Semantic retrieval uses a deterministic topic embedding fixture; it is not a production embedding model.

Candidate corpus: **366 chunks** (360 distractors + 6 gold documents).

## Results

| Mode | Hit@1 | Hit@3 | MRR | False-positive rate | No-context accuracy | Avg latency (ms) |
|---|---:|---:|---:|---:|---:|---:|
| lexical | 86.7% | 100.0% | 0.933 | 62.5% | 37.5% | 5.24 |
| semantic | 100.0% | 100.0% | 1.000 | 0.0% | 100.0% | 2.87 |
| hybrid | 100.0% | 100.0% | 1.000 | 62.5% | 37.5% | 6.89 |

## Decision

**Do not merge a V0.12 retrieval change yet.** B2 validates the evaluation harness and separates semantic retrieval from lexical retrieval. The semantic fixture is intentionally idealized; the next meaningful gate is a real embedding provider plus reranking and a quality gate.

## Interpretation

- Lexical remains the recall-oriented baseline.
- Pure semantic retrieval shows the expected benefit on vocabulary changes, but the result is fixture-dependent.
- Hybrid is the production-shaped path, but its 0.55/0.45 weighting and 0.08 gate should be tuned only with real embeddings.
- The 366-chunk corpus exercises the >300 candidate-pool behavior present in the current implementation.
