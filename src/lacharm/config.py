"""Survey configuration: everything survey-specific lives in YAML, not in code.

Adding a country means adding a file under ``config/surveys/``; the pipeline code
only ever sees a validated :class:`SurveyConfig`.
"""

from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    # Unknown keys are errors, so a typo in the YAML fails loudly instead of being ignored.
    model_config = ConfigDict(extra="forbid")


class OfficialFigure(_StrictModel):
    """A published benchmark, with enough provenance to be re-checked."""

    value: float
    unit: str
    source: str
    url: str
    consulted: date


class YearFiles(_StrictModel):
    """Raw files for one survey year, relative to ``raw_dir``."""

    microdata_zip: str
    sas_input: str
    dictionary: str
    deflator: str
    official_population: OfficialFigure | None = None


class Encoding(_StrictModel):
    sas_input: str
    microdata: str


class Design(_StrictModel):
    """Names of the sampling-design variables in the source survey."""

    person_weight: str
    strata: str
    psu: str


class DictionaryConfig(_StrictModel):
    """How to read the publisher's variable dictionary."""

    header_rows: int
    module_heading_pattern: str
    universe_pattern: str
    not_applicable_label: str


class SurveyConfig(_StrictModel):
    survey_id: str
    country: str = Field(pattern=r"^[A-Z]{3}$")  # ISO 3166-1 alpha-3
    name: str
    publisher: str
    raw_dir: Path
    interim_dir: Path
    catalog_dir: Path
    encoding: Encoding
    design: Design
    dictionary: DictionaryConfig
    years: dict[int, YearFiles]

    def files_for(self, year: int) -> YearFiles:
        if year not in self.years:
            available = sorted(self.years)
            raise KeyError(f"Year {year} is not configured for {self.survey_id}: {available}")
        return self.years[year]

    def raw_path(self, filename: str) -> Path:
        return self.raw_dir / filename

    def interim_path(self, year: int) -> Path:
        return self.interim_dir / str(year)


def load_survey_config(path: Path) -> SurveyConfig:
    """Load and validate a survey YAML file."""
    with Path(path).open(encoding="utf-8") as handle:
        return SurveyConfig.model_validate(yaml.safe_load(handle))
