"""Tests for the fixed-width reader and the ingest step, on hand-written fixtures.

The fixture mimics the layout of a household survey file. Its values are made up
for testing the parser only; they are not survey data.
"""

import zipfile

import polars as pl
import pytest

from lacharm.config import SurveyConfig, load_survey_config
from lacharm.ingest.fixed_width import (
    count_bad_width_lines,
    detect_float_columns,
    find_data_member,
    parse_chunk,
)
from lacharm.ingest.pipeline import IngestValidationError, run_ingest
from lacharm.ingest.sas_input import parse_sas_input_text

SAS_INPUT = """\
input
@0001 Ano   $4.   /* Ano de referência */
@0005 UF   $2.   /* Unidade da Federação */
@0007 V2009   3.   /* Idade */
@0010 V1032   9.   /* Peso */
@0019 V3001   $1.   /* Sabe ler */
;
"""

# Columns:  Ano  UF V2009 V1032     V3001
DATA_LINES = [
    "202401035000100.50" + "1",
    "202411007000200.25" + "2",
    "202435   000050.00" + " ",  # blank age and blank V3001
]

SPECS = parse_sas_input_text(SAS_INPUT)


def test_detects_which_numeric_columns_have_decimals():
    assert detect_float_columns(DATA_LINES, SPECS) == {"V1032"}


def test_parse_chunk_assigns_types():
    frame = parse_chunk(DATA_LINES, SPECS, float_columns={"V1032"})

    assert frame.schema == {
        "Ano": pl.String,
        "UF": pl.String,
        "V2009": pl.Int64,
        "V1032": pl.Float64,
        "V3001": pl.String,
    }


def test_parse_chunk_keeps_codes_as_written_and_parses_numbers():
    frame = parse_chunk(DATA_LINES, SPECS, float_columns={"V1032"})

    assert frame["UF"].to_list() == ["01", "11", "35"]  # leading zero preserved
    assert frame["V2009"].to_list() == [35, 7, None]
    assert frame["V1032"].to_list() == [100.5, 200.25, 50.0]


def test_blank_fields_become_null():
    frame = parse_chunk(DATA_LINES, SPECS, float_columns={"V1032"})

    assert frame["V3001"].to_list() == ["1", "2", None]


def test_line_with_wrong_width_is_rejected():
    lines = [*DATA_LINES, DATA_LINES[0] + "X"]

    assert count_bad_width_lines(lines, expected_width=19) == 1
    with pytest.raises(ValueError, match="expected width"):
        parse_chunk(lines, SPECS, float_columns={"V1032"})


def test_decimal_in_an_integer_column_is_an_error_not_a_truncation():
    lines = ["2024013.5000100.501"]

    with pytest.raises(pl.exceptions.InvalidOperationError):
        parse_chunk(lines, SPECS, float_columns={"V1032"})


# --- End-to-end on a tiny zip -------------------------------------------------


def _make_survey(tmp_path, data_lines, newline="\r\n", official_population=None) -> SurveyConfig:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "input.txt").write_bytes(SAS_INPUT.encode("latin-1"))
    payload = "".join(line + newline for line in data_lines).encode("latin-1")
    with zipfile.ZipFile(raw_dir / "micro.zip", "w") as archive:
        archive.writestr("micro.txt", payload)

    year_files = {
        "microdata_zip": "micro.zip",
        "sas_input": "input.txt",
        "dictionary": "unused.xls",
        "deflator": "unused.xls",
    }
    if official_population is not None:
        year_files["official_population"] = {
            "value": official_population,
            "unit": "persons",
            "source": "test",
            "url": "https://example.org",
            "consulted": "2026-01-01",
        }
    return SurveyConfig.model_validate(
        {
            "survey_id": "tst_survey",
            "country": "TST",
            "name": "Test survey",
            "publisher": "Test",
            "raw_dir": raw_dir,
            "interim_dir": tmp_path / "interim",
            "encoding": {"sas_input": "latin-1", "microdata": "latin-1"},
            "design": {"person_weight": "V1032", "strata": "UF", "psu": "UF"},
            "years": {2024: year_files},
        }
    )


def test_find_data_member_reports_uncompressed_size(tmp_path):
    config = _make_survey(tmp_path, DATA_LINES)

    member = find_data_member(config.raw_path("micro.zip"))

    assert member.name == "micro.txt"
    assert member.size_bytes == 3 * (19 + 2)  # three lines, CRLF


def test_run_ingest_writes_parquet_in_chunks_and_validates(tmp_path):
    config = _make_survey(tmp_path, DATA_LINES, official_population=350.0)

    result = run_ingest(config, 2024, chunk_rows=2)

    assert result.rows_read == result.rows_written == result.rows_expected == 3
    assert result.n_parts == 2  # 2 rows + 1 row
    assert result.weight_sum == pytest.approx(350.75)
    assert result.population_diff_pct == pytest.approx(100 * 0.75 / 350)

    written = pl.read_parquet(config.interim_path(2024) / "part-*.parquet")
    assert written.height == 3
    assert written.columns == ["Ano", "UF", "V2009", "V1032", "V3001"]


def test_run_ingest_is_reproducible_and_removes_stale_parts(tmp_path):
    config = _make_survey(tmp_path, DATA_LINES)

    run_ingest(config, 2024, chunk_rows=1)  # three parts
    run_ingest(config, 2024, chunk_rows=3)  # one part: the other two must be gone

    parts = sorted(path.name for path in config.interim_path(2024).glob("*.parquet"))
    assert parts == ["part-00000.parquet"]


def test_run_ingest_handles_unix_line_endings(tmp_path):
    config = _make_survey(tmp_path, DATA_LINES, newline="\n")

    assert run_ingest(config, 2024).newline_bytes == 1


def test_run_ingest_fails_when_file_size_does_not_match_row_count(tmp_path):
    # Last line has no terminator: the size-implied row count is fractional.
    config = _make_survey(tmp_path, DATA_LINES)
    zip_path = config.raw_path("micro.zip")
    payload = "\r\n".join(DATA_LINES).encode("latin-1")
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("micro.txt", payload)

    with pytest.raises(IngestValidationError, match="Row count mismatch"):
        run_ingest(config, 2024)


def test_unknown_year_is_an_error(tmp_path):
    config = _make_survey(tmp_path, DATA_LINES)

    with pytest.raises(KeyError, match="2023"):
        run_ingest(config, 2023)


# --- The real survey config ---------------------------------------------------


def test_brazil_config_is_valid():
    config = load_survey_config("config/surveys/bra_pnadc_visita1.yaml")

    assert config.country == "BRA"
    assert config.design.person_weight == "V1032"
    assert 2024 in config.years
