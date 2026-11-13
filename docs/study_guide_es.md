# Guía de estudio

Guía para entender y defender el proyecto en una entrevista técnica. Cada fase
tiene: qué se hizo, por qué, las decisiones clave y preguntas de repaso.

## Fase 0 — Setup

**Qué se hizo.** Se creó el esqueleto del proyecto antes de tocar datos:
entorno reproducible, lint, tests, hooks de git y CI.

**Decisiones clave.**

- **`uv` con `uv.lock`.** El `pyproject.toml` declara rangos de versiones
  (`pytest>=8.0`); el lockfile fija la versión exacta de cada paquete,
  incluidas las dependencias transitivas. La CI instala con `uv sync --locked`,
  que falla si el lockfile no coincide con el `pyproject.toml`. Así la CI y
  cualquier persona que clone el repo usan las mismas versiones.
- **Layout `src/`.** El paquete vive en `src/lacharm/` y se instala en modo
  editable. Los tests importan el paquete instalado, no la carpeta local, y
  eso detecta errores de empaquetado que de otro modo pasarían inadvertidos.
- **`Makefile` como única puerta de entrada.** `make test`, `make lint` y
  `make all` son los mismos comandos en local y en la CI. Las recetas son
  llamadas simples a `uv run`, para que funcionen igual en Windows y Linux.
- **`ruff` para lint y formato.** Una sola herramienta reemplaza a flake8,
  isort y black. `make lint` solo verifica; `make format` corrige.
- **`.gitignore` desde el primer commit.** `data/`, `*.zip`, `*.parquet` y
  `.env` quedan excluidos antes de que exista ningún dato o clave. Es más
  seguro que limpiar el historial después.
- **Dependencias mínimas.** Solo se instalan `pytest`, `ruff` y `pre-commit`.
  Cada librería (polars, pydantic, samplics) se agrega en la fase que la usa.
- **CI sin datos.** GitHub Actions corre lint y tests en Python 3.11 y 3.13.
  Los tests usan fixtures pequeños escritos a mano, nunca microdatos.

**Preguntas de repaso.**

1. ¿Qué diferencia hay entre declarar `polars>=1.0` en `pyproject.toml` y
   tener un `uv.lock`? ¿Cuál de los dos garantiza la reproducibilidad?
2. Los microdatos de la PNAD Contínua son públicos. ¿Por qué no se suben al
   repo, y cómo puede otra persona reproducir los resultados?
3. La CI no tiene acceso a los datos. ¿Qué puede verificar y qué no? ¿Cómo se
   cubre lo que la CI no ve?

## Fase 1 — Ingesta (crudo → Parquet)

_Pendiente._

## Fase 2 — Catálogo de metadatos

_Pendiente._

## Fase 3 — Esquema armonizado

_Pendiente._

## Fase 4 — Mapeo con LLM

_Pendiente._

## Fase 5 — Evaluación del LLM

_Pendiente._

## Fase 6 — Transformación

_Pendiente._

## Fase 7 — Controles de calidad

_Pendiente._

## Fase 8 — Indicadores de pobreza y desigualdad

_Pendiente._

## Fase 9 — Nube (opcional)

_Pendiente._

## Fase 10 — Presentación del portafolio

_Pendiente._

## Glosario

Se completa a medida que aparecen los conceptos: FGT, Gini, diseño muestral
complejo, linealización de Taylor, PPP, deflactor, armonización, ancho fijo,
Parquet.
