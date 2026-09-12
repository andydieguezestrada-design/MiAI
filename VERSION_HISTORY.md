# MiAI Version History

## V1 → V0.11.1
The repository preserves the available project evolution and tests through the current stable baseline. Historical code is not fabricated where an original snapshot is unavailable.

## V0.11.1 — Current stable baseline
- Fixed FTS5 stale-row accumulation during document re-ingestion.
- Preserved lexical, semantic, and hybrid RAG paths.
- Added/retained regression coverage for RAG quality, isolation, fallback, and cleanup.
- CI/API validation and C++ Release build pass.

## V0.12 — Development / benchmark track
### B1 — RAG Quality
Benchmark artifacts live under `benchmarks/rag_quality_v12/`.

### B2 — Semantic + Hybrid RAG
Benchmark artifacts live under `benchmarks/rag_quality_v12/b2/` and include B2 reports/results.

B2 is evaluation-only and does not constitute a V0.12 stable release. Its semantic embedding fixture is deterministic/test-only.

## Next
B3 will validate a real embedding provider/model before any runtime promotion into the stable branch.


## V0.12-B4 — Real Embeddings
- Added OpenAI-compatible real embedding provider with batch response validation.
- Added persistent reindexing for missing chunk vectors.
- Increased semantic candidate pool to 5000 chunks/project.
- Added API reindex endpoint and B4 regression tests.
- Kept deterministic CI independent of external embedding services.
- Status: Release Candidate; real-provider benchmark still required.
