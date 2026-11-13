"""Tests for the dictionary parser and the catalog cross-checks.

The fixture is a small hand-written sheet in the layout of IBGE's dictionary.
It reproduces the quirks of the real file (codes stored as numbers and as text,
ranges in the code column, "Não aplicável" rows) with made-up content.
"""

import polars as pl
import pytest
import xlwt

from lacharm.ingest.sas_input import ColumnSpec
from lacharm.metadata.catalog import catalog_to_frame, read_catalog_json, write_catalog_json
from lacharm.metadata.compare import compare_with_data, compare_with_input
from lacharm.metadata.ibge_dictionary import (
    DictionaryError,
    DictionaryLayout,
    normalize_code,
    parse_dictionary,
    parse_dictionary_rows,
)

LAYOUT = DictionaryLayout(
    header_rows=2,
    module_heading_pattern=r"^Parte\b",
    universe_pattern=r"pessoas de \d+ anos ou mais de idade",
    not_applicable_label="Não aplicável",
)

PERIOD = "1º tri/2024"

# position, width, variable, question, description, code, category, period
ROWS = [
    ["Dicionário de teste", "", "", "", "", "", "", ""],
    ["Posição", "Tamanho", "Código", "Quesito", "Descrição", "Tipo", "Descrição", "Período"],
    ["Parte 1 - Identificação", "", "", "", "", "", "", ""],
    [1.0, 2.0, "UF", "", "Unidade da\nFederação", 11.0, "Rondônia", PERIOD],
    ["", "", "", "", "", 12.0, "Acre", ""],
    [3.0, 9.0, "UPA", "", "Unidade Primária", "", "UF (2) + Número (7)", PERIOD],
    [
        12.0,
        15.0,
        "V1032",
        "",
        "Peso",
        "6 dígitos e 8 casas decimais",
        "Peso com calibração",
        PERIOD,
    ],
    ["Parte 2 - Trabalho das pessoas de 14 anos ou mais de idade", "", "", "", "", "", "", ""],
    [27.0, 2.0, "V2005", 5.0, "Condição no domicílio", "01", "Pessoa responsável", PERIOD],
    ["", "", "", "", "", "02", "Cônjuge", ""],
    ["", "", "", "", "", 10.0, "Neto(a)", ""],
    [" 2 - Pessoas Ocupadas", "", "", "", "", "", "", ""],
    [29.0, 1.0, "V4001", "1A", "Trabalhou?", 1.0, "Sim", PERIOD],
    ["", "", "", "", "", 2.0, "Não ", ""],
    ["", "", "", "", "", "", "Não aplicável", ""],
    [30.0, 2.0, "V2008", 8.0, "Dia de nascimento", "01 a 31", "Dia", PERIOD],
    ["", "", "", "", "", 99.0, "Não informado", ""],
    [32.0, 1.0, "V4033", 33.0, "Recebia em dinheiro?", 1.0, "Em dinheiro", PERIOD],
    ["", "", "", "", "", "", "Não ou não aplicável", ""],
]


@pytest.fixture
def entries():
    return {entry.variable: entry for entry in parse_dictionary_rows(ROWS, LAYOUT, year=2024)}


def test_one_entry_per_variable_in_sheet_order(entries):
    assert list(entries) == ["UF", "UPA", "V1032", "V2005", "V4001", "V2008", "V4033"]


def test_position_width_label_and_period(entries):
    uf = entries["UF"]

    assert (uf.start, uf.width, uf.year) == (1, 2, 2024)
    assert uf.label == "Unidade da Federação"  # line break collapsed, text not translated
    assert uf.period == PERIOD


def test_numeric_codes_are_normalized_to_the_variable_width(entries):
    assert entries["UF"].categories == {"11": "Rondônia", "12": "Acre"}
    assert entries["V4001"].categories == {"1": "Sim", "2": "Não"}


def test_mixed_text_and_number_codes_end_up_consistent(entries):
    # "01" and "02" are text cells, 10.0 is a number cell: all become 2-character codes.
    assert list(entries["V2005"].categories) == ["01", "02", "10"]


