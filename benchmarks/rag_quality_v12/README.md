# MiAI V0.12 — RAG Quality Benchmark B1

Este benchmark **no modifica V0.11.1**. La versión estable se conserva como baseline.

## Dataset B1

- 6 documentos
- 15 consultas positivas
- 8 consultas negativas
- exact match, paráfrasis, vocabulario diferente, consultas ambiguas e irrelevantes

## Métricas

- Positive hit rate
- Negative rejection rate
- False positive rate
- MRR
- Latencia media

## Modos

Baseline:

```bash
python benchmarks/rag_quality_v12/run.py --mode baseline
```

Prototipo V0.12 lexical:

```bash
python benchmarks/rag_quality_v12/run.py --mode v12-lexical
```

El prototipo aplica stopwords + solapamiento ponderado por IDF + bonos controlados de frase/título.

**Importante:** este prototipo es experimental. No sustituye todavía el retrieval híbrido semántico de V0.12.

## Criterio provisional de release

No se aprueba V0.12 por una sola métrica. Como objetivo inicial:

- Positive hit rate >= 95%
- Negative rejection rate >= 95%
- MRR >= 0.90
- sin regresión de aislamiento por proyecto
