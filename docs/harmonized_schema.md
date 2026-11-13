# Harmonized schema

Generated from `config/harmonized_schema.yaml` by `lacharm schema`. Do not edit by hand.

Version 1.0. Person- and household-level variables for poverty, inequality and labor market analysis, comparable across countries and years.

38 variables: 26 at person level, 12 at household level. 30 are mapped from source variables, 6 are derived from other harmonized variables and 2 are constants of the survey.

## Conventions

- **Missing values.** Missing is always null. Sentinel codes such as 9 or 99 are never used. For variables with a universe, null means the person or household is outside it.
- **Household membership.** Lodgers, live-in domestic employees and relatives of domestic employees are not household members: they are assumed not to share the household budget. They are excluded from household size and from household income. This follows SEDLAC. The IDB databank is stricter and excludes every non-relative.
- **Income.** Incomes are monthly, in local currency. Where a survey reports both usual and actual labor income, usual income is used. A null individual income counts as zero when household income is added up.
- **Not applied.** Two adjustments made by SEDLAC are deliberately not applied: imputed rent of owner-occupied housing is not added to income, and rural incomes are not increased by 15%.

## Identification and sampling design

| Variable | Level | Type | Values or range | Origin | Nullable | IDB |
|---|---|---|---|---|---|---|
| `country` | person | string | - | constant | no | pais_c |
| `year` | person | integer | 1980 to 2100 | constant | no | anio_c |
| `household_id` | person | string | - | mapped | no | idh_ch |
| `person_id` | person | string | - | mapped | no | idp_ci |
| `weight` | person | float | > 0 | mapped | no | factor_ci |
| `strata` | person | string | - | mapped | no | - |
| `psu` | person | string | - | mapped | no | - |
| `urban` | household | category | 1 = Urban; 0 = Rural | mapped | no | zona_c |
| `region` | household | string | - | mapped | no | region_c |

- **`country`**: Country of the survey, ISO 3166-1 alpha-3 code.
- **`year`**: Reference year of the survey.
- **`household_id`**: Identifier of the household, unique within a country and year. Built from the survey's own household key.
- **`person_id`**: Identifier of the person, unique within a country and year. Built from the household key plus the person's order number in the household.
- **`weight`**: Expansion factor of the person: the number of people in the population the respondent represents. The calibrated weight recommended by the publisher for annual estimates.
- **`strata`**: Sampling stratum, as defined by the survey design.
- **`psu`**: Primary sampling unit, as defined by the survey design.
- **`urban`**: Whether the dwelling is in an urban area, using the country's own official definition of urban.
- **`region`**: First-level administrative division where the dwelling is located (state, department or province), as the official code used by the country.

## Demographics

| Variable | Level | Type | Values or range | Origin | Nullable | IDB |
|---|---|---|---|---|---|---|
| `sex` | person | category | 1 = Male; 2 = Female | mapped | no | sexo_ci |
| `age` | person | integer | 0 to 130 | mapped | no | edad_ci |
| `relationship` | person | category | 1 = Head; 2 = Spouse or partner; 3 = Child (including stepchild); 4 = Other relative; 5 = Other non-relative (including lodgers); 6 = Domestic employee or relative of a domestic employee | mapped | no | relacion_ci |
| `household_member` | person | category | 1 = Member; 0 = Not a member | mapped | no | miembros_ci |
| `ethnicity` | person | category | 1 = Indigenous; 2 = Afro-descendant; 3 = Other | mapped | yes | afroind_ci |
| `household_size` | household | integer | 1 to 60 | derived | no | nmiembros_ch |

- **`sex`**: Sex of the person.
- **`age`**: Age in completed years at the survey reference date. Unit: years.
- **`relationship`**: Relationship to the head of the household.
- **`household_member`**: Whether the person counts as a household member for household size and per capita income. Lodgers, live-in domestic employees and relatives of domestic employees do not.
- **`ethnicity`**: Self-reported race or ethnicity, grouped into the three categories used by the IDB. Missing: Null when not reported or not asked.
- **`household_size`**: Number of household members (persons with household_member = 1). Unit: persons. Derived from `household_member`.

## Education

| Variable | Level | Type | Values or range | Origin | Nullable | IDB |
|---|---|---|---|---|---|---|
| `literate` | person | category | 1 = Yes; 0 = No | mapped | yes | - |
| `attends_school` | person | category | 1 = Yes; 0 = No | mapped | yes | asiste_ci |
| `years_education` | person | integer | 0 to 25 | mapped | yes | aedu_ci |
| `education_level` | person | category | 1 = No education; 2 = Primary incomplete; 3 = Primary complete; 4 = Secondary incomplete; 5 = Secondary complete; 6 = Tertiary incomplete; 7 = Tertiary complete | mapped | yes | eduno_ci, edupi_ci, edupc_ci, edusi_ci, edusc_ci, eduui_ci, eduuc_ci |

- **`literate`**: Whether the person can read and write. Universe: Persons at or above the age from which the survey asks about education. Missing: Null outside the universe.
- **`attends_school`**: Whether the person currently attends school at any level. Universe: Persons at or above the age from which the survey asks about education. Missing: Null outside the universe.
- **`years_education`**: Completed years of formal education. Unit: years. Universe: Persons at or above the age from which the survey asks about education. Missing: Null outside the universe or when the level cannot be determined.
- **`education_level`**: Highest level of formal education attained. Primary, secondary and tertiary follow the country's own system; the mapping of national levels to these categories is documented per survey. Universe: Persons at or above the age from which the survey asks about education. Missing: Null outside the universe or when the level cannot be determined.

## Labor

