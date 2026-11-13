"""The harmonized target schema: what every survey is mapped to.

The schema is declared in ``config/harmonized_schema.yaml`` and validated here.
Validation is strict on purpose: the schema is the contract for the LLM mapping
step, the transformation step and the quality controls, so an inconsistency in
it (a category without codes, a derived variable that depends on nothing) must
fail when the file is loaded, not three phases later.
"""

from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

Block = Literal["identification", "demographics", "education", "labor", "income", "housing"]
Level = Literal["person", "household"]
VariableType = Literal["string", "integer", "float", "category"]

# How a variable gets its values:
#   constant - taken from the survey configuration (country, year)
#   mapped   - built from source variables; this is what the LLM proposes
#   derived  - computed from other harmonized variables, identically for every survey
Origin = Literal["constant", "mapped", "derived"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Reference(_StrictModel):
    name: str
    url: str
    consulted: date
    used_for: str


class ValueRange(_StrictModel):
    min: float | None = None
    max: float | None = None
    exclusive_min: bool = False

    @model_validator(mode="after")
    def _check_bounds(self) -> "ValueRange":
        if self.min is None and self.max is None:
            raise ValueError("a range needs at least one of min, max")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError(f"min ({self.min}) is greater than max ({self.max})")
        return self


class HarmonizedVariable(_StrictModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    block: Block
    level: Level
    type: VariableType
    origin: Origin
    definition: str = Field(min_length=10)
    unit: str | None = None
    allowed_values: dict[int, str] | None = None  # category variables: code -> label
    range: ValueRange | None = None  # numeric variables
    universe: str | None = None  # who the variable applies to; None means everyone
    nullable: bool
    missing: str = Field(min_length=1)  # what a null means, or "Not allowed."
    derived_from: list[str] = []
    idb_equivalent: str | None = None  # name(s) in the IDB harmonized databank

    @model_validator(mode="after")
    def _check_consistency(self) -> "HarmonizedVariable":
        if self.type == "category":
            if not self.allowed_values or len(self.allowed_values) < 2:
                raise ValueError(f"{self.name}: a category needs at least two allowed_values")
            if self.range is not None:
                raise ValueError(f"{self.name}: a category cannot have a range")
        elif self.allowed_values is not None:
            raise ValueError(f"{self.name}: allowed_values is only valid for type 'category'")

        if self.type == "string" and self.range is not None:
            raise ValueError(f"{self.name}: a string cannot have a range")

        if self.origin == "derived" and not self.derived_from:
            raise ValueError(f"{self.name}: a derived variable must list derived_from")
        if self.origin != "derived" and self.derived_from:
            raise ValueError(f"{self.name}: derived_from is only valid for origin 'derived'")

        # A variable restricted to a universe is necessarily null outside it.
        if self.universe is not None and not self.nullable:
            raise ValueError(f"{self.name}: a variable with a universe must be nullable")
        return self


class Conventions(_StrictModel):
    missing_values: str
    household_membership: str
    income: str
    not_applied: str


class HarmonizedSchema(_StrictModel):
    schema_version: str
    description: str
    references: list[Reference]
    conventions: Conventions
    variables: list[HarmonizedVariable]

    @model_validator(mode="after")
    def _check_variables(self) -> "HarmonizedSchema":
        names = [variable.name for variable in self.variables]
        duplicated = sorted({name for name in names if names.count(name) > 1})
        if duplicated:
            raise ValueError(f"duplicated variable names: {duplicated}")

        known = set(names)
        for variable in self.variables:
            unknown = [name for name in variable.derived_from if name not in known]
            if unknown:
                raise ValueError(f"{variable.name}: derived_from unknown variables {unknown}")
        return self

    def get(self, name: str) -> HarmonizedVariable:
        for variable in self.variables:
            if variable.name == name:
                return variable
        raise KeyError(f"{name!r} is not a variable of the harmonized schema")

    def by_origin(self, origin: Origin) -> list[HarmonizedVariable]:
        return [variable for variable in self.variables if variable.origin == origin]

    def by_level(self, level: Level) -> list[HarmonizedVariable]:
        return [variable for variable in self.variables if variable.level == level]


def load_schema(path: Path) -> HarmonizedSchema:
    """Load and validate the harmonized schema YAML."""
    with Path(path).open(encoding="utf-8") as handle:
        return HarmonizedSchema.model_validate(yaml.safe_load(handle))


# --- Human-readable documentation ---------------------------------------------

_BLOCK_TITLES = {
    "identification": "Identification and sampling design",
    "demographics": "Demographics",
    "education": "Education",
    "labor": "Labor",
    "income": "Income",
    "housing": "Housing and basic services",
}


def render_markdown(schema: HarmonizedSchema) -> str:
    """Render the schema as a Markdown reference document."""
    lines = [
        "# Harmonized schema",
        "",
        "Generated from `config/harmonized_schema.yaml` by `lacharm schema`. Do not edit by hand.",
        "",
        f"Version {schema.schema_version}. {schema.description}",
        "",
        f"{len(schema.variables)} variables: "
        f"{len(schema.by_level('person'))} at person level, "
        f"{len(schema.by_level('household'))} at household level. "
        f"{len(schema.by_origin('mapped'))} are mapped from source variables, "
        f"{len(schema.by_origin('derived'))} are derived from other harmonized variables "
        f"and {len(schema.by_origin('constant'))} are constants of the survey.",
        "",
        "## Conventions",
        "",
        f"- **Missing values.** {schema.conventions.missing_values}",
        f"- **Household membership.** {schema.conventions.household_membership}",
        f"- **Income.** {schema.conventions.income}",
        f"- **Not applied.** {schema.conventions.not_applied}",
        "",
    ]
    for block, title in _BLOCK_TITLES.items():
        lines += [
            f"## {title}",
            "",
            "| Variable | Level | Type | Values or range | Origin | Nullable | IDB |",
            "|---|---|---|---|---|---|---|",
        ]
        variables = [variable for variable in schema.variables if variable.block == block]
        lines += [_table_row(variable) for variable in variables]
        lines.append("")
        for variable in variables:
            lines.append(f"- **`{variable.name}`**: {variable.definition}{_details(variable)}")
        lines.append("")

    lines += ["## References", ""]
    for reference in schema.references:
        lines.append(
            f"- [{reference.name}]({reference.url}), consulted "
            f"{reference.consulted.isoformat()}. {reference.used_for}"
        )
    return "\n".join(lines) + "\n"


def _table_row(variable: HarmonizedVariable) -> str:
    return (
        f"| `{variable.name}` | {variable.level} | {variable.type} | {_values(variable)} "
        f"| {variable.origin} | {'yes' if variable.nullable else 'no'} "
        f"| {variable.idb_equivalent or '-'} |"
    )


def _values(variable: HarmonizedVariable) -> str:
    if variable.allowed_values:
        return "; ".join(f"{code} = {label}" for code, label in variable.allowed_values.items())
    if variable.range is None:
        return "-"
    lower = "" if variable.range.min is None else f"{variable.range.min:g}"
    upper = "" if variable.range.max is None else f"{variable.range.max:g}"
    if variable.range.exclusive_min:
        return f"> {lower}" if not upper else f"> {lower} to {upper}"
    return f">= {lower}" if not upper else f"{lower} to {upper}"


def _details(variable: HarmonizedVariable) -> str:
    parts = []
    if variable.unit:
        parts.append(f"Unit: {variable.unit}.")
    if variable.universe:
        parts.append(f"Universe: {variable.universe}")
    if variable.nullable:
        parts.append(f"Missing: {variable.missing}")
    if variable.derived_from:
        names = ", ".join(f"`{name}`" for name in variable.derived_from)
        parts.append(f"Derived from {names}.")
    return (" " + " ".join(parts)) if parts else ""