def test_question_number_drops_excel_decimal(entries):
    assert entries["V2005"].question_number == "5"
    assert entries["V4001"].question_number == "1A"
    assert entries["UF"].question_number is None


def test_ranges_and_units_go_to_value_note_not_to_categories(entries):
    assert entries["V1032"].categories == {}
    assert entries["V1032"].value_note == "6 dígitos e 8 casas decimais: Peso com calibração"
    # A range next to a special code: both are kept, separately.
    assert entries["V2008"].value_note == "01 a 31: Dia"
    assert entries["V2008"].categories == {"99": "Não informado"}


def test_not_applicable_sets_a_flag_instead_of_a_category(entries):
    assert entries["V4001"].has_not_applicable is True
    assert entries["V4001"].remark is None
    assert entries["UF"].has_not_applicable is False


def test_variant_of_not_applicable_keeps_its_wording(entries):
    # Here a blank means "no" as well as "not applicable": the wording matters.
    assert entries["V4033"].has_not_applicable is True
    assert entries["V4033"].remark == "Não ou não aplicável"


def test_text_without_a_code_is_a_remark(entries):
    assert entries["UPA"].remark == "UF (2) + Número (7)"
    assert entries["UPA"].categories == {}


def test_module_submodule_and_universe_come_from_headings(entries):
    assert entries["UF"].module == "Parte 1 - Identificação"
    assert entries["UF"].universe is None  # the heading does not state one

    assert entries["V2005"].module.startswith("Parte 2")
    assert entries["V2005"].submodule is None
    assert entries["V2005"].universe == "pessoas de 14 anos ou mais de idade"

    assert entries["V4001"].submodule == "2 - Pessoas Ocupadas"
    assert entries["V4001"].universe == "pessoas de 14 anos ou mais de idade"


def test_normalize_code():
    assert normalize_code(10.0, 2) == "10"
    assert normalize_code(1.0, 2) == "01"
    assert normalize_code("01", 2) == "01"
    assert normalize_code("01 a 14", 2) is None
    assert normalize_code("valor em reais", 8) is None
    with pytest.raises(DictionaryError):
        normalize_code(1.5, 2)


def test_duplicated_code_is_an_error():
    rows = [
        *ROWS,
        [33.0, 1.0, "V9", "", "Teste", 1.0, "Sim", PERIOD],
        ["", "", "", "", "", 1.0, "Não", ""],
    ]

    with pytest.raises(DictionaryError, match="duplicated code"):
        parse_dictionary_rows(rows, LAYOUT, year=2024)


def test_category_before_any_variable_is_an_error():
    rows = [*ROWS[:2], ["", "", "", "", "", 1.0, "Sim", ""]]

    with pytest.raises(DictionaryError, match="unexpected content"):
        parse_dictionary_rows(rows, LAYOUT, year=2024)


def _write_xls(rows, path):
    workbook = xlwt.Workbook()
    sheet = workbook.add_sheet("dicionário")
    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(row):
            if value != "":
                sheet.write(row_index, column_index, value)
    workbook.save(str(path))


def test_reads_a_real_xls_file(tmp_path):
    path = tmp_path / "dictionary.xls"
    _write_xls(ROWS, path)

    from_file = parse_dictionary(path, LAYOUT, year=2024)

    assert from_file == parse_dictionary_rows(ROWS, LAYOUT, year=2024)


def test_catalog_json_round_trip_keeps_accents(tmp_path, entries):
    path = tmp_path / "catalog.json"

    write_catalog_json(list(entries.values()), path)

    assert "Rondônia" in path.read_text(encoding="utf-8")  # not escaped as ô
    assert read_catalog_json(path) == list(entries.values())


def test_catalog_frame_has_one_row_per_variable(entries):
    frame = catalog_to_frame(list(entries.values()))

    assert frame.height == 7
    uf_categories = frame.filter(pl.col("variable") == "UF")["categories"].to_list()[0]
    assert uf_categories == [
        {"code": "11", "label": "Rondônia"},
        {"code": "12", "label": "Acre"},
    ]


# --- Cross-checks -------------------------------------------------------------


