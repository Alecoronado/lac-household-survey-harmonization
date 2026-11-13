"""Tests for the harmonized schema: the real YAML is valid and the validation rules hold."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from lacharm.schema import HarmonizedSchema, HarmonizedVariable, load_schema, render_markdown

SCHEMA_PATH = Path("config/harmonized_schema.yaml")
SCHEMA_DOC_PATH = Path("docs/harmonized_schema.md")


@pytest.fixture(scope="module")
def schema() -> HarmonizedSchema:
    return load_schema(SCHEMA_PATH)


# --- The real schema ----------------------------------------------------------


def test_schema_file_is_valid_and_has_the_agreed_size(schema):
    assert 30 <= len(schema.variables) <= 40


def test_every_block_is_present(schema):
    blocks = {variable.block for variable in schema.variables}

    assert blocks == {"identification", "demographics", "education", "labor", "income", "housing"}


def test_schema_names_no_country_and_no_source_variable(schema):
    # The target must stay survey-agnostic: survey knowledge lives in config/surveys/.
    text = SCHEMA_PATH.read_text(encoding="utf-8")
    variables_section = text[text.index("\nvariables:") :]

    for forbidden in ("PNAD", "IBGE", "Brazil", "Brasil", "V1032", "VD5008"):
        assert forbidden not in variables_section


def test_design_variables_cannot_be_null(schema):
    for name in ("household_id", "person_id", "weight", "strata", "psu", "sex", "age"):
        assert schema.get(name).nullable is False


def test_income_per_capita_is_derived_from_income_and_size(schema):
    variable = schema.get("household_income_pc")

    assert variable.origin == "derived"
    assert variable.derived_from == ["household_income", "household_size"]
    assert variable.level == "household"


def test_only_mapped_variables_are_left_for_the_llm(schema):
    mapped = {variable.name for variable in schema.by_origin("mapped")}

    assert "country" not in mapped  # constant from the survey config
    assert "household_size" not in mapped  # derived
    assert {"sex", "age", "labor_status", "labor_income"} <= mapped


def test_generated_documentation_is_up_to_date(schema):
    # Fails when the YAML changes and `make schema` was not run again.
    assert SCHEMA_DOC_PATH.read_text(encoding="utf-8") == render_markdown(schema)


def test_get_unknown_variable_is_an_error(schema):
    with pytest.raises(KeyError, match="not_a_variable"):
        schema.get("not_a_variable")


# --- Validation rules ---------------------------------------------------------


def _variable(**overrides) -> dict:
    base = {
        "name": "example",
        "block": "demographics",
        "level": "person",
        "type": "integer",
        "origin": "mapped",
        "definition": "An example variable for tests.",
        "nullable": False,
        "missing": "Not allowed.",
    }
    return {**base, **overrides}


def _schema(*variables: dict) -> dict:
    return {
        "schema_version": "test",
        "description": "Test schema.",
        "references": [],
        "conventions": {
            "missing_values": "x",
            "household_membership": "x",
            "income": "x",
            "not_applied": "x",
        },
        "variables": list(variables),
    }


def test_minimal_variable_is_valid():
    assert HarmonizedVariable.model_validate(_variable()).name == "example"


def test_category_needs_allowed_values():
    with pytest.raises(ValidationError, match="at least two allowed_values"):
        HarmonizedVariable.model_validate(_variable(type="category"))


def test_allowed_values_only_for_categories():
    with pytest.raises(ValidationError, match="only valid for type 'category'"):
        HarmonizedVariable.model_validate(_variable(allowed_values={1: "a", 2: "b"}))


def test_string_cannot_have_a_range():
    with pytest.raises(ValidationError, match="string cannot have a range"):
        HarmonizedVariable.model_validate(_variable(type="string", range={"min": 0}))


def test_range_bounds_must_be_ordered():
    with pytest.raises(ValidationError, match="greater than max"):
        HarmonizedVariable.model_validate(_variable(range={"min": 5, "max": 1}))


def test_derived_variable_must_say_what_it_is_derived_from():
    with pytest.raises(ValidationError, match="must list derived_from"):
        HarmonizedVariable.model_validate(_variable(origin="derived"))


def test_mapped_variable_cannot_list_derived_from():
    with pytest.raises(ValidationError, match="only valid for origin 'derived'"):
        HarmonizedVariable.model_validate(_variable(derived_from=["other"]))


def test_variable_with_a_universe_must_be_nullable():
    with pytest.raises(ValidationError, match="must be nullable"):
        HarmonizedVariable.model_validate(_variable(universe="Employed persons."))


def test_name_must_be_snake_case():
    with pytest.raises(ValidationError):
        HarmonizedVariable.model_validate(_variable(name="HouseholdSize"))


def test_unknown_field_is_rejected():
    with pytest.raises(ValidationError):
        HarmonizedVariable.model_validate(_variable(defintion="typo"))


def test_duplicated_names_are_rejected():
    with pytest.raises(ValidationError, match="duplicated variable names"):
        HarmonizedSchema.model_validate(_schema(_variable(), _variable()))


def test_derived_from_must_reference_existing_variables():
    derived = _variable(name="total", origin="derived", derived_from=["missing_one"])

    with pytest.raises(ValidationError, match="derived_from unknown variables"):
        HarmonizedSchema.model_validate(_schema(_variable(), derived))
