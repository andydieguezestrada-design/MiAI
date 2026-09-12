# MiAI V0.12-B3 — Reranking + Quality Gate

## Resultado
- Corpus: 366 chunks (6 gold + 360 distractores)
- Consultas: 23 (15 positivas + 8 negativas)
- Hit@1: **100%**
- Hit@3: **100%**
- MRR: **1.000**
- False-positive rate: **0%**
- No-context accuracy: **100%**
- Latencia media: **~3.8–4.2 ms** en este benchmark local

Se probaron quality gates 0.20, 0.30 y 0.40, manteniendo las métricas anteriores en este dataset.

## Decisión
B3 es prometedor, pero **no se integra todavía en V0.11.1 y V0.12 no se declara estable**.

El motivo es que el embedding usado es un fixture determinista por tópicos, no un modelo semántico de producción. El siguiente paso es validar con un embedding real y consultas más difíciles.

## Método
Reranking semantic-first sobre candidatos híbridos, combinando similitud semántica, cobertura léxica, coincidencia de términos del título y frase exacta, seguido de quality gate.
