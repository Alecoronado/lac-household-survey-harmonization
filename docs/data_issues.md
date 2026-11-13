# Data issues log

Problems found in the data while building the pipeline: variables that change
between years, unexpected categories, inconsistent weights, mismatches between
the SAS input file and the dictionary.

Each entry records what was found, how it was detected, and what was decided.

| # | Date | Survey / year | Issue | How it was detected | Decision |
|---|---|---|---|---|---|
| 1 | 2026-11-13 | PNADC visita 1, all years | IBGE publishes visit 1 microdata for 2012-2019 and 2022-2025 only. There are no visit 1 files for 2020 and 2021. | Listing of `Visita_1/Dados/` on the IBGE server. | Not yet investigated why, or whether another visit covers those years. Any time series must handle the gap explicitly. |
| 2 | 2026-11-13 | PNADC visita 1, 2024 | The SAS informat does not distinguish integers from decimals: weights are declared `15.` like any integer, but the data carry an explicit decimal point (`000158.42040029`). | Inspecting the weight fields of the first rows. | Numeric type is detected from the data in the first chunk; later chunks are cast strictly, so a decimal in an integer column raises an error. Result: 202 decimal columns (`V1031`, `V1032` and the 200 replicate weights), 63 integer columns. |
| 3 | 2026-11-13 | PNADC visita 1, 2024 | The SAS input file is encoded in ISO-8859-1 (Latin-1) with CRLF line endings, not UTF-8. | `file` on the input file; accents break when read as UTF-8. | Encoding is declared per survey in the YAML config. |
| 4 | 2026-11-13 | PNADC visita 1, 2024 | 200 of the 484 variables are replicate weights (`V1032001`-`V1032200`), 81% of each line. | SAS input file. | Kept in the same Parquet dataset; columnar storage means they cost nothing unless read. To be used or not for variance estimation in Phase 8. |
