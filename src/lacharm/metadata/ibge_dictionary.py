"""Parser for IBGE's PNAD Continua variable dictionary (.xls).

The dictionary is a spreadsheet laid out for people, not programs:

    position | width | variable | question no. | description | code | category | period
    ---------+-------+----------+--------------+-------------+------+----------+-------
    Parte 2 - Características Gerais dos Moradores                  <- module heading
    92       | 2     | V2005    | 5            | Condição... | 01   | Pessoa.. | 1º tri..
             |       |          |              |             | 02   | Cônjuge  |
             |       |          |              |             | 10.0 | Neto(a)  |       <- number!
             |       |          |              |             |      | Não aplicável

A variable row carries the first category; the rows below it carry the rest.
Three quirks are handled here:

* Codes are stored inconsistently: some as text (``"01"``), some as numbers
  (``10.0``). They are normalized to the variable's width (``"10"``, ``"01"``) so
  they match the codes in the data, which are stored as text.
* The code column also holds things that are not codes: ranges (``"01 a 14"``) and
  units (``"valor em reais"``). Those go to ``value_note``.
* A category without a code and labelled "Não aplicável" means the field is blank
  in the data. It sets ``has_not_applicable`` instead of becoming a category.
  Any other text without a code goes to ``remark``.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import xlrd

from lacharm.metadata.catalog import CatalogEntry

# Column positions in the sheet.
_START, _WIDTH, _VARIABLE, _QUESTION, _LABEL, _CODE, _CATEGORY, _PERIOD = range(8)

Cell = str | float  # text cell (possibly empty) or number cell
Row = list[Cell]


class DictionaryError(ValueError):
    """The dictionary does not have the expected structure."""


@dataclass(frozen=True)
class DictionaryLayout:
    """Survey-specific knowledge needed to read the sheet (comes from the YAML config)."""

    header_rows: int
    module_heading_pattern: str  # headings that open a top-level module
    universe_pattern: str  # phrase inside a module heading that states its universe
    not_applicable_label: str


def read_xls_rows(path: Path, sheet_index: int = 0) -> list[Row]:
    """Read a sheet as rows of plain values: ``float`` for number cells, ``str`` otherwise."""
    workbook = xlrd.open_workbook(str(path))
    sheet = workbook.sheet_by_index(sheet_index)
    rows = []
    for index in range(sheet.nrows):
        row = []
        for cell in sheet.row(index):
            is_number = cell.ctype == xlrd.XL_CELL_NUMBER
            row.append(float(cell.value) if is_number else str(cell.value))
        rows.append(row)
    return rows


def parse_dictionary_rows(
    rows: list[Row], layout: DictionaryLayout, year: int
) -> list[CatalogEntry]:
    """Turn the sheet rows into catalog entries, in the order they appear."""
    module_heading = re.compile(layout.module_heading_pattern)
    universe_phrase = re.compile(layout.universe_pattern)

    entries: list[CatalogEntry] = []
    current: _Draft | None = None
    module: str | None = None
    submodule: str | None = None
    universe: str | None = None

    for row_number, row in enumerate(rows[layout.header_rows :], start=layout.header_rows + 1):
        cells = [_clean(cell) for cell in row]

        if _is_blank_row(cells):
            continue

        if _is_heading(cells):
            heading = cells[_START]
            if module_heading.search(heading):
                module, submodule = heading, None
                match = universe_phrase.search(heading)
                universe = match.group(0) if match else None
            else:
                submodule = heading
            continue

        if cells[_VARIABLE] != "":
            if current is not None:
                entries.append(current.build())
            current = _Draft(
                variable=cells[_VARIABLE],
                label=cells[_LABEL],
                question_number=_as_text(cells[_QUESTION]) or None,
                module=module,
                submodule=submodule,
                universe=universe,
                period=cells[_PERIOD] or None,
                year=year,
                start=_as_int(cells[_START], row_number, "start position"),
                width=_as_int(cells[_WIDTH], row_number, "width"),
                not_applicable_label=layout.not_applicable_label,
            )
        elif current is None or any(cell != "" for cell in cells[:_CODE]):
            raise DictionaryError(f"Row {row_number}: unexpected content {row!r}")

        current.add_value(cells[_CODE], cells[_CATEGORY], row_number)

    if current is not None:
        entries.append(current.build())
    if not entries:
        raise DictionaryError("No variables were found in the dictionary")
    return entries


def parse_dictionary(path: Path, layout: DictionaryLayout, year: int) -> list[CatalogEntry]:
    return parse_dictionary_rows(read_xls_rows(path), layout, year)


def normalize_code(cell: Cell, width: int) -> str | None:
    """Return the code as stored in the data, or None if the cell is not a code.

    ``10.0`` -> ``"10"``; ``1.0`` with width 2 -> ``"01"``; ``"01"`` -> ``"01"``;
    ``"01 a 14"`` -> None.
    """
    if isinstance(cell, float):
        if not cell.is_integer():
            raise DictionaryError(f"Category code {cell!r} is not an integer")
        return str(int(cell)).zfill(width)
    if cell.isascii() and cell.isdigit():
        return cell.zfill(width)
    return None


class _Draft:
    """A catalog entry being assembled from consecutive rows."""

    def __init__(self, *, not_applicable_label: str, **fields: object) -> None:
        self._fields = fields
        self._not_applicable_label = not_applicable_label
        self._categories: dict[str, str] = {}
        self._value_notes: list[str] = []
        self._remarks: list[str] = []
        self._has_not_applicable = False

    def add_value(self, code_cell: Cell, label: Cell, row_number: int) -> None:
        label = _as_text(label)
        if code_cell == "":  # text without a code: "not applicable" or a remark
            if self._not_applicable_label.lower() in label.lower():
                self._has_not_applicable = True
            # "Não ou não aplicável" says more than "not applicable": keep the wording.
            if label and label != self._not_applicable_label:
                self._remarks.append(label)
            return

        code = normalize_code(code_cell, int(self._fields["width"]))
        if code is None:  # a range or a unit in the code column, not a code
            text = _as_text(code_cell)
            self._value_notes.append(f"{text}: {label}" if label else text)
            return
        if code in self._categories:
            variable = self._fields["variable"]
            raise DictionaryError(f"Row {row_number}: duplicated code {code!r} in {variable}")
        self._categories[code] = label

    def build(self) -> CatalogEntry:
        return CatalogEntry(
            **self._fields,
            categories=self._categories,
            value_note=" | ".join(self._value_notes) or None,
            remark=" | ".join(self._remarks) or None,
            has_not_applicable=self._has_not_applicable,
        )


def _clean(cell: Cell) -> Cell:
    """Collapse line breaks and repeated spaces in text cells; leave numbers alone."""
    if isinstance(cell, float):
        return cell
    return " ".join(cell.split())


def _as_text(cell: Cell) -> str:
    """Text of a cell. Whole numbers lose the ``.0`` Excel adds (``5.0`` -> ``"5"``)."""
    if isinstance(cell, float):
        return str(int(cell)) if cell.is_integer() else str(cell)
    return cell


def _as_int(cell: Cell, row_number: int, what: str) -> int:
    if isinstance(cell, float) and cell.is_integer():
        return int(cell)
    raise DictionaryError(f"Row {row_number}: {what} is not a whole number: {cell!r}")


def _is_blank_row(cells: list[Cell]) -> bool:
    return all(cell == "" for cell in cells)


def _is_heading(cells: list[Cell]) -> bool:
    """A heading has text in the first column and nothing anywhere else."""
    first, rest = cells[0], cells[1:]
    return isinstance(first, str) and first != "" and all(cell == "" for cell in rest)
