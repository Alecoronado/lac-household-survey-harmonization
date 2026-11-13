# CLAUDE.md — Brief del proyecto

## 1. Contexto y rol

Soy Alessandro Coronado, data scientist. Estoy postulando a una consultoría de Data Scientist en el Grupo de Pobreza del BID (Washington DC). El puesto consiste en construir una infraestructura de análisis de encuestas de hogares de América Latina con inteligencia artificial. Sus líneas de trabajo son:

- Armonización de encuestas de hogares con modelos de lenguaje (LLM).
- Infraestructura de datos en la nube (AWS y Databricks).
- Automatización de controles de calidad.
- Medición de pobreza y desigualdad.
- Mapas de pobreza con machine learning y estimación en áreas pequeñas.

Quiero un proyecto de portafolio real, público en GitHub, que demuestre esas competencias con datos reales de la PNAD Contínua (IBGE, Brasil). Empezamos con Brasil, pero la arquitectura debe permitir sumar otros países de América Latina y el Caribe solo agregando configuración (un YAML por encuesta), sin reescribir el código.

Tu rol: actúa como data scientist senior y tutor a la vez. Además de construir el proyecto, quiero aprender y poder defenderlo en una entrevista técnica. Por eso:

- Antes de cada fase, explícame en español y en pocas líneas qué vamos a hacer y por qué.
- Al terminar cada fase, resume las decisiones clave y hazme 3 preguntas de repaso como las que haría un entrevistador del BID.
- Si hay una decisión de diseño con alternativas razonables, preséntamelas y pregúntame antes de seguir.
- El código, los comentarios, los commits y el README van en inglés. La guía de estudio (`docs/study_guide_es.md`) va en español.

## 2. Reglas no negociables

- **Solo datos reales.** No inventes datos para el análisis. La única excepción son fixtures mínimos escritos a mano (unas pocas líneas) para probar el parser en los tests unitarios.
- **Nunca subas microdatos a GitHub.** `data/` va en `.gitignore`. El repo contiene código, configuración, metadatos derivados (catálogo de variables), mapeos y resultados agregados. Agrega en el README una sección "Data access" que explique cómo descargar los datos del IBGE.
- **No inventes nombres de variables, códigos ni valores.** Todo sale del diccionario y del archivo `input` oficiales del IBGE. Si algo no está claro, detente y pregúntame.
- **No confíes en tu memoria para cifras oficiales.** Las líneas de pobreza, los factores PPP, la población oficial y las tasas publicadas se verifican en la fuente: Banco Mundial (PIP), IBGE o SIDRA. Cita la fuente y la fecha de consulta en `docs/sources.md`.
- **El LLM propone y el humano aprueba.** Ningún mapeo generado por el LLM se aplica a los datos sin mi revisión explícita.
- **Reproducibilidad.** Un solo comando debe reconstruir todo desde los archivos crudos (`make all` o equivalente). Versiones fijadas, seeds fijas y temperatura 0 en el LLM.
- **Costo cero o casi cero.** Cachea cada llamada al LLM. Usa las capas gratuitas cuando toque la nube (fase opcional).
- **Commits pequeños y descriptivos**, una rama por fase y un Pull Request por fase hacia `main`.

## 3. Datos de entrada

Ya los descargué del FTP público del IBGE. Están en `data/raw/brasil/` (si no están, pídemelos):

- `PNADC_<año>_visita1.zip`: microdatos de ancho fijo de la PNAD Contínua anual, visita 1. Es la que trae el módulo completo de ingresos de todas las fuentes, la que se usa para medir pobreza.
- `input_PNADC_<año>_visita1_*.txt`: programa de lectura en formato SAS con posiciones, anchos y nombres de las variables.
- `dicionario_PNADC_<año>_visita1_*.xls`: diccionario con descripciones y categorías.
- `deflator_PNADC_<año>.xls`: deflactores, de `.../Anual/Microdados/Visita/Documentacao_Geral/`.

Origen: `https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Anual/Microdados/Visita/`

Los nombres exactos de archivo pueden variar. Detecta lo que hay en la carpeta y confírmamelo antes de seguir.

