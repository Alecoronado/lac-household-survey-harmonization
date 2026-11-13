# LAC Household Survey Harmonization

[![CI](https://github.com/Alecoronado/lac-household-survey-harmonization/actions/workflows/ci.yml/badge.svg)](https://github.com/Alecoronado/lac-household-survey-harmonization/actions/workflows/ci.yml)

LLM-assisted harmonization of Latin American household surveys, with automated
quality controls and design-based poverty and inequality indicators.

> **Status: work in progress.** Phase 0 (project setup) is complete. Results,
> the architecture diagram and limitations are added as each phase lands.

## Problem

Every country in Latin America and the Caribbean runs its own household survey,
with its own variable names, codes and questionnaire. Comparing poverty across
countries requires *harmonizing* them into a common schema, which is slow,
manual and error-prone work. This project tests how far a large language model
can speed that up when it is used as a proposer whose output a human reviews,
and when its accuracy is measured against a hand-built reference mapping.

The first survey is Brazil's **PNAD Contínua** (IBGE), annual file, visit 1.
Adding a country should only require a new YAML file under `config/surveys/`.

## Pipeline

| Step | Module | Output |
|---|---|---|
| Ingest fixed-width microdata | `lacharm.ingest` | Parquet |
| Build a variable catalog from the official dictionary | `lacharm.metadata` | Catalog (Parquet + JSON) |
| Propose mappings with an LLM, reviewed by a human | `lacharm.mapping` | `mappings/approved/` |
| Apply approved mappings, derive and deflate variables | `lacharm.transform` | Harmonized Parquet |
| Run declarative quality controls | `lacharm.quality` | QC report |
| Estimate poverty (FGT) and Gini with the survey design | `lacharm.indicators` | Indicator report |

## Quick start

Requires [uv](https://docs.astral.sh/uv/) and GNU Make.

```bash
make install   # create the environment from uv.lock and install git hooks
make test      # run the unit tests
make lint      # run ruff (lint + format check)
```

## Data access

**This repository contains no microdata.** The `data/` folder is git-ignored.
Download the files yourself from IBGE's public FTP server:

<https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Anual/Microdados/Visita/>

Place them in `data/raw/brasil/`:

| File | Location on the FTP server | Content |
|---|---|---|
| `PNADC_<year>_visita1.zip` | `Visita_1/Dados/` | Fixed-width microdata |
| `input_PNADC_<year>_visita1_*.txt` | `Visita_1/Documentacao/` | SAS input program (column positions) |
| `dicionario_PNADC_<year>_visita1_*.xls` | `Visita_1/Documentacao/` | Variable dictionary |
| `deflator_PNADC_<year>.xls` | `Documentacao_Geral/` | Deflators |

Exact file names vary by year and release date.

## Repository layout

```
config/      harmonized target schema and one YAML per survey
src/lacharm/ pipeline code (ingest, metadata, mapping, transform, quality, indicators)
mappings/    proposed (raw LLM output), approved (human-reviewed), gold (manual reference)
reports/     aggregate QC and indicator reports
docs/        study guide (Spanish), sources, data issues, architecture
tests/       unit tests on small hand-written fixtures
```

## License

Code is released under the [MIT License](LICENSE). PNAD Contínua microdata
belong to IBGE and are not redistributed here.
