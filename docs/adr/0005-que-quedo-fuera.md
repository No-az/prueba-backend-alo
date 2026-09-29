# ADR 0005 · Qué quedó fuera y por qué

**Estado:** aceptada

## Contexto

Se consideraron varias mejoras propias de un servicio en producción. Algunas cambiaban lo que pide el enunciado, que los evaluadores van a probar tal cual. Se aplicó una regla: **ninguna extensión puede cambiar una ruta, una respuesta, la fórmula de la cuota o la forma de levantar el proyecto**.

## Decisión: se dejan fuera

| Mejora | Por qué no | Cómo se haría sin romper nada |
|---|---|---|
| Autenticación OAuth2/JWT con roles | Las rutas del enunciado responderían 401 sin token | `POST /auth/token` con el flujo *password*, tokens cortos firmados, refresh token en cookie `HttpOnly` y dependencias `require_role(...)` |
| Versionado `/api/v1` | Cambia las rutas pedidas | Montar el router en `/api/v1` y dejar `/applications` como alias |
| Plazo y tasa reales | El enunciado fija `cuota = amount / 12` | Amortización francesa con plazo y tasa en la versión de política. Con tasa 0 y plazo 12 da exactamente `amount / 12` |
| PostgreSQL | Agrega un servicio que el enunciado no pide | Ver ADR 0004 |
| Paginación por cursor | Cambiaría la forma de la respuesta del listado | Cursor opcional devuelto en headers (`Link`, `X-Next-Cursor`), manteniendo la lista como respuesta |
| Frontend (React + Vite) | Fuera del alcance de una prueba de backend | Una SPA en `frontend/` con tipos generados desde el OpenAPI |

## Sí se agregaron, porque no cambian nada de lo pedido

Historial de evaluaciones, versionado de políticas, índices, límite de peticiones, errores RFC 7807, contenedor sin root, CI y actualización de dependencias vulnerables.

## Pendiente importante

El `external_score` llega en el request, así que un cliente podría enviar el valor que quiera. En producción el backend debe consultarlo al buró detrás de un puerto `ScoreProvider`, con un adaptador que actúe como capa anticorrupción frente al formato del proveedor.