Pistas para verificar en el diccionario, no para asumir: se suelen usar `UPA` (unidad primaria de muestreo), `Estrato`, un peso de visita con calibración (por ejemplo `V1032`), `V2007` (sexo), `V2009` (edad), `V2005` (condición en el hogar), variables derivadas de educación (`VD3004`/`VD3005`), de trabajo (`VD4001`/`VD4002`) y de ingreso del hogar (`VD5007`/`VD5008`). El hogar se identifica con `UPA + V1008 + V1014`. Confirma cada una en el diccionario del año que usemos.

## 4. Stack técnico

- Python 3.11+ con `uv` (o `venv` + `pip-tools`) y `pyproject.toml`.
- `polars` o `pyarrow` para leer el ancho fijo por bloques y escribir Parquet. `pandas` solo donde haga falta.
- `pydantic` para los esquemas y para la salida estructurada del LLM. `pandera` para validar los DataFrames.
- `pyyaml` para la configuración.
- SDK de Anthropic y de OpenAI, con el proveedor elegido por la variable de entorno `LLM_PROVIDER`. Las claves van en `.env`, que no se sube.
- `samplics` (o una implementación propia validada) para estimaciones con diseño muestral complejo: errores estándar por linealización de Taylor con estratos y UPA.
- `pytest`, `ruff`, `pre-commit`, GitHub Actions (CI solo con tests y lint, sin datos).
- `duckdb` es opcional para consultas SQL sobre Parquet.
- Fase opcional de nube: PySpark en Databricks Free Edition / Community Edition y Parquet en AWS S3 (capa gratuita).

## 5. Estructura esperada del repo

```
lac-household-survey-harmonization/
├── README.md                    # inglés: problema, arquitectura, resultados, limitaciones
├── CLAUDE.md                    # este prompt
├── pyproject.toml / Makefile
├── config/
│   ├── harmonized_schema.yaml   # esquema común LAC (target)
│   └── surveys/
│       └── bra_pnadc_visita1.yaml   # config por encuesta/año
├── src/lacharm/
│   ├── ingest/        # lector SAS input + ancho fijo -> Parquet
│   ├── metadata/      # diccionario IBGE -> catálogo de variables
│   ├── mapping/       # recuperación de candidatos + LLM + revisión humana
│   ├── transform/     # aplicar mapeos aprobados, variables derivadas, deflactar
│   ├── quality/       # controles de calidad automáticos + reporte
│   ├── indicators/    # pobreza (FGT), Gini, con diseño muestral
│   └── cli.py
├── mappings/
│   ├── proposed/      # salida cruda del LLM
│   ├── approved/      # mapeos revisados por mí (los que se aplican)
│   └── gold/          # mapeo manual de referencia para evaluar al LLM
├── reports/           # reportes de QC y de indicadores (agregados)
├── docs/
│   ├── study_guide_es.md
│   ├── sources.md
│   └── architecture.md (con diagrama)
├── tests/
└── data/              # en .gitignore: raw/, interim/, harmonized/
```

## 6. Plan de trabajo por fases

Trabaja una fase a la vez. Al final de cada una: tests en verde, commit, resumen para mí, preguntas de repaso y esperar mi OK.

### Fase 0 — Setup

- Inicializa el repo, `pyproject`, `ruff`, `pytest`, `pre-commit`, `.gitignore` (incluye `data/`, `.env`, `*.zip`), `Makefile` y una CI básica en GitHub Actions.
- Crea `docs/study_guide_es.md` con una sección por fase, que irás llenando.
- Criterio de aceptación: `make test` y `make lint` corren en local y en la CI.

### Fase 1 — Ingesta (crudo → Parquet)

- Escribe un parser del `input` SAS del IBGE (líneas tipo `@posición NOMBRE $ancho.` con comentario) que devuelva una tabla de especificación de columnas: nombre, inicio, ancho, tipo y descripción. Pruébalo con fixtures mínimos escritos a mano.
- Lee el `.txt` de ancho fijo dentro del .zip y por bloques (el archivo es grande) y escribe Parquet en `data/interim/bra/pnadc_visita1/<año>/`, con tipos correctos y compresión `zstd`.
- Validaciones de ingesta:
  - El número de filas coincide con el del archivo.
  - Ninguna línea tiene un ancho distinto al esperado.
  - La suma del peso de personas es comparable con la población residente que publica el IBGE para ese año. Busca la cifra oficial, cítala y reporta la diferencia en %.
