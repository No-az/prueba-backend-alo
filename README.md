# Prueba Técnica — Backend

**Tiempo estimado:** 1 hora
**Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest, Docker

---

## Contexto

Construye un servicio HTTP que evalúe solicitudes de crédito. Una solicitud incluye:

| Campo               | Tipo  | Descripción                                       |
|---------------------|-------|---------------------------------------------------|
| `amount`            | int   | Monto solicitado en COP                           |
| `monthly_income`    | int   | Ingresos mensuales en COP                         |
| `employment_months` | int   | Antigüedad laboral en meses                       |
| `external_score`    | int   | Score externo (0–1000)                            |
| `product`           | str   | Tipo de producto: `PHONE`, `TWIST` o `CARD`       |

## Reglas de evaluación

Existen tres políticas que se aplican según el tipo de producto:

| Producto | Política     | Regla                                                                 |
|----------|--------------|-----------------------------------------------------------------------|
| PHONE    | Conservadora | `score ≥ 700` AND `employment_months ≥ 12` AND `cuota ≤ 25% ingreso` |
| TWIST    | Estándar     | `score ≥ 600` AND `cuota ≤ 35% ingreso`                              |
| CARD     | Agresiva     | `score ≥ 550` OR (`score ≥ 500` AND `monthly_income ≥ 3,000,000`)    |

> Asume plazo fijo de 12 meses: `cuota = amount / 12`

Cada solicitud debe persistirse con su decisión (`APPROVED` o `REJECTED`) y las razones del rechazo cuando aplique.

## Endpoints requeridos

1. **`POST /applications`** — recibe la solicitud, la evalúa y la persiste. Retorna la decisión.
2. **`GET /applications/{id}`** — retorna una solicitud por ID.
3. **`GET /applications?status=APPROVED&product=TWIST`** — lista con filtros opcionales.

## Restricciones de diseño

- La selección de política según producto **no** debe ser un `if/elif` dentro del endpoint.
- El acceso a la base de datos **no** debe estar acoplado al endpoint.
- Cubre con tests al menos: una aprobación, un rechazo por cada política, y el flujo end-to-end del endpoint.

## Bonus (solo si te sobra tiempo)

`POST /applications/{id}/reevaluate` que vuelva a correr la evaluación con la política actual (útil si cambian umbrales).

---

## Setup

**Requisitos:** Docker Desktop instalado. Nada más.

### Levantar el servicio

```bash
docker compose up --build
```

- API: http://localhost:8000
- Docs interactivos: http://localhost:8000/docs

### Correr los tests

```bash
docker compose run --rm app pytest -v
```

### Estructura sugerida (puedes modificarla si lo justificas)

```
app/
├── main.py              # FastAPI app + routers
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic schemas
├── database.py          # engine + session
├── repositories/        # acceso a datos
├── services/            # orquestación
└── strategies/          # políticas de evaluación
tests/
```

## Entrega

Push a tu repo personal (público, o privado con acceso compartido) y envía el link.

¡Éxitos!
