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
| 5 | 2026-11-13 | PNADC visita 1, 2024 | The dictionary stores category codes inconsistently: text (`"01"`) and numbers (`10.0`), sometimes within one variable (`V2005`). | Cell types of the code column: 563 number cells, 527 text cells. | Codes are normalized to the variable's width. Verified against the data: 0 undocumented values across the 190 purely categorical variables. |
| 6 | 2026-11-13 | PNADC visita 1, 2024 | The code column of the dictionary also holds ranges (`01 a 14`) and units (`valor em reais`), not only codes. | Parsing the dictionary. | Stored in `value_note`, separate from `categories`. Three variables (`V2008`, `V20081`, `V20082`) combine a range with the special code for "Não informado". |
| 7 | 2026-11-13 | PNADC visita 1, 2024 | In 13 variables a blank means "Não ou não aplicável" (no, or not applicable), not just "not applicable". | Categories without a code in the dictionary. | Wording kept in `remark`. Must be considered when recoding these variables: a blank is not always missing. |
| 8 | 2026-11-13 | PNADC visita 1, 2024 | `Capital`, `RM_RIDE` and `S01020` have blank values (293,354, 263,689 and 106,740 rows) that the dictionary does not explain with a "Não aplicável" category. | Cross-check of dictionary codes against the Parquet data. | Open. For `Capital` and `RM_RIDE` a blank plausibly means the household is outside a capital or metropolitan region, but the dictionary does not say so; to be confirmed before these variables are used. |
| 9 | 2026-11-13 | PNADC visita 1, 2024 | `Estrato` has no description in the dictionary; only a remark about its first two positions. | Dictionary vs input cross-check. | The catalog carries the SAS input description (`sas_label`) alongside the dictionary label. |
| 10 | 2026-11-13 | PNADC visita 1, 2024 | The dictionary has no universe column. The universe is stated only in two module headings (age 5+ for education, age 14+ for work). | Inspecting the dictionary. | `universe` is filled only from those headings (151 of 484 variables). Inferring universes from the data is left to the QC phase. |
