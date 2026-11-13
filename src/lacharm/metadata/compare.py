"""Cross-checks between the three descriptions of a survey file.

A survey file is described twice by its publisher (the SAS input program and the
dictionary) and once by itself (the values actually present in the data). The three
should agree. Where they do not, the difference is reported, never silently fixed.
"""

from dataclasses import dataclass, field

import polars as pl

from lacharm.ingest.sas_input import ColumnSpec
from lacharm.metadata.catalog import CatalogEntry


@dataclass(frozen=True)
class LayoutComparison:
    """Dictionary vs SAS input program."""

    n_input: int  # variables in the input program
    only_in_input: list[str]
    only_in_dictionary: list[str]
    position_mismatches: list[str]  # human-readable, one per variable
    without_label: list[str]

    @property
    def coverage_pct(self) -> float:
        """Share of the input program's variables that the dictionary documents."""
        return 100 * (self.n_input - len(self.only_in_input)) / self.n_input


def compare_with_input(entries: list[CatalogEntry], specs: list[ColumnSpec]) -> LayoutComparison:
    catalog = {entry.variable: entry for entry in entries}
    layout = {spec.name: spec for spec in specs}

    mismatches = []
    for name in sorted(catalog.keys() & layout.keys()):
        entry, spec = catalog[name], layout[name]
        if (entry.start, entry.width) != (spec.start, spec.width):
            mismatches.append(
                f"{name}: dictionary says start {entry.start}, width {entry.width}; "
                f"input says start {spec.start}, width {spec.width}"
            )

    return LayoutComparison(
        n_input=len(specs),
        only_in_input=[spec.name for spec in specs if spec.name not in catalog],
        only_in_dictionary=[entry.variable for entry in entries if entry.variable not in layout],
        position_mismatches=mismatches,
        without_label=[entry.variable for entry in entries if not entry.label],
    )


@dataclass(frozen=True)
class CodeComparison:
    """Dictionary categories vs values observed in the data, for one variable."""

    variable: str
    undocumented: dict[str, int] = field(default_factory=dict)  # code in data -> rows
    unused: list[str] = field(default_factory=list)  # documented, never observed
    null_rows: int = 0
    has_not_applicable: bool = False
    # The dictionary gives a range or unit next to the codes (e.g. day of birth:
    # "01 a 31" plus the special code 99). Values outside the codes are then expected.
    value_note: str | None = None

    @property
    def blank_not_documented(self) -> bool:
        """Blank values exist but the dictionary lists no "not applicable" category."""
        return self.null_rows > 0 and not self.has_not_applicable


def compare_with_data(entries: list[CatalogEntry], data: pl.LazyFrame) -> list[CodeComparison]:
    """Compare documented codes with observed values, for every variable with categories.

    Only aggregates leave this function: codes and row counts, never records.
    """
    schema = data.collect_schema()
    coded = [entry for entry in entries if entry.categories and entry.variable in schema]
    frame = data.select([entry.variable for entry in coded]).collect()

    results = []
    for entry in coded:
        column = frame[entry.variable]
        counts = column.drop_nulls().value_counts()
        observed = dict(zip(counts[entry.variable], counts["count"], strict=True))

        if schema[entry.variable] == pl.String:
            documented = set(entry.categories)
        else:  # numeric column: "01" and 1 are the same code
            documented = {int(code) for code in entry.categories}

        undocumented = {str(code): n for code, n in observed.items() if code not in documented}
        unused = sorted(str(code) for code in documented - observed.keys())
        results.append(
            CodeComparison(
                variable=entry.variable,
                undocumented=dict(sorted(undocumented.items())),
                unused=unused,
                null_rows=column.null_count(),
                has_not_applicable=entry.has_not_applicable,
                value_note=entry.value_note,
            )
        )
    return results
