"""Read a fixed-width text file in chunks and turn each chunk into a typed DataFrame.

The file is streamed straight out of the .zip archive, a block of lines at a time,
so memory use is bounded by the chunk size and nothing is extracted to disk.
"""

import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import islice
from pathlib import Path

import polars as pl

from lacharm.ingest.sas_input import ColumnSpec, record_length

_LINE = "line"


@dataclass(frozen=True)
class ArchiveMember:
    """The single data file inside a microdata zip archive."""

    name: str
    size_bytes: int  # uncompressed


def find_data_member(zip_path: Path) -> ArchiveMember:
    """Return the only file in the archive; more than one is ambiguous, so it is an error."""
    with zipfile.ZipFile(zip_path) as archive:
        members = [info for info in archive.infolist() if not info.is_dir()]
    if len(members) != 1:
        names = [info.filename for info in members]
        raise ValueError(f"Expected exactly one file in {zip_path.name}, found {names}")
    return ArchiveMember(name=members[0].filename, size_bytes=members[0].file_size)


def iter_line_chunks(
    zip_path: Path, member: str, encoding: str, chunk_rows: int
) -> Iterator[list[str]]:
    """Yield lists of at most ``chunk_rows`` lines, without their line terminators."""
    with zipfile.ZipFile(zip_path) as archive, archive.open(member) as stream:
        while True:
            raw_lines = list(islice(stream, chunk_rows))
            if not raw_lines:
                return
            # Decode the whole block at once: much faster than line by line.
            # Fixed-width positions are byte positions, so the encoding must be
            # single-byte (ASCII, Latin-1): one byte is then exactly one character.
            yield b"".join(raw_lines).decode(encoding).splitlines()


def count_bad_width_lines(lines: list[str], expected_width: int) -> int:
    """Number of lines whose length differs from the record length."""
    return sum(1 for line in lines if len(line) != expected_width)


def detect_float_columns(lines: list[str], specs: list[ColumnSpec]) -> set[str]:
    """Numeric columns that carry a decimal point in the data.

    The SAS informat (``15.``) does not say whether a numeric field is an integer or
    a decimal; the data do, because decimals are written with an explicit point.
    Detection runs on the first chunk only. That is safe: later chunks are cast
    strictly, so a decimal showing up in a column typed as integer raises an error
    instead of being silently truncated.
    """
    frame = pl.DataFrame({_LINE: lines})
    numeric = [spec for spec in specs if spec.kind == "numeric"]
    has_point = frame.select(
        [
            pl.col(_LINE)
            .str.slice(spec.start - 1, spec.width)
            .str.contains(".", literal=True)
            .any()
            .alias(spec.name)
            for spec in numeric
        ]
    ).row(0, named=True)
    return {name for name, flag in has_point.items() if flag}


def parse_chunk(lines: list[str], specs: list[ColumnSpec], float_columns: set[str]) -> pl.DataFrame:
    """Slice each line into typed columns.

    * String columns keep their text exactly as written (``"01"`` keeps its leading
      zero, matching the codes in the dictionary).
    * Numeric columns become Int64, or Float64 if listed in ``float_columns``.
    * A field that is entirely blank becomes null in both cases.
    """
    expected_width = record_length(specs)
    bad = count_bad_width_lines(lines, expected_width)
    if bad:
        raise ValueError(f"{bad} line(s) do not have the expected width of {expected_width}")

    expressions = []
    for spec in specs:
        raw = pl.col(_LINE).str.slice(spec.start - 1, spec.width)
        stripped = raw.str.strip_chars()
        is_blank = stripped == ""
        if spec.kind == "string":
            column = pl.when(is_blank).then(None).otherwise(raw)
        else:
            dtype = pl.Float64 if spec.name in float_columns else pl.Int64
            column = pl.when(is_blank).then(None).otherwise(stripped).cast(dtype, strict=True)
        expressions.append(column.alias(spec.name))

    return pl.DataFrame({_LINE: lines}).select(expressions)
