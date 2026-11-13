"""Command-line entry point. Each phase registers its subcommand here."""

import argparse
import logging
from pathlib import Path

from lacharm import __version__

REPORTS_DIR = Path("reports")
SCHEMA_PATH = Path("config/harmonized_schema.yaml")
SCHEMA_DOC_PATH = Path("docs/harmonized_schema.md")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lacharm",
        description="LLM-assisted harmonization of Latin American household surveys.",
    )
    parser.add_argument("--version", action="version", version=f"lacharm {__version__}")
    subcommands = parser.add_subparsers(dest="command")

    ingest = subcommands.add_parser(
        "ingest", help="Convert raw fixed-width microdata to Parquet and validate it."
    )
    ingest.add_argument("--survey", type=Path, required=True, help="Survey YAML file.")
    ingest.add_argument("--year", type=int, required=True, help="Survey year to ingest.")
    ingest.set_defaults(handler=_ingest)

    catalog = subcommands.add_parser(
        "catalog", help="Build the variable catalog from the dictionary and cross-check it."
    )
    catalog.add_argument("--survey", type=Path, required=True, help="Survey YAML file.")
    catalog.add_argument("--year", type=int, required=True, help="Survey year.")
    catalog.set_defaults(handler=_catalog)

    schema = subcommands.add_parser(
        "schema", help="Validate the harmonized schema and regenerate its documentation."
    )
    schema.add_argument("--schema", type=Path, default=SCHEMA_PATH, help="Schema YAML file.")
    schema.add_argument("--doc", type=Path, default=SCHEMA_DOC_PATH, help="Markdown output.")
    schema.set_defaults(handler=_schema)

    return parser


def _ingest(args: argparse.Namespace) -> int:
    # Imported here so `lacharm --version` stays fast and dependency-free.
    from lacharm.config import load_survey_config
    from lacharm.ingest.pipeline import run_ingest, write_report

    config = load_survey_config(args.survey)
    result = run_ingest(config, args.year)

    report_path = REPORTS_DIR / f"ingest_{config.survey_id}_{args.year}.md"
    write_report(result, config.files_for(args.year).sas_input, report_path)

    logging.info("Rows: %d | columns: %d", result.rows_written, result.n_columns)
    logging.info("Sum of %s: %.0f", result.weight_variable, result.weight_sum)
    if result.population_diff_pct is not None:
        logging.info("Difference vs official population: %+.4f%%", result.population_diff_pct)
    logging.info("Report: %s", report_path)
    return 0


def _catalog(args: argparse.Namespace) -> int:
    from lacharm.config import load_survey_config
    from lacharm.metadata.pipeline import run_catalog, write_report

    config = load_survey_config(args.survey)
    result = run_catalog(config, args.year)

    report_path = REPORTS_DIR / f"catalog_{config.survey_id}_{args.year}.md"
    write_report(result, report_path)

    logging.info("Coverage of the input program: %.1f%%", result.layout.coverage_pct)
    logging.info("Catalog: %s", result.json_path)
    logging.info("Report: %s", report_path)
    return 0


def _schema(args: argparse.Namespace) -> int:
    from lacharm.schema import load_schema, render_markdown

    schema = load_schema(args.schema)  # raises if the YAML is inconsistent
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text(render_markdown(schema), encoding="utf-8", newline="\n")

    logging.info("Schema %s is valid: %d variables", schema.schema_version, len(schema.variables))
    logging.info("Documentation: %s", args.doc)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command is None:
        return 0
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