- Criterio de aceptación: el Parquet se genera de forma reproducible, las validaciones quedan en un log y existe un test del parser.

### Fase 2 — Catálogo de metadatos

- Convierte el diccionario `.xls` en un catálogo estructurado (`variable`, `label`, `categories` {código: etiqueta}, `module`, `universe`, `year`) en Parquet y JSON.
- El catálogo es la entrada del LLM. Debe ser limpio y estar en portugués original, sin traducir.
- Criterio de aceptación: el catálogo cubre el 100% de las variables del `input`; las discrepancias entre `input` y diccionario se reportan.

### Fase 3 — Esquema armonizado (target)

- Diseña `config/harmonized_schema.yaml` inspirado en las encuestas armonizadas del BID (SCL Data / "Encuestas de Hogares Armonizadas de América Latina y el Caribe") y en SEDLAC (CEDLAS–Banco Mundial). Antes, investiga cómo definen sus variables y cita esas fuentes.
- Unas 30 a 40 variables a nivel persona y hogar, en estos bloques:
  - Identificación y diseño: país, año, id de hogar, id de persona, factor de expansión, estrato, UPA, área urbana/rural, región.
  - Demografía: sexo, edad, parentesco con el jefe, tamaño del hogar.
  - Educación: asistencia, años de educación, nivel alcanzado, alfabetismo.
  - Trabajo: condición de actividad, ocupado/desocupado, categoría ocupacional, formalidad (si la encuesta lo permite), horas.
  - Ingresos: ingreso laboral, no laboral, del hogar y per cápita del hogar.
  - Vivienda y servicios básicos, si están en la visita 1.
- Cada variable lleva: definición, tipo, unidad, valores permitidos o rango, nivel (persona/hogar) y cómo se trata el missing.
- Criterio de aceptación: el esquema se valida con pydantic y yo lo apruebo antes de seguir.

### Fase 4 — Mapeo con LLM (núcleo del proyecto)

- Recuperación de candidatos: para cada variable del esquema, recupera las 10 a 15 variables más parecidas del catálogo (BM25 o embeddings sobre etiqueta + categorías). Así se ahorran tokens y se reducen las alucinaciones.
- Prompt al LLM: definición de la variable objetivo y candidatos con sus etiquetas y categorías. Pide salida JSON estructurada validada con pydantic, con estos campos:
  - `target_var`, `source_vars`
  - `transformation`: `direct` | `recode` | `derive` | `not_available`
  - `recode_map`: código fuente → código armonizado
  - `derivation`: expresión, si aplica
  - `confidence`: 0 a 1
  - `rationale`: breve, en inglés
  - `caveats`
- Robustez:
  - Temperatura 0.
  - Reintentos con validación.
  - Caché en disco por hash de (prompt + modelo + versión del prompt).
  - Registro de tokens y costo por corrida.
  - El prompt va versionado (`prompt_version`).
- Revisión humana: las propuestas se guardan en `mappings/proposed/`. Crea un comando `review` (CLI simple) que me muestre cada propuesta y me deje aprobar, editar o rechazar. El resultado va a `mappings/approved/`. Las propuestas con `confidence` < 0,8 se marcan para revisión obligatoria.
- Criterio de aceptación: se generan propuestas para todo el esquema, existe el flujo de revisión y la segunda corrida no hace llamadas nuevas gracias al caché.

### Fase 5 — Evaluación del LLM

- Te ayudo a construir a mano `mappings/gold/` para unas 30 variables, leyendo el diccionario. Así aprendo la encuesta.
- Mide la exactitud del LLM contra el gold: acierto de variable fuente (top-1), acierto del tipo de transformación y acierto del recode. Compara al menos dos configuraciones: proveedor A vs B, o prompt v1 vs v2, o con vs sin recuperación de candidatos.
- Escribe una tabla de resultados para el README con costo y tiempo por configuración.
- Criterio de aceptación: el script de evaluación es reproducible y la tabla queda en `reports/llm_evaluation.md`.

### Fase 6 — Transformación (Parquet armonizado)

