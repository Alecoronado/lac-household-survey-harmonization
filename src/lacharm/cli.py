"""Command-line entry point. Each phase registers its subcommand here."""

import argparse
import logging
from pathlib import Path

from lacharm import __version__

REPORTS_DIR = Path("reports")


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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command is None:
        return 0
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
