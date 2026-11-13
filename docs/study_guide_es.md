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

**Qué se hizo.** Se convirtió el archivo de ancho fijo de la PNAD Contínua
2024 (visita 1) en Parquet con tipos, y se validó el resultado.

**Conceptos.**

- **Ancho fijo.** El archivo no tiene separadores ni encabezado: cada línea
  mide 3.699 caracteres y cada variable ocupa siempre las mismas posiciones.
  Sin el layout, el archivo es ilegible.
- **`input` SAS.** Es el programa de lectura que publica el IBGE. Cada línea
  `@0094 V2007 $1. /* Sexo */` dice: la variable `V2007` empieza en la columna
  94, mide 1 carácter y es de texto (`$`). Sin `$` es numérica.
- **Parquet.** Formato columnar, comprimido y con tipos. Leer 3 columnas de
  484 no obliga a leer las otras 481. El zip de 169 MB (1,41 GB sin comprimir)
  quedó en 151 MB de Parquet con `zstd`.

**Decisiones clave.**

- **El layout sale del `input` oficial, no del código.** El parser lo
  convierte en una lista de columnas (nombre, inicio, ancho, tipo,
  descripción). Otro país con otro layout solo necesita su propio archivo.
- **Lectura por bloques desde el zip.** Se leen 25.000 líneas a la vez
  directamente del `.zip`, sin extraer los 1,41 GB a disco. La memoria usada
  depende del tamaño del bloque, no del archivo.
- **Códigos como texto.** `UF = "01"` conserva el cero inicial y coincide con
  el diccionario. Convertirlo a entero rompería esa correspondencia, que es
  justo lo que el LLM necesita en la Fase 4.
- **Enteros vs decimales se detectan en los datos.** El `input` declara los
  pesos como `15.`, igual que un entero, pero los datos traen punto decimal.
  El tipo se decide con el primer bloque y los siguientes se convierten en
  modo estricto: si aparece un decimal en una columna entera, el proceso
  falla en vez de truncar en silencio.
- **Un campo en blanco es `null`.** En la PNAD el blanco significa "no
  aplica" (por ejemplo, ingreso laboral de un niño). No es cero.
- **Los 200 pesos replicados se conservan** en el mismo Parquet. Ocupan el
  81% de cada línea, pero al ser columnar no cuestan nada si no se leen.
- **Configuración en YAML validada con pydantic.** Rutas, codificación y
  nombre del peso viven en `config/surveys/bra_pnadc_visita1.yaml`. Una clave
  mal escrita produce un error, no se ignora.

**Validaciones y resultado (2024).**

| Validación | Resultado |
|---|---|
| Filas leídas vs filas que implica el tamaño del archivo | 381.815 = 381.815 |
| Filas en el Parquet vs filas leídas | 381.815 = 381.815 |
| Líneas con ancho distinto de 3.699 | 0 |
| Suma de `V1032` vs población oficial | 211.852.978 vs 211.853.000 |

**Lo que hay que saber explicar sobre la suma de pesos.** La diferencia es de
22 personas porque el IBGE publica en miles. Coincide casi exacto por dos
razones: `V1032` está calibrado para que sume la proyección de población, y la
tabla 6407 de SIDRA se calcula con esta misma encuesta. Por eso la validación
prueba que leímos bien las filas y los pesos, pero no es una comparación
contra una fuente independiente. No dice nada sobre la calidad de la encuesta.

**Peso con y sin calibración.** El `input` describe `V1031` como "Peso SEM
calibração" y `V1032` como "Peso COM calibração". Calibrar es ajustar los
pesos para que los totales estimados coincidan con totales conocidos, aquí
las proyecciones de población (`V1030`, `V1034`). Para estimar se usa
`V1032`. El detalle exacto de cómo construye el IBGE cada peso está pendiente
de verificar en su documentación metodológica.

**Preguntas de repaso.**

1. La suma de `V1032` coincide con la población oficial con una diferencia de
   22 personas. ¿Qué demuestra eso y qué no demuestra?
2. ¿Por qué las variables de código se guardan como texto y no como enteros?
   ¿Qué se rompería más adelante si `UF` fuera `1` en vez de `"01"`?
3. El archivo pesa 1,41 GB sin comprimir. ¿Cómo lo procesas sin cargarlo
   entero en memoria, y qué cambiaría si fueran 26 países y 10 años?

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
