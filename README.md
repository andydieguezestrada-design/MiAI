# MiAI V1 — V2 Integrado

MiAI V1 es el proyecto principal. Las capacidades desarrolladas en V2 han sido
absorbidas dentro de esta misma base; no existe un segundo proyecto independiente.

## Integrado desde V2

- Motor `AIEngine`.
- Proveedores intercambiables:
  - `ollama` para modelos locales.
  - `openai_compatible` para servidores remotos compatibles.
  - `mock` únicamente para pruebas CI.
- Memoria por proyecto.
- Pipeline de contexto/reasoning.
- API REST `/ai/chat`.
- SDK Python.
- Núcleo C++ preparado para operaciones de alto rendimiento.
- GitHub Actions sin dependencia de Ollama para las pruebas.

## Arquitectura

```text
Proyecto futuro (ARTattoo, etc.)
          |
          v
      MiAI API / SDK
          |
          v
      AI Engine
      /        \
   Memory    Reasoning
          |
     Model Provider
    /      |       \
 Ollama  Remote    Mock(CI)
          |
       Modelo LLM
```

RAG y Tools de V1 se conservan dentro del proyecto para su expansión posterior.

## Ejecutar localmente con Ollama

1. Instala dependencias:
   `python -m pip install -r requirements.txt`
2. Instala/inicia Ollama y descarga un modelo:
   `ollama pull llama3.2:3b`
3. Ejecuta:
   `uvicorn api.main:app --host 0.0.0.0 --port 8000`

Variables:
- `MIAI_PROVIDER=ollama`
- `MIAI_MODEL=llama3.2:3b`
- `MIAI_OLLAMA_URL=http://localhost:11434`

Para un servidor compatible con OpenAI:
- `MIAI_PROVIDER=openai_compatible`
- `MIAI_MODEL=<modelo>`
- `MIAI_BASE_URL=<endpoint>`
- `MIAI_API_KEY=<clave>`

## Admin API (control del propietario / app Android MiAI Admin)

Además de `/ai/*`, el Core expone `/admin/*` para el control del propietario:
estado, métricas, política de costo, cambio de proveedor/modelo, logs de
auditoría/sistema y ciclo de vida de releases firmadas. Todo bajo `/admin/*`
exige la cabecera `X-Owner-Token`.

**Primer paso, obligatorio antes de vincular la app:**

```bash
python scripts/generate_owner_token.py --url https://tu-core.ejemplo.com
```

Esto imprime el JSON de pairing (`{"url", "token", "pin"}`) que se pega en la
pantalla "Vincular MiAI Admin" de la app Android. El token solo se guarda
hasheado — si lo pierdes, vuelve a correr el script con `--rotate`.

Detalles de diseño (por qué "aplicar" un release no reemplaza el proceso en
caliente, cómo se calcula `tool_metrics_7d`, etc.) en `python/admin/`.

Nunca guardes claves dentro del repositorio.

## GitHub Actions

Las pruebas usan `MIAI_PROVIDER=mock`, por lo que no intentan conectarse a
`localhost:11434`. Esto evita el error `Connection refused` visto cuando CI
intentaba ejecutar Ollama sin tener Ollama instalado.

El uso real de Ollama sigue disponible fuera de CI.


## MiAI 0.3 — memoria persistente

La V1 sigue siendo la base única del proyecto y las capacidades de V2 continúan integradas.
Esta evolución añade:

- Memoria persistente por proyecto con SQLite.
- Perfiles persistentes por proyecto.
- Recuperación local por palabras clave como primera capa de RAG.
- Endpoints para guardar, consultar y limpiar memoria.
- Prompt estructurado con memoria, perfil y contexto recuperado.
- CI aislada con memoria `:memory:` y proveedor `mock`, sin depender de Ollama.

La memoria se guarda por defecto en `data/miai_memory.sqlite3` cuando se ejecuta localmente.

## MiAI V0.4 — Tool/Plugin Engine

MiAI V0.4 añade una capa estable de herramientas/plugins sin separar V1 y V2.

Incluye:
- `ToolSpec`: contrato de cada herramienta.
- `ToolRegistry`: registro central de herramientas.
- `ToolExecutor`: frontera segura de ejecución y manejo de errores.
- Herramientas integradas: `calculator`, `datetime`, `system_info`.
- `/ai/tools`: catálogo de herramientas disponibles.
- `/ai/tools/execute`: ejecución explícita mediante API.
- El `ReasoningPipeline` recibe los esquemas de herramientas para que los modelos puedan conocer sus capacidades.
- La ejecución ocurre fuera del modelo; MiAI no debe inventar resultados.

Esto deja preparada la arquitectura para futuros plugins de web, archivos, visión, RAG, bases de datos, GitHub y ARTattoo.


## MiAI V0.5 — Autonomous Agent

