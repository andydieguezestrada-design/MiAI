# Integración V1 + V2

Esta versión conserva MiAI V1 como proyecto principal y absorbe dentro de
él las capacidades de MiAI V2.

No se deben crear dos repositorios para V1 y V2. El repositorio de GitHub
debe contener un único MiAI.

El proveedor `mock` se añadió exclusivamente para que GitHub Actions no
dependa de Ollama. Ollama y OpenAI-compatible siguen siendo proveedores
disponibles para ejecución real.


## Evolución 0.3

Las capacidades de V1 y V2 permanecen dentro del mismo proyecto MiAI.
La nueva capa añade memoria persistente SQLite, perfiles de proyecto y recuperación
local inicial. La interfaz pública de `AIEngine` se conserva para no romper los
proyectos consumidores.
