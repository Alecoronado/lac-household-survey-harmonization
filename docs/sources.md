# Sources

Every official figure used in this project (poverty lines, PPP factors,
official population, published rates) is verified at its source and recorded
here. Nothing is taken from memory.

| Figure | Value | Source | URL | Date consulted | Used in |
|---|---|---|---|---|---|
| Resident population, Brazil, 2024 | 211,853 thousand | IBGE, SIDRA table 6407 "População residente, por sexo e grupos de idade" (PNAD Contínua anual, accumulated first visits), variable 606, total | <https://sidra.ibge.gov.br/tabela/6407> (API: <https://apisidra.ibge.gov.br/values/t/6407/n1/all/v/606/p/2024/c2/6794/c58/95253>) | 2026-11-13 | Ingest validation: sum of `V1032` |

## Methodological references

| Reference | What it was used for | URL | Date consulted |
|---|---|---|---|
| IDB, Harmonized Household Surveys of Latin America and the Caribbean (SCL Data), repository `EL-BID/armonizacion_microdatos_encuestas_hogares_scl`, file `_DOCS/Labels&ExternalVars_Harmonized_DataBank.do` | List of harmonized variables, their labels and category codes; `idb_equivalent` crosswalk in the schema | <https://github.com/EL-BID/armonizacion_microdatos_encuestas_hogares_scl> | 2026-11-13 |
| IDB, same repository, `BRA/PNADC/program/BRA_2022a_variablesBID.do` | How the IDB defines household membership (`miembros_ci = relacion_ci < 5`) and builds keys for PNAD Contínua. Read for the definitions only; not used as a mapping. | <https://github.com/EL-BID/armonizacion_microdatos_encuestas_hogares_scl/tree/master/BRA/PNADC/program> | 2026-11-13 |
| CEDLAS and The World Bank, "Guía Metodológica SEDLAC", version of October 2025 | Household membership (lodgers, domestic employees and their families excluded), household per capita income, imputed rent, 15% rural adjustment, definitions of informality | <https://www.cedlas.econo.unlp.edu.ar/wp/wp-content/uploads/Guia_SEDLAC.pdf> | 2026-11-13 |

## Data files

| File | Publisher | URL | Date downloaded |
|---|---|---|---|
| `PNADC_2024_visita1_20251119.zip` | IBGE | <https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Anual/Microdados/Visita/Visita_1/Dados/> | 2026-11-13 |
| `input_PNADC_2024_visita1_20251119.txt` | IBGE | <https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Anual/Microdados/Visita/Visita_1/Documentacao/> | 2026-11-13 |
| `dicionario_PNADC_microdados_2024_visita1_20251119.xls` | IBGE | same folder as the input file | 2026-11-13 |
| `deflator_PNADC_2024.xls` | IBGE | <https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Anual/Microdados/Visita/Documentacao_Geral/> | 2026-11-13 |

SHA-256 of the microdata archive as downloaded: `e6f631a6ecf55f16a486f12f56409be50ca522488ea52dd2b6446de3f63c8b52`
