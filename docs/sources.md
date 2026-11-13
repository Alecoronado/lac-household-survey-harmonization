# Sources

Every official figure used in this project (poverty lines, PPP factors,
official population, published rates) is verified at its source and recorded
here. Nothing is taken from memory.

| Figure | Value | Source | URL | Date consulted | Used in |
|---|---|---|---|---|---|
| Resident population, Brazil, 2024 | 211,853 thousand | IBGE, SIDRA table 6407 "População residente, por sexo e grupos de idade" (PNAD Contínua anual, accumulated first visits), variable 606, total | <https://sidra.ibge.gov.br/tabela/6407> (API: <https://apisidra.ibge.gov.br/values/t/6407/n1/all/v/606/p/2024/c2/6794/c58/95253>) | 2026-11-13 | Ingest validation: sum of `V1032` |

## Data files

| File | Publisher | URL | Date downloaded |
|---|---|---|---|
| `PNADC_2024_visita1_20251119.zip` | IBGE | <https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Anual/Microdados/Visita/Visita_1/Dados/> | 2026-11-13 |
| `input_PNADC_2024_visita1_20251119.txt` | IBGE | <https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Anual/Microdados/Visita/Visita_1/Documentacao/> | 2026-11-13 |
| `dicionario_PNADC_microdados_2024_visita1_20251119.xls` | IBGE | same folder as the input file | 2026-11-13 |
| `deflator_PNADC_2024.xls` | IBGE | <https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Anual/Microdados/Visita/Documentacao_Geral/> | 2026-11-13 |

SHA-256 of the microdata archive as downloaded: `e6f631a6ecf55f16a486f12f56409be50ca522488ea52dd2b6446de3f63c8b52`
