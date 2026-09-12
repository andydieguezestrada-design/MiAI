# MiIA Core — conexión con la APK

## Arquitectura

APK MiIA Admin -> HTTPS -> MiIA Core -> ProviderManager -> proveedor/modelo.

La APK no recibe ni almacena las API keys de los proveedores. El Core las recibe como variables de entorno.

## Despliegue rápido en Render

1. Sube este proyecto al repositorio `MiAI` manteniendo `render.yaml` y `Dockerfile` en la raíz.
2. En Render: New -> Blueprint y selecciona el repositorio.
3. El servicio se llamará `miai-core` y comprobará `/health`.
4. En Environment completa:
   - `MIAI_BASE_URL`
   - `MIAI_API_KEY`
   - `MIAI_MODEL`
   - `MIAI_OWNER_TOKEN`
5. Guarda y despliega.
6. Prueba `https://TU-SERVICIO.onrender.com/health`.
7. El payload para la APK debe ser:

```json
{"url":"https://TU-SERVICIO.onrender.com","token":"EL_MISMO_MIAI_OWNER_TOKEN","pin":"000000"}
```

El PIN solo forma parte del formato que espera la APK Admin. La autenticación HTTP del Core usa `X-Owner-Token`.

## Proveedores alternativos

Configura el proveedor principal y, si quieres fallback, sus variables `MIAI_*` correspondientes y `MIAI_FALLBACK_PROVIDERS` o `MIAI_PROVIDER_CHAIN`.

Nunca pongas API keys en el repositorio, en `render.yaml` ni dentro de la APK.

## Importante sobre el plan Free

El filesystem local de un servicio Free es efímero. SQLite puede perder cambios al reiniciar/hibernar/redeployar. Para una prueba sirve; para producción usa almacenamiento persistente/DB externa.
