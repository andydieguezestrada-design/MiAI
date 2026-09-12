# Arquitectura MiAI V1 + V2 Integrado

V1 es la base única del proyecto. V2 aporta capacidades adicionales dentro
de esa misma estructura.

## Capas

1. API Gateway
2. AI Engine
3. Memory
4. Reasoning
5. Model Providers
6. RAG (base V1)
7. Tools (base V1)
8. SDK
9. C++ Core

## Proveedores

`ollama` y `openai_compatible` son proveedores reales. `mock` existe para
pruebas automatizadas sin depender de servicios externos.

## Regla de CI

GitHub Actions debe validar código, contratos y compilación. No debe requerir
descargar o ejecutar un LLM real para una prueba unitaria.

## V0.6 Advanced RAG

`AIEngine` consulta el `Retriever` por proyecto antes de construir el prompt. `RAGStore` persiste documentos y chunks en SQLite. SQLite FTS5 se usa como primera recuperación cuando está disponible; un scoring léxico posterior prioriza coincidencia de términos, frases y título. La respuesta del modelo recibe el contexto recuperado, pero el almacenamiento y la recuperación ocurren fuera del modelo.


## V0.7 Vision

`VisionEngine` reutiliza memoria y RAG por proyecto y delega la comprensión visual a un `VisionProvider`. La capa de proveedor permite cambiar entre visión local (Ollama), APIs OpenAI-compatible y mock de CI sin cambiar la API pública de MiAI.

Flujo: `cliente -> /ai/vision -> VisionEngine -> contexto memoria/RAG -> VisionProvider -> respuesta -> memoria`.
