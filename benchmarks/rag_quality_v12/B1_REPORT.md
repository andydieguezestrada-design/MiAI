# RAG Quality B1 — diagnóstico inicial

## Baseline V0.11.1

Dataset: **23 consultas / 6 documentos**.

- Positive hit rate: **100%**
- Negative rejection rate: **37.5%**
- False positive rate: **62.5%**
- MRR: **0.933**

Conclusión: el baseline recupera muy bien los positivos de este dataset, pero acepta demasiado contexto irrelevante.

## Experimento V0.12-B1 lexical

Se probó un scorer experimental con:

1. stopword filtering en español;
2. weighting IDF por consulta;
3. coincidencia de frase controlada;
4. pequeño title bonus.

Resultado:

- Positive hit rate: **40.0%**
- Negative rejection rate: **100%**
- False positive rate: **0%**
- MRR: **0.367**

## Conclusión importante

**No fusionar este scorer lexical en V0.11.1.**

El experimento confirma el trade-off que buscábamos medir:

> reducir los falsos positivos únicamente con lexical/IDF destruye demasiado recall.

Por tanto, V0.12 debe combinar recuperación semántica real con señales léxicas, en lugar de sustituir el retrieval actual por un lexical gate más estricto.

## Siguiente experimento

V0.12-B2 debe medir:

- lexical baseline;
- semantic retrieval;
- hybrid retrieval;
- precision@1 / precision@3;
- recall@1 / recall@3;
- MRR;
- false-positive rate;
- no-context accuracy;
- score separation;
- latencia;
- candidate pool >300 chunks.

El benchmark debe conservar V0.11.1 como baseline inmutable.