def test_compare_with_input_finds_missing_and_mismatched_variables(entries):
    specs = [
        ColumnSpec("UF", 1, 2, "string", ""),
        ColumnSpec("UPA", 3, 8, "string", ""),  # width differs from the dictionary (9)
        ColumnSpec("V9999", 40, 1, "string", ""),  # not in the dictionary
    ]

    comparison = compare_with_input(list(entries.values()), specs)

    assert comparison.only_in_input == ["V9999"]
    assert comparison.only_in_dictionary == ["V1032", "V2005", "V4001", "V2008", "V4033"]
    assert len(comparison.position_mismatches) == 1
    assert comparison.position_mismatches[0].startswith("UPA:")
    assert comparison.coverage_pct == pytest.approx(100 * 2 / 3)


def test_compare_with_data_reports_codes_and_blanks(entries):
    data = pl.LazyFrame(
        {
            "UF": ["11", "11", "13", None],  # 13 is undocumented, 12 unused, blank undocumented
            "V4001": ["1", "2", None, None],  # blanks are documented as "not applicable"
            "V2008": ["05", "31", "99", "99"],  # range variable: other values are expected
        }
    )

    results = {r.variable: r for r in compare_with_data(list(entries.values()), data)}

    assert results["UF"].undocumented == {"13": 1}
    assert results["UF"].unused == ["12"]
    assert results["UF"].blank_not_documented is True

    assert results["V4001"].undocumented == {}
    assert results["V4001"].null_rows == 2
    assert results["V4001"].blank_not_documented is False

    assert results["V2008"].value_note == "01 a 31: Dia"
    assert results["V2008"].undocumented == {"05": 1, "31": 1}


def test_compare_with_data_matches_numeric_columns_by_value(entries):
    data = pl.LazyFrame({"V2005": [1, 2, 10, 7]})  # stored as integers

    result = compare_with_data(list(entries.values()), data)[0]

    assert result.undocumented == {"7": 1}
    assert result.unused == []


# --- End-to-end ---------------------------------------------------------------

SAS_INPUT = """\
input
@0001 UF   $2.   /* Unidade da Federação */
@0003 UPA   $9.   /* UPA */
@0012 V1032   15.   /* Peso COM calibração */
@0027 V2005   $2.   /* Condição no domicílio */
@0029 V4001   $1.   /* Trabalhou */
@0030 V2008   $2.   /* Dia de nascimento */
@0032 V4033   $1.   /* Recebia em dinheiro */
;
"""


def test_run_catalog_writes_catalog_and_report(tmp_path):
    from lacharm.config import SurveyConfig
    from lacharm.metadata.pipeline import run_catalog, write_report

    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "input.txt").write_bytes(SAS_INPUT.encode("latin-1"))
    _write_xls(ROWS, raw_dir / "dictionary.xls")
    config = SurveyConfig.model_validate(
        {
            "survey_id": "tst_survey",
            "country": "TST",
            "name": "Test survey",
            "publisher": "Test",
            "raw_dir": raw_dir,
            "interim_dir": tmp_path / "interim",
            "catalog_dir": tmp_path / "catalog",
            "encoding": {"sas_input": "latin-1", "microdata": "latin-1"},
            "design": {"person_weight": "V1032", "strata": "UF", "psu": "UPA"},
            "dictionary": {
                "header_rows": LAYOUT.header_rows,
                "module_heading_pattern": LAYOUT.module_heading_pattern,
                "universe_pattern": LAYOUT.universe_pattern,
                "not_applicable_label": LAYOUT.not_applicable_label,
            },
            "years": {
                2024: {
                    "microdata_zip": "unused.zip",
                    "sas_input": "input.txt",
                    "dictionary": "dictionary.xls",
                    "deflator": "unused.xls",
                }
            },
        }
    )

    result = run_catalog(config, 2024)
    report_path = tmp_path / "report.md"
    write_report(result, report_path)

    assert result.layout.coverage_pct == 100
    assert result.codes is None  # no ingested data in this test
    assert len(read_catalog_json(result.json_path)) == 7
    assert pl.read_parquet(result.parquet_path).height == 7
    # The SAS program's description is attached to each entry.
    assert result.entries[2].sas_label == "Peso COM calibração"
    assert "Coverage: **100.0%**" in report_path.read_text(encoding="utf-8")
