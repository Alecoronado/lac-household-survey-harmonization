"""The variable catalog: one structured entry per source variable.

The catalog is the common interface between a survey's documentation and the rest
of the pipeline. Each statistical office ships its dictionary in a different
layout, so each needs its own parser, but every parser produces these entries.
The LLM mapping step reads the catalog, never the original dictionary.

Text is kept in the source language. Nothing is translated or paraphrased.
"""

import json
from pathlib import Path

import polars as pl
from pydantic import BaseModel, ConfigDict


class CatalogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variable: str
    label: str  # question text or description, as written in the dictionary
    sas_label: str | None = None  # short description from the SAS input program
    question_number: str | None = None
    categories: dict[str, str] = {}  # code (as stored in the data) -> label
    value_note: str | None = None  # range or unit written in the code column
    remark: str | None = None  # other text attached to the variable, without a code
    has_not_applicable: bool = False  # the dictionary says a blank means "not applicable"
    module: str | None = None
    submodule: str | None = None
    universe: str | None = None  # only what the dictionary states explicitly
    period: str | None = None
    year: int
    start: int  # 1-based position, as documented in the dictionary
    width: int


def write_catalog_json(entries: list[CatalogEntry], path: Path) -> None:
    """Write the catalog as readable UTF-8 JSON (accents are not escaped)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [entry.model_dump() for entry in entries]
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def read_catalog_json(path: Path) -> list[CatalogEntry]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [CatalogEntry.model_validate(item) for item in payload]


def catalog_to_frame(entries: list[CatalogEntry]) -> pl.DataFrame:
    """The catalog as a table. Categories become a list of {code, label} structs."""
    records = []
    for entry in entries:
        record = entry.model_dump()
        record["categories"] = [
            {"code": code, "label": label} for code, label in entry.categories.items()
        ]
        records.append(record)
    category_type = pl.List(pl.Struct({"code": pl.String, "label": pl.String}))
    return pl.DataFrame(records, schema_overrides={"categories": category_type})