| Variable | Level | Type | Values or range | Origin | Nullable | IDB |
|---|---|---|---|---|---|---|
| `labor_status` | person | category | 1 = Employed; 2 = Unemployed; 3 = Out of the labor force | mapped | yes | condocup_ci |
| `employed` | person | category | 1 = Yes; 0 = No | derived | yes | emp_ci |
| `unemployed` | person | category | 1 = Yes; 0 = No | derived | yes | desemp_ci |
| `employment_type` | person | category | 1 = Employer; 2 = Self-employed; 3 = Employee; 4 = Unpaid family worker | mapped | yes | categopri_ci |
| `formal` | person | category | 1 = Formal; 0 = Informal | mapped | yes | formal_ci |
| `hours_main` | person | integer | 0 to 168 | mapped | yes | horaspri_ci |
| `hours_total` | person | integer | 0 to 168 | mapped | yes | horastot_ci |

- **`labor_status`**: Labor force status in the reference week, using the country's official definitions of employment and unemployment. Universe: Persons of working age, as defined by the survey. Missing: Null below working age.
- **`employed`**: Whether the person is employed (labor_status = 1). Universe: Persons of working age, as defined by the survey. Missing: Null below working age. Derived from `labor_status`.
- **`unemployed`**: Whether the person is unemployed (labor_status = 2). Universe: Persons of working age, as defined by the survey. Missing: Null below working age. Derived from `labor_status`.
- **`employment_type`**: Type of employment relationship in the main job. Universe: Employed persons. Missing: Null when not employed.
- **`formal`**: Whether the worker contributes to a social security or pension system through any job (the legal definition of formality). Universe: Employed persons. Missing: Null when not employed.
- **`hours_main`**: Hours usually worked per week in the main job. Unit: hours per week. Universe: Employed persons. Missing: Null when not employed.
- **`hours_total`**: Hours usually worked per week in all jobs. Unit: hours per week. Universe: Employed persons. Missing: Null when not employed.

## Income

| Variable | Level | Type | Values or range | Origin | Nullable | IDB |
|---|---|---|---|---|---|---|
| `labor_income_main` | person | float | >= 0 | mapped | yes | ylmpri_ci |
| `labor_income` | person | float | >= 0 | mapped | yes | ylm_ci |
| `nonlabor_income` | person | float | >= 0 | mapped | yes | ynlm_ci |
| `household_income` | household | float | >= 0 | derived | no | - |
| `household_income_pc` | household | float | >= 0 | derived | no | - |
| `household_income_pc_real` | household | float | >= 0 | derived | no | - |

- **`labor_income_main`**: Usual monthly income from the main job. Unit: local currency per month, current prices. Universe: Employed persons with remuneration in the main job. Missing: Null outside the universe.
- **`labor_income`**: Usual monthly income from all jobs. Unit: local currency per month, current prices. Universe: Employed persons with remuneration in any job. Missing: Null outside the universe. Counted as zero in household income.
- **`nonlabor_income`**: Monthly income from all sources other than work: pensions, public and private transfers, capital income and other sources. Unit: local currency per month, current prices. Universe: Persons who received income from a non-labor source. Missing: Null outside the universe. Counted as zero in household income.
- **`household_income`**: Total monthly household income: labor income plus non-labor income, added over household members only. Unit: local currency per month, current prices. Derived from `labor_income`, `nonlabor_income`, `household_member`.
- **`household_income_pc`**: Household per capita income, household_income divided by household_size. Unit: local currency per person per month, current prices. Derived from `household_income`, `household_size`.
- **`household_income_pc_real`**: Household per capita income at the prices of the survey's reference period, using the publisher's deflators. Unit: local currency per person per month, reference-period prices. Derived from `household_income_pc`.

## Housing and basic services

| Variable | Level | Type | Values or range | Origin | Nullable | IDB |
|---|---|---|---|---|---|---|
| `dwelling_tenure` | household | category | 1 = Owned (paid off or being paid); 2 = Rented; 3 = Other (ceded, occupied or other arrangement) | mapped | yes | viviprop_ch |
| `bedrooms` | household | integer | 0 to 50 | mapped | yes | dorm_ch |
| `piped_water` | household | category | 1 = Yes; 0 = No | mapped | yes | aguared_ch |
| `electricity` | household | category | 1 = Yes; 0 = No | mapped | yes | luz_ch |
| `toilet` | household | category | 1 = Yes; 0 = No | mapped | yes | bano_ch |
| `internet` | household | category | 1 = Yes; 0 = No | mapped | yes | internet_ch |

- **`dwelling_tenure`**: Tenure status of the dwelling. Missing: Null when not reported.
- **`bedrooms`**: Number of rooms permanently used for sleeping. Unit: rooms. Missing: Null when not reported.
- **`piped_water`**: Whether the dwelling is supplied by a piped water network. Missing: Null when not reported.
- **`electricity`**: Whether the dwelling has electricity, from the grid or another source. Missing: Null when not reported.
- **`toilet`**: Whether the household has a bathroom or toilet facility. Missing: Null when not reported.
- **`internet`**: Whether any resident has access to the internet at home. Missing: Null when not reported.

## References

- [IDB Harmonized Household Surveys of Latin America and the Caribbean (SCL Data)](https://github.com/EL-BID/armonizacion_microdatos_encuestas_hogares_scl), consulted 2026-11-13. Variable list, category codes and the idb_equivalent crosswalk (_DOCS/Labels&ExternalVars_Harmonized_DataBank.do).
- [SEDLAC Methodological Guide (CEDLAS and The World Bank), October 2025](https://www.cedlas.econo.unlp.edu.ar/wp/wp-content/uploads/Guia_SEDLAC.pdf), consulted 2026-11-13. Definition of household membership, household per capita income and labor informality.
