# V0.12-B2 — Semantic + Hybrid RAG

Benchmark-only evaluation. V0.11.1 remains frozen as the stable baseline.

- **Lexical:** V0.11.1 without embeddings.
- **Semantic:** deterministic 6-topic embedding fixture, pure cosine ranking.
- **Hybrid:** V0.11.1 production hybrid scorer (0.55 semantic + 0.45 lexical).

The semantic fixture is **not** a production embedding model. It isolates retrieval behavior before connecting a real provider.

The benchmark inserts 360 distractors plus 6 gold documents (366 chunks) to exercise a >300 candidate pool.
