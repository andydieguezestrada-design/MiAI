# MiAI — Control de versiones y actualizaciones

MiAI se mantiene bajo control manual del propietario.

## Reglas

- No hay actualización automática de la aplicación.
- Cada release tiene una versión explícita.
- `python/core/version.py` es la fuente única de verdad del runtime.
- `release.json` es el contrato de release para los clientes Android.
- GitHub Actions debe validar runtime + manifest antes de aceptar una build.
- Stable/Beta pueden gestionarse mediante el campo `channel`.
- Las versiones anteriores se conservan para rollback.

## Flujo recomendado

1. Cambiar código y `VERSION` en `python/core/version.py`.
2. Actualizar `release.json` y notas de release.
3. Ejecutar tests y CI.
4. Revisar el artefacto generado.
5. El propietario decide si instala/publica la nueva versión, subiendo el
   paquete firmado desde la app MiAI Admin (o vía `POST /admin/release/upload`)
   y confirmando con `POST /admin/release/apply`.

## Cómo funciona `/admin/release/*` (implementado en `python/admin/release_manager.py`)

- **`upload`**: valida que el archivo sea un `.zip` real y que contenga un
  `release.json` con `version`. Lo deja en cuarentena (`data/releases/pending/`)
  sin tocar nada más.
- **`apply`**: archiva el paquete pendiente, actualiza la versión "actual"
  rastreada en `data/releases/state.json`, guarda la versión anterior en el
  historial (para rollback), y — si existe — ejecuta
  `scripts/apply_release.sh <ruta-del-zip>`.
- **`rollback`**: recupera la última versión del historial y la vuelve a
  marcar como actual; también dispara el hook si existe.
- **`discard`**: borra el paquete pendiente sin aplicarlo.

Importante: aplicar un release **no reemplaza el código del proceso en
caliente** — eso no puede hacerse de forma segura desde dentro del propio
proceso Python. `apply`/`rollback` sólo preparan el paquete y actualizan el
estado rastreado; `GET /admin/release/state` expone `requires_restart` para
que tanto el propietario como la app Android sepan si el proceso en
ejecución todavía no coincide con la versión "actual" registrada. El swap de
código real y el reinicio del proceso quedan a cargo de
`scripts/apply_release.sh` (o del mecanismo de despliegue que uses:
systemd, Docker, etc.) — este contrato deja ese paso desacoplado a propósito.

## Seguridad

- Las claves/API secrets no deben almacenarse en la APK, en `release.json`
  ni en el repositorio.
- El Owner Token de `/admin/*` sólo se guarda hasheado (SHA-256) en
  `data/miai_admin.sqlite3`; no hay forma de recuperarlo en texto plano,
  solo de rotarlo con `python scripts/generate_owner_token.py --rotate`.
