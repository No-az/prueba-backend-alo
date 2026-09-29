# ADR 0003 · El historial de evaluaciones es de solo inserción

**Estado:** aceptada

## Contexto

Una decisión de crédito tiene que poder explicarse tiempo después: ante un reclamo, una auditoría o un cambio de política. Si reevaluar sobrescribiera la decisión anterior, se perdería esa trazabilidad.

## Decisión

- Hay dos tablas: `applications` guarda los datos de la solicitud y su decisión vigente, y `evaluations` guarda cada evaluación con la versión de política, la cuota, la proporción y los motivos.
- `applications.status` repite la decisión de la última evaluación a propósito (desnormalización), para que filtrar el listado sea una consulta simple con índice. Se actualiza en la misma transacción que inserta la evaluación.
- La aplicación nunca hace `UPDATE` ni `DELETE` sobre `evaluations`. La migración `0003` agrega triggers para que la base tampoco lo permita.

## Consecuencias

- `GET /applications/{id}/evaluations` muestra la historia completa de una decisión.
- Se guarda más información (una fila por evaluación), algo irrelevante frente al valor de auditoría.
- Corregir un error de datos exige una evaluación nueva, no editar la anterior. Es intencional.