MiAI incorpora un agente autónomo acotado con ciclo PLAN/ACT/OBSERVE/REFLECT/FINAL.

- `POST /ai/agent` ejecuta tareas multi-paso.
- El agente solo puede utilizar herramientas registradas en `ToolRegistry`.
- Cada ejecución tiene un límite de pasos configurable (1–12).
- Los resultados de herramientas se devuelven al agente como observaciones.
- Si una herramienta falla, el error vuelve al agente para que pueda corregir la estrategia.
- CI utiliza proveedores mock/fake para no depender de Ollama.

El agente no ejecuta código arbitrario y no expone cadenas de pensamiento privadas.

## MiAI V0.6 — Advanced RAG

MiAI V0.6 añade una capa de conocimiento persistente por proyecto. Los documentos se dividen en fragmentos y se almacenan en SQLite; cuando está disponible se usa SQLite FTS5 para recuperación inicial y después un reranking léxico por coincidencia de términos, frases y título.

Incluye:
- `RAGStore` persistente y aislado por proyecto.
- Chunking con solapamiento configurable.
- Recuperación FTS5 con fallback seguro a búsqueda local.
- Reranking por relevancia léxica.
- Ingesta, búsqueda, listado y eliminación de documentos mediante API.
- Integración automática del conocimiento recuperado en `/ai/chat`.
- La base queda preparada para incorporar embeddings/vector search en una siguiente evolución sin romper la API.

Endpoints:
- `POST /ai/knowledge`
- `POST /ai/knowledge/search`
- `GET /ai/knowledge/{project}`
- `DELETE /ai/knowledge/{project}/{document_id}`


## MiAI V0.7 — Vision Engine

MiAI incorpora análisis multimodal de imágenes sin acoplarse a un proyecto concreto. La imagen se envía como Base64 y el motor de visión recibe también la instrucción, perfil del proyecto, memoria relevante y conocimiento RAG disponible.

### Endpoint
- `POST /ai/vision` — analiza una imagen y devuelve una respuesta detallada.

### Parámetros principales
- `image_base64`: imagen codificada en Base64.
- `instruction`: qué debe analizar MiAI.
- `project`: aislamiento de memoria/contexto.
- `system`: instrucciones adicionales.
- `mime_type`: `image/jpeg`, `image/png`, `image/webp`, etc.
- `temperature`: control de variabilidad.

### Proveedores
- `ollama`: visión local con un modelo compatible con imágenes.
- `openai_compatible`: cualquier endpoint compatible que acepte contenido multimodal.
- `mock`: pruebas CI sin depender de una GPU ni de Internet.

La arquitectura queda preparada para que futuros proyectos solamente pasen imagen + parámetros a MiAI.

## MiAI V0.7 — Vision (Online First)

V0.7 adds multimodal image analysis while keeping MiAI hardware-agnostic.

### Recommended execution path

`Mobile development → GitHub Actions → MiAI API → online vision provider → vision model`

MiAI does not require a GPU, local model, or powerful PC to develop or use the vision layer. The OpenAI-compatible provider is the primary path; Ollama remains an optional local provider.

### Vision endpoint

`POST /ai/vision`

Accepts `image_base64`, `instruction`, `project`, optional `system`, `mime_type`, and `temperature`. Mobile clients may send raw Base64 or a `data:image/...;base64,...` value.

MiAI combines project memory and RAG context with the vision instruction. The image itself is not stored in MiAI memory; only the task and returned result are persisted.

### Configuration

```env
MIAI_VISION_PROVIDER=openai_compatible
MIAI_VISION_MODEL=<vision-model>
MIAI_VISION_BASE_URL=https://example.com/v1
MIAI_VISION_API_KEY=<secret>
```

Keep secrets in the runtime environment, never in source code or a mobile app bundle. For CI use `MIAI_VISION_PROVIDER=mock`. Ollama can be enabled explicitly when local inference is desired.

## MiAI V0.8 — Context, Sessions & Reliability
V0.8 keeps the V1/V2 project unified and strengthens the online-first brain: persistent sessions, deterministic context budgeting, response-quality validation, JSON response mode, provider retries/fallbacks and safer provider configuration. Existing V0.7 endpoints remain compatible.

### Chat improvements
`POST /ai/chat` now accepts optional `session_id` and `response_format` (`text` or `json`). JSON mode validates that the returned answer is valid JSON before accepting it.

### Sessions
- `POST /ai/sessions`
- `GET /ai/sessions/{project}`
- `GET /ai/session/{session_id}`
- `DELETE /ai/session/{session_id}`

### Reliability
Set `MIAI_RETRIES` and `MIAI_FALLBACK_PROVIDERS` to enable bounded retries/fallbacks. No provider credentials or model files belong in the repository.

## MiAI V0.9.1 — Streaming, sesiones avanzadas y memoria semántica
V0.9 evoluciona el núcleo sin separar V1/V2 en proyectos distintos. La API pública sigue siendo reutilizable por ARTattoo y futuros proyectos.

