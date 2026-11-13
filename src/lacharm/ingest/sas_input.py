"""Parser for the SAS INPUT programs that statistical offices ship with fixed-width microdata.

A fixed-width file has no delimiters: every variable lives at a fixed position in
each line. The positions are only documented in a SAS program whose relevant lines
look like this (IBGE, PNAD Continua):

    @0094 V2007   $1.   /* Sexo */
    @0103 V2009   3.   /* Idade na data de referência */

Meaning: variable ``V2007`` starts at column 94 (1-based), is 1 character wide and is
a character variable (``$``); ``V2009`` starts at column 103, is 3 wide and numeric.
"""

import re
from dataclasses import dataclass
from pathlib import Path

# @<start> <name> <optional $><width>.<optional decimals> /* <optional description> */
_COLUMN_LINE = re.compile(
    r"""
    ^\s*@(?P<start>\d+)          # 1-based start position
    \s+(?P<name>\w+)             # variable name
    \s+(?P<char>\$?)             # "$" marks a character variable
    \s*(?P<width>\d+)\.          # field width
    (?P<decimals>\d*)            # implied decimals (not used by IBGE, parsed for safety)
    \s*(?:/\*\s*(?P<description>.*?)\s*\*/)?   # trailing comment
    \s*$
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class ColumnSpec:
    """Where one variable lives in a fixed-width line."""

    name: str
    start: int  # 1-based, as written in the SAS program
    width: int
    kind: str  # "string" (SAS character) or "numeric"
    description: str

    @property
    def end(self) -> int:
        """Last column occupied by the variable (1-based, inclusive)."""
        return self.start + self.width - 1


class SasInputError(ValueError):
    """The SAS input program is malformed or internally inconsistent."""


def parse_sas_input_text(text: str) -> list[ColumnSpec]:
    """Extract the column specification from the text of a SAS INPUT program.

    Lines that do not start with ``@`` (comments, ``data``/``infile`` statements)
    are ignored. A line that starts with ``@`` but cannot be parsed is an error:
    silently skipping it would shift nothing but would drop a variable.
    """
    specs: list[ColumnSpec] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.lstrip().startswith("@"):
            continue
        match = _COLUMN_LINE.match(line)
        if match is None:
            raise SasInputError(f"Line {line_number}: cannot parse column definition: {line!r}")
        if match["decimals"]:
            raise SasInputError(
                f"Line {line_number}: implied decimals ({line.strip()!r}) are not supported"
            )
        specs.append(
            ColumnSpec(
                name=match["name"],
                start=int(match["start"]),
                width=int(match["width"]),
                kind="string" if match["char"] else "numeric",
                description=match["description"] or "",
            )
        )

    if not specs:
        raise SasInputError("No column definitions (lines starting with '@') were found")
    _check_layout(specs)
    return specs


def parse_sas_input(path: Path, encoding: str) -> list[ColumnSpec]:
    """Read a SAS INPUT program from disk and parse it."""
    return parse_sas_input_text(Path(path).read_text(encoding=encoding))


def record_length(specs: list[ColumnSpec]) -> int:
    """Expected number of characters in every data line."""
    return max(spec.end for spec in specs)


def _check_layout(specs: list[ColumnSpec]) -> None:
    """Reject duplicated names and overlapping columns."""
    names = [spec.name for spec in specs]
    duplicated = sorted({name for name in names if names.count(name) > 1})
    if duplicated:
        raise SasInputError(f"Duplicated variable names: {duplicated}")

    ordered = sorted(specs, key=lambda spec: spec.start)
    for previous, current in zip(ordered, ordered[1:], strict=False):
        if current.start <= previous.end:
            raise SasInputError(
                f"Columns overlap: {previous.name} ends at {previous.end} "
                f"but {current.name} starts at {current.start}"
            )
