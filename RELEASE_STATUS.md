# MiAI Release Status

## Current stable
**V0.11.1** — stable baseline.

Validated items include the RAG FTS5 re-ingestion fix, RAG isolation/quality regressions, semantic fallback behavior, delete cleanup, Python compilation, C++ Release build, and GitHub Actions CI/API validation.

## V0.12 development
V0.12 is currently a quality/retrieval development track, not a stable release.

- **B1 — RAG Quality:** lexical baseline benchmark.
- **B2 — Semantic + Hybrid RAG:** evaluation benchmark over a corpus larger than 300 chunks.
- B2's semantic embedding is deterministic/test-only and must not be represented as a production embedding provider.
- Next validation target: B3 with a real embedding model/provider, followed by reranking and a quality gate if results justify integration.

## Master package policy
This package combines the authoritative V1→V0.11.1 runtime baseline with V0.12 benchmark artifacts. Benchmark artifacts are preserved for reproducibility and do not by themselves change the stable runtime version.


## V0.12-B4
Release Candidate. Real embeddings are integrated behind environment configuration. Stable promotion is blocked only on real-provider retrieval quality validation.