- Aplica solo los mapeos aprobados y genera las variables derivadas: tamaño del hogar, ingreso per cápita del hogar (cuida qué miembros entran, por ejemplo pensionistas y empleados domésticos, según la definición del IBGE) e ingresos deflactados a precios de un período de referencia con el archivo de deflactores.
- Salida: `data/harmonized/bra/<año>/persons.parquet` y `households.parquet`, validados con pandera contra el esquema.
- Criterio de aceptación: el 100% de las filas pasa la validación del esquema, o las excepciones quedan documentadas.

### Fase 7 — Controles de calidad automáticos

- Las reglas se declaran en YAML para que sean reutilizables entre países:
  - Rangos y valores permitidos.
  - Tasas de missing por variable.
  - Unicidad de llaves.
  - Exactamente un jefe por hogar.
  - Coherencia edad–educación y edad–trabajo.
  - Ingresos negativos o atípicos.
  - Suma de pesos vs población oficial.
  - Comparación de tasas clave (por ejemplo la desocupación) contra el SIDRA del IBGE, con tolerancia.
- Clasifica cada regla como `error` (detiene el pipeline) o `warning`.
- Genera un reporte legible (`reports/qc_<país>_<año>.md` o HTML) con tablas y gráficos simples.
- Criterio de aceptación: el reporte se genera con un comando y la CI corre las reglas sobre fixtures.

### Fase 8 — Indicadores de pobreza y desigualdad

- Pobreza: usa las líneas internacionales vigentes del Banco Mundial (verifícalas en PIP; desde 2025 están en PPP 2021) y su conversión a reales con el factor PPP de consumo privado y el IPC que corresponda. Documenta cada paso.
- Calcula FGT(0), FGT(1) y FGT(2) y el Gini del ingreso per cápita del hogar, a nivel nacional, por región y por área urbana/rural.
- Errores estándar e intervalos de confianza con el diseño muestral (estrato + UPA + pesos), no solo estimaciones puntuales. Explícame la diferencia.
- Validación externa: compara con lo que publican el Banco Mundial (PIP) y el IBGE (Síntese de Indicadores Sociais). Explica las diferencias: definición de ingreso, imputaciones, línea usada, año de PPP.
- Criterio de aceptación: existe `reports/poverty_bra_<año>.md` con tablas, intervalos de confianza y la comparación externa.

### Fase 9 (opcional, muy valorada por el BID) — Nube

- Versiona la ingesta y la transformación en PySpark para Databricks Free Edition / Community Edition, leyendo y escribiendo Parquet (o Delta) y, si es posible, desde un bucket S3 de capa gratuita.
- Documenta en `docs/cloud.md` cómo se escalaría a los 26 países prestatarios del BID y a varios años.
- Criterio de aceptación: un notebook o job reproducible y una explicación honesta de qué corrió y qué es solo diseño.

### Fase 10 — Presentación del portafolio

- README en inglés: problema, diagrama de arquitectura, cómo correrlo, resultados principales (tabla de evaluación del LLM, indicadores con intervalos de confianza, resumen de QC), limitaciones, próximos pasos (sumar Bolivia y Perú; mapa de pobreza con estimación en áreas pequeñas, que será el Proyecto 2) y licencia.
- La guía de estudio en español debe quedar completa, con un glosario: FGT, Gini, diseño muestral complejo, Taylor, PPP, deflactor, armonización, ancho fijo, Parquet.
- Prepárame un resumen de 5 minutos para contar el proyecto en la entrevista y una lista de 10 preguntas técnicas probables con respuestas.

## 7. Forma de trabajar conmigo

- Empieza mostrando el plan de la Fase 0 y espera mi OK.
- Cuando algo dependa de mí (descargas, API keys, aprobar el esquema, revisar mapeos, construir el gold), dímelo de forma explícita y detente.
- Si encuentras un problema en los datos (variables que cambiaron entre años, categorías raras, pesos inconsistentes), regístralo en `docs/data_issues.md`. Esto también es material de entrevista.
- No avances de fase con tests en rojo.
- Prefiere soluciones simples y legibles a soluciones ingeniosas. Este repo lo va a leer un equipo técnico del BID.

## 8. Notas del entorno local

- Windows 11. `uv` y GNU Make se instalaron con winget; si un shell no los encuentra, hay que reabrirlo para que tome el PATH nuevo.
- El paquete se llama `lacharm` y se ejecuta con `uv run lacharm`.
