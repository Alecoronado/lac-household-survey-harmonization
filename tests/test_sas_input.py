"""Tests for the SAS INPUT parser, on a small hand-written fixture."""

import pytest

from lacharm.ingest.sas_input import (
    ColumnSpec,
    SasInputError,
    parse_sas_input,
    parse_sas_input_text,
    record_length,
)

# Hand-written, in the style of IBGE's input file. Not real survey content.
SAS_INPUT = """\
/* PROGRAMA DE LEITURA EM SAS */

data example;
infile "...\\example.txt" lrecl=4000 Missover;
input
@0001 Ano   $4.   /* Ano de referência */
@0005 UF   $2.   /* Unidade da Federação */
@0007 V2009   3.   /* Idade na data de referência */
@0010 V1032   15.   /* Peso COM calibração */
@0025 VD0001   8.
;
run;
"""


def test_parses_names_positions_and_widths():
    specs = parse_sas_input_text(SAS_INPUT)

    assert [spec.name for spec in specs] == ["Ano", "UF", "V2009", "V1032", "VD0001"]
    assert [spec.start for spec in specs] == [1, 5, 7, 10, 25]
    assert [spec.width for spec in specs] == [4, 2, 3, 15, 8]


def test_dollar_sign_marks_string_columns():
    specs = {spec.name: spec for spec in parse_sas_input_text(SAS_INPUT)}

    assert specs["UF"].kind == "string"
    assert specs["V2009"].kind == "numeric"


def test_description_comes_from_the_comment():
    specs = {spec.name: spec for spec in parse_sas_input_text(SAS_INPUT)}

    assert specs["V2009"].description == "Idade na data de referência"
    assert specs["VD0001"].description == ""  # no comment on that line


def test_record_length_is_the_end_of_the_last_column():
    specs = parse_sas_input_text(SAS_INPUT)

    assert specs[-1] == ColumnSpec("VD0001", 25, 8, "numeric", "")
    assert record_length(specs) == 32


def test_reads_latin1_files(tmp_path):
    path = tmp_path / "input.txt"
    path.write_bytes(SAS_INPUT.encode("latin-1"))

    specs = parse_sas_input(path, encoding="latin-1")

    assert specs[0].description == "Ano de referência"


def test_unparseable_column_line_is_an_error():
    with pytest.raises(SasInputError, match="Line 2"):
        parse_sas_input_text("@0001 Ano $4.\n@0005 UF two.\n")


def test_overlapping_columns_are_an_error():
    with pytest.raises(SasInputError, match="overlap"):
        parse_sas_input_text("@0001 Ano $4.\n@0004 UF $2.\n")


def test_duplicated_names_are_an_error():
    with pytest.raises(SasInputError, match="Duplicated"):
        parse_sas_input_text("@0001 Ano $4.\n@0005 Ano $2.\n")


def test_file_without_columns_is_an_error():
    with pytest.raises(SasInputError, match="No column definitions"):
        parse_sas_input_text("data example;\nrun;\n")
