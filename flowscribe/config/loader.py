"""Configuration loading and merging utilities."""
from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Optional

from .model import AppConfig, GenerationConfig, LLMConfig, LLMOptions, PathsConfig, PromptConfig
from ..logging import get_logger

logger = get_logger(__name__)

DEFAULT_CONFIG_FILENAMES = ["flowscribe.toml", "flowscribe-config.toml"]


class ConfigError(Exception):
    """Raised when configuration cannot be loaded or is invalid."""


def _load_file(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        content = path.read_bytes()
        data = tomllib.loads(content.decode("utf-8"))
        if not isinstance(data, dict):
            raise ConfigError(f"Config at {path} is not a TOML table")
        logger.debug("Loaded config file: %s", path)
        return data
    except Exception as exc:  # pragma: no cover - file IO edge cases
        raise ConfigError(f"Failed to load config from {path}: {exc}") from exc


def _env_override() -> dict:
    mapping = {
        "FS_LLM_HOST": ("llm", "host"),
        "FS_LLM_MODEL": ("llm", "model"),
    }
    overrides: dict = {}
    for env_name, path in mapping.items():
        if env_name in os.environ:
            current = overrides
            for key in path[:-1]:
                current = current.setdefault(key, {})
            current[path[-1]] = os.environ[env_name]
    return overrides


def _dict_to_config(raw: dict) -> AppConfig:
    llm_cfg = raw.get("llm", {}) if isinstance(raw.get("llm", {}), dict) else {}
    llm_opts = llm_cfg.get("options", {}) if isinstance(llm_cfg.get("options", {}), dict) else {}

    paths_cfg = raw.get("paths", {}) if isinstance(raw.get("paths", {}), dict) else {}
    prompts_cfg = raw.get("prompts", {}) if isinstance(raw.get("prompts", {}), dict) else {}
    gen_cfg = raw.get("generation", {}) if isinstance(raw.get("generation", {}), dict) else {}

    return AppConfig(
        paths=PathsConfig(
            input_path=Path(paths_cfg["input_path"]).expanduser() if paths_cfg.get("input_path") else None,
            output_dir=Path(paths_cfg.get("output_dir", "generated")).expanduser(),
        ),
        prompts=PromptConfig(
            profile=prompts_cfg.get("profile", "n8n-doc"),
            system_prompt=prompts_cfg.get("system_prompt", PromptConfig().system_prompt),
            user_prompt_template=prompts_cfg.get(
                "user_prompt_template", PromptConfig().user_prompt_template
            ),
        ),
        generation=GenerationConfig(
            dry_run=bool(gen_cfg.get("dry_run", False)),
            verbose=bool(gen_cfg.get("verbose", False)),
        ),
        llm=LLMConfig(
            host=llm_cfg.get("host", LLMConfig().host),
            model=llm_cfg.get("model", LLMConfig().model),
            options=LLMOptions(
                num_predict=llm_opts.get("num_predict"),
                temperature=llm_opts.get("temperature"),
                top_p=llm_opts.get("top_p"),
                num_ctx=llm_opts.get("num_ctx"),
                repeat_penalty=llm_opts.get("repeat_penalty"),
            ),
        ),
    )


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    """Load configuration from file, environment, and defaults.

    Resolution order: defaults < config file < env vars < CLI (applied separately).
    """

    base = AppConfig()

    paths_to_try = [config_path] if config_path else [Path(name) for name in DEFAULT_CONFIG_FILENAMES]
    file_data: dict = {}
    for path in paths_to_try:
        if path and path.is_file():
            file_data = _load_file(path)
            break
    file_config = _dict_to_config(file_data) if file_data else AppConfig()

    env_config = _dict_to_config(_env_override()) if _env_override() else AppConfig()

    config = base.merge(file_config).merge(env_config)
    logger.debug("Config resolved: %s", config)
    return config


def apply_cli_overrides(base: AppConfig, args: dict) -> AppConfig:
    """Merge CLI-style overrides (dict of provided values) into an AppConfig."""

    override_cfg = AppConfig(
        paths=PathsConfig(
            input_path=Path(args["input_path"]).expanduser().resolve() if args.get("input_path") else None,
            output_dir=Path(args["output_dir"]).expanduser().resolve() if args.get("output_dir") else None,
        ),
        prompts=PromptConfig(
            profile=args.get("prompt_profile", base.prompts.profile),
            system_prompt=args.get("system_prompt") or base.prompts.system_prompt,
            user_prompt_template=args.get("user_prompt") or base.prompts.user_prompt_template,
        ),
        generation=GenerationConfig(
            dry_run=bool(args.get("dry_run", False)),
            verbose=bool(args.get("verbose", False)),
        ),
        llm=LLMConfig(
            host=args.get("host") or base.llm.host,
            model=args.get("model") or base.llm.model,
            options=LLMOptions(
                num_predict=args.get("num_predict"),
                temperature=args.get("temperature"),
                top_p=args.get("top_p"),
                num_ctx=args.get("num_ctx"),
                repeat_penalty=args.get("repeat_penalty"),
            ),
        ),
    )

    return base.merge(override_cfg)
