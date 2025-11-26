<h1 align="center">FlowScribe</h1>

<p align="center">
  <a href="https://www.python.org/">
    <img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white">
  </a>
  <a href="https://ollama.com/">
    <img alt="LLM Backend" src="https://img.shields.io/badge/LLM-Ollama-3FB950">
  </a>
  <a href="#">
    <img alt="Interface" src="https://img.shields.io/badge/Interface-CLI%20%2B%20GUI-4C1">
  </a>
  <a href="https://deepwiki.com/CagriCatik/FlowScribe">
    <img alt="Ask DeepWiki" src="https://deepwiki.com/badge.svg">
  </a>
</p>

<h4 align="center">
A n8n Workflow Documentation Generator
</h4>

- FlowScribe turns n8n workflow JSON definitions into implementation-grade Markdown documentation using a local LLM (Ollama by default).
- The project uses a layered architecture with reusable core services, an extensible LLM client interface, and both CLI and PyQt desktop front-ends.

## Key features

- Recursive discovery of `.json` workflows from a single file or directory tree.
- Prompt-driven documentation generation (system + user templates) with placeholder substitution (e.g., `{filename}`, `{workflow_json}`).
- Ollama backend via `/api/chat`, with an abstraction layer ready for additional LLM providers.
- Output writer that mirrors the input directory structure and can run in dry-run mode.
- Deterministic configuration resolution (defaults < TOML config < environment variables < CLI overrides).
- CLI with `generate`, `dry-run`, and `config show` commands plus clear exit codes.
- PyQt6 GUI wired to the same engine for non-blocking batch runs.
- Unit tests for discovery, JSON handling, prompt building, configuration loading, and the Ollama client (HTTP mocked).

## Repository layout

```bash
flowscribe/
  cli/           # CLI entrypoint and argument parsing
  config/        # Typed config models and loader/merger
  core/          # Discovery, JSON IO, prompt building, engine orchestration, outputs
  gui/           # PyQt6 application using the engine
  llm/           # LLM interface, Ollama client, and related errors
  logging.py     # Shared logging setup
tests/           # Unit tests
````

## Requirements

* Python 3.10+ (uses `tomllib` and pathlib conveniences).
* Local Ollama instance reachable at `http://localhost:11434` (default) or another host you configure.
* Python packages: `requests`, `tqdm`, `rich`, `PyQt6` (for the GUI), and `pytest` for tests.

Install dependencies (example):

```bash
pip install requests tqdm rich PyQt6 pytest
```

## Configuration

FlowScribe resolves configuration in this order: built-in defaults < TOML file < environment variables < CLI flags.

Supported config file names (first match wins):

* `flowscribe.toml`
* `flowscribe-config.toml`

Example `flowscribe.toml`:

```toml
[paths]
input_path = "./workflows"
output_dir = "./generated-docs"

[prompts]
profile = "n8n-doc"
system_prompt = "...custom system instructions..."
user_prompt_template = "...custom user template with {filename} and {workflow_json}..."

[generation]
dry_run = false
verbose = false

[llm]
host = "http://localhost:11434"
model = "llama3.2:1b"

[llm.options]
num_predict = 4096
temperature = 0.18
top_p = 0.9
num_ctx = 8192
repeat_penalty = 1.08
```

Environment variable overrides:

* `FS_LLM_HOST`
* `FS_LLM_MODEL`

## CLI usage

Run the CLI via the module entrypoint:

```bash
python -m flowscribe.cli.main generate /path/to/workflows -o ./docs
```

Commands:

* `generate INPUT_PATH [options]` -- create Markdown docs.
* `dry-run INPUT_PATH [options]` -- list workflows without calling the LLM or writing files.
* `config show [--config PATH]` -- print the resolved configuration.

Common options (shared by `generate` and `dry-run`):

* `-o, --output-dir PATH` -- output directory root (mirrors input structure).
* `--config PATH` -- explicit TOML config file.
* `-m, --model NAME` and `--host URL` -- LLM target.
* `--num-predict`, `--temperature`, `--top-p`, `--num-ctx`, `--repeat-penalty` -- LLM sampling controls.
* `--system-prompt`, `--user-prompt`, `--prompt-profile` -- prompt overrides.
* `-v, --verbose` -- enable DEBUG logging.

Exit codes:

* `0` success
* `1` usage error
* `2` configuration error
* `3` LLM communication error
* `4` runtime/discovery error

## GUI usage

Launch the desktop app (PyQt6 required):

```bash
python -m flowscribe.gui.app
```

The GUI mirrors the CLI capabilities: select input/output paths, choose the Ollama host/model and options, edit prompts, and run batch generation in a non-blocking worker thread with progress and logs.

## Library usage

You can call the engine from Python code:

```python
from pathlib import Path
from flowscribe.config.loader import load_config, apply_cli_overrides
from flowscribe.core.engine import WorkflowEngine

config = load_config()  # merges defaults + flowscribe.toml + env
config = apply_cli_overrides(config, {"input_path": "./workflows", "output_dir": "./docs"})
engine = WorkflowEngine(config)
result = engine.run_batch(input_path=Path("./workflows"), output_root=Path("./docs"))
print(result.processed, "files documented")
```

## Development

Run the test suite:

```bash
pytest -q
```