### Streaming
`POST /ai/chat/stream` entrega respuestas mediante Server-Sent Events (SSE), permitiendo que una app móvil muestre la respuesta progresivamente. Los proveedores con streaming nativo lo aprovechan; los demás usan un fallback compatible que divide la respuesta final en fragmentos.

Eventos SSE:
- `token` — fragmento de respuesta.
- `done` — respuesta completada.
- `error` — error de ejecución.

### Sesiones avanzadas
Las memorias de conversación pueden asociarse a `session_id`, manteniendo aislamiento por proyecto y sesión.

Nuevos endpoints:
- `PATCH /ai/session/{session_id}` — cambia título/resumen.
- `GET /ai/session/{session_id}/messages` — recupera mensajes de una sesión.
- `DELETE /ai/session/{session_id}/messages` — limpia únicamente los mensajes de esa sesión.

Eliminar una sesión también elimina sus memorias asociadas.

### Memoria semántica
V0.9 añade `SemanticMemoryStore`. Puede utilizar un endpoint OpenAI-compatible de embeddings para recuperar recuerdos por similitud semántica. Si el servicio de embeddings no está disponible, MiAI conserva un fallback léxico y no bloquea el chat.

Configuración:
```env
MIAI_SEMANTIC_MEMORY=true
MIAI_EMBEDDING_MODEL=text-embedding-3-small
MIAI_EMBEDDING_BASE_URL=https://example.com/v1
MIAI_EMBEDDING_API_KEY=<secret>
```

La memoria sigue siendo persistente en SQLite, aislada por proyecto y opcionalmente por sesión. No se guardan credenciales ni modelos dentro del repositorio.


## MiAI V0.9.1 — CI Hardening

V0.9.1 es una versión de mantenimiento sobre V0.9. Se mantienen streaming, sesiones avanzadas y memoria semántica, y se refuerza la validación de CI.

- Versión de API: `0.9.1`.
- El streaming incorpora recuperación de memoria semántica cuando está habilitada.
- Las respuestas completadas por streaming se persisten también en memoria semántica.
- GitHub Actions ejecuta un smoke test real de la API además de validar la importación.
- Se añade `concurrency` para cancelar ejecuciones CI obsoletas del mismo ref y evitar colas innecesarias.
- No se incluyen modelos ni bases de datos de ejecución en el repositorio.

## V0.10 — Deep reasoning and quality refinement

V0.10 is additive to the V1–V9 architecture. Existing modules and APIs are preserved. It adds a depth-aware reasoning prompt, a non-invasive response quality assessment, optional automatic refinement (`MIAI_AUTO_REFINE=true` by default), and deeper vision response refinement while keeping the original image-analysis contract.

## V0.11.1 — RAG FTS5 idempotency fix

V0.11.1 corrige la reingesta de documentos en FTS5 eliminando las filas de índice antiguas antes de reemplazar los chunks. Añade regresiones para idempotencia y contenido obsoleto, sin cambiar el scoring híbrido de V0.11.

## V0.11 — RAG Quality Gate + hybrid semantic retrieval

V0.11 is additive to V1–V10. It keeps the existing RAG API and lexical retrieval path while adding a relevance gate and optional semantic embeddings for hybrid ranking.

- Weak/irrelevant retrieval is rejected before it reaches the model context.
- Existing lexical scoring remains available when embeddings are not configured.
- When an OpenAI-compatible embedding provider is configured, RAG combines lexical and semantic relevance.
- Semantic retrieval can recover conceptually related chunks even when the query uses different words.
- Exact phrase matches are preserved as high-confidence matches.
- Embedding failures never make document ingestion or retrieval fail; MiAI falls back to the existing lexical path.
- New threshold: `MIAI_RAG_MIN_SCORE` (default `0.08`).
- The same embedding configuration used by semantic memory can be reused by RAG.
- No V1–V10 module or public endpoint is removed.

## Master package: V1 → V0.12
This GitHub-ready master package combines the authoritative stable runtime baseline through V0.11.1 with preserved V0.12-B1/B2 RAG quality benchmark artifacts under `benchmarks/rag_quality_v12/`. V0.12 remains development/benchmark status until real embedding validation and subsequent quality gates are completed.


## V0.12-B4 — Real embeddings

B4 adds a production-oriented OpenAI-compatible embeddings adapter while keeping CI deterministic. Configure `MIAI_EMBEDDING_BASE_URL`, `MIAI_EMBEDDING_API_KEY` and `MIAI_EMBEDDING_MODEL` in the runtime environment. Reindex missing vectors with `POST /ai/knowledge/{project}/reindex`. Do not commit credentials.

B4 is a Release Candidate, not yet the stable release: validate retrieval quality against a real embedding model before promoting V0.12.
