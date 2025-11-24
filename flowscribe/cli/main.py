"""Command line entrypoint for FlowScribe."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..config.loader import apply_cli_overrides, load_config, ConfigError
from ..config.model import AppConfig
from ..core.engine import WorkflowEngine, RunResult
from ..core.discovery import DiscoveryError
from ..logging import setup_logging, get_logger
from ..llm.errors import LLMError

EXIT_SUCCESS = 0
EXIT_USAGE = 1
EXIT_CONFIG = 2
EXIT_LLM = 3
EXIT_RUNTIME = 4

logger = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flowscribe", description="Generate Markdown docs for n8n workflows.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate documentation")
    _add_shared_options(generate)

    dry_run = subparsers.add_parser("dry-run", help="List workflows without generating docs")
    _add_shared_options(dry_run)

    config_cmd = subparsers.add_parser("config", help="Configuration utilities")
    config_cmd.add_argument("action", choices=["show"], help="Show resolved configuration")

    return parser


def _add_shared_options(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("input_path", type=str, help="Path to workflow JSON file or directory")
    sub.add_argument("-o", "--output-dir", type=str, default=None, help="Output directory root")
    sub.add_argument("--config", type=str, default=None, help="Path to flowscribe TOML config")
    sub.add_argument("-m", "--model", type=str, default=None, help="LLM model name")
    sub.add_argument("--host", type=str, default=None, help="LLM host URL")
    sub.add_argument("--num-predict", type=int, dest="num_predict")
    sub.add_argument("--temperature", type=float)
    sub.add_argument("--top-p", dest="top_p", type=float)
    sub.add_argument("--num-ctx", dest="num_ctx", type=int)
    sub.add_argument("--repeat-penalty", dest="repeat_penalty", type=float)
    sub.add_argument("--system-prompt", dest="system_prompt", type=str)
    sub.add_argument("--user-prompt", dest="user_prompt", type=str)
    sub.add_argument("--prompt-profile", dest="prompt_profile", type=str)
    sub.add_argument("-v", "--verbose", action="store_true")


def _run_generation(config: AppConfig) -> RunResult:
    engine = WorkflowEngine(config)
    return engine.run_batch(
        input_path=config.paths.input_path or Path("."),
        output_root=config.paths.output_dir,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args_ns = parser.parse_args(argv)
    args = vars(args_ns)

    setup_logging(level=(10 if args.get("verbose") else 20))

    try:
        base_config = load_config(Path(args.get("config")) if args.get("config") else None)
    except ConfigError as exc:
        logger.error("Configuration error: %s", exc)
        return EXIT_CONFIG

    merged = apply_cli_overrides(base_config, args)
    merged.generation.dry_run = merged.generation.dry_run or args_ns.command == "dry-run"

    if args_ns.command == "config":
        print(merged)
        return EXIT_SUCCESS

    if merged.paths.input_path is None:
        logger.error("Input path is required")
        return EXIT_USAGE

    try:
        result = _run_generation(merged)
    except DiscoveryError as exc:
        logger.error("Discovery failed: %s", exc)
        return EXIT_RUNTIME
    except LLMError as exc:
        logger.error("LLM communication failed: %s", exc)
        return EXIT_LLM
    except Exception as exc:  # pragma: no cover - unexpected
        logger.exception("Unexpected error: %s", exc)
        return EXIT_RUNTIME

    logger.info(
        "Processing complete. Total files: %d, succeeded: %d, failed: %d",
        result.total,
        result.processed,
        result.failed,
    )

    if merged.generation.dry_run:
        logger.info("Dry run enabled; no files were generated.")

    return EXIT_SUCCESS


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
