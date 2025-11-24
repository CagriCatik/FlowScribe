#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import List, Optional, Dict, Any

import requests
from tqdm import tqdm
import logging
from rich.logging import RichHandler

# Logging setup with Rich
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger("n8n-doc-gen")

# Adjust this to the model you have installed in Ollama
DEFAULT_OLLAMA_MODEL = "llama3.2:1b"

# Default config path (same directory as this file)
DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.json")

SYSTEM_PROMPT = (
    "You are an expert technical writer, systems architect, and diagram designer.\n"
    "Your job is to read n8n workflow JSON definitions and produce precise, "
    "implementation-level documentation for engineers.\n\n"
    "Always produce a single, clean Markdown document with this structure:\n\n"
    "1. Title\n"
    "2. Overview\n"
    "   - What the workflow is for, its purpose, and the business/technical problem it solves.\n"
    "3. Triggers and entry points\n"
    "4. Inputs and outputs\n"
    "5. Node-by-node flow\n"
    "6. Control flow and logic\n"
    "7. External integrations\n"
    "8. Error handling and retries\n"
    "9. Configuration and deployment notes\n"
    "10. Security and data protection\n"
    "11. Limitations and extension points\n"
    "12. Visual diagrams\n\n"
    "In section 12 (Visual diagrams), you must generate at least one Mermaid diagram:\n"
    "- A flowchart that shows the main execution path through the workflow nodes.\n"
    "- Optionally, a sequence diagram for key interactions between major components.\n\n"
    "Mermaid requirements:\n"
    "- Use valid Mermaid syntax.\n"
    "- Wrap each diagram in a fenced Markdown code block: ```mermaid on its own line, "
    "then the diagram, then ``` on its own line.\n"
    "- Prefer flowchart LR (left to right) style for node graphs.\n"
    "- Node labels should be concise and derived from n8n node names or types.\n\n"
    "Content guidelines:\n"
    "- Be concise but comprehensive; write for experienced developers.\n"
    "- Use Markdown headings, subheadings, bullet lists, and tables where helpful.\n"
    "- Do not invent functionality beyond what the JSON implies.\n"
    "- When you reasonably infer something, label it with [Inference].\n"
    "- When information cannot be determined from the JSON, state that explicitly.\n"
    "- Do not include the raw JSON in the output.\n"
    "- Do not include any meta commentary about yourself or the generation process.\n"
    "- The Markdown must be self-contained and ready to paste into documentation.\n"
)

USER_PROMPT_TEMPLATE = """You are given an n8n workflow JSON definition.

Using only the information in this JSON and following your system instructions,
generate the complete Markdown documentation for this workflow, including the
required Mermaid diagram(s) in the Visual diagrams section.

Workflow file name: {filename}

Here is the JSON:

```json
{workflow_json}
```"""


def load_config(path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load base configuration from JSON.

    Returns an empty dict if the file does not exist or cannot be parsed.
    """
    cfg_path = path or DEFAULT_CONFIG_PATH
    if not cfg_path.is_file():
        logger.info("Config file not found at %s, using code defaults.", cfg_path)
        return {}
    try:
        with cfg_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            logger.warning("Config file %s does not contain a JSON object. Ignoring.", cfg_path)
            return {}
        logger.info("Loaded config from %s", cfg_path)
        return data
    except Exception as exc:
        logger.warning("Failed to load config from %s: %s. Using code defaults.", cfg_path, exc)
        return {}


def call_ollama(
    json_str: str,
    filename: str,
    model: str = DEFAULT_OLLAMA_MODEL,
    host: str = "http://localhost:11434",
    num_predict: Optional[int] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    num_ctx: Optional[int] = None,
    repeat_penalty: Optional[float] = None,
    system_prompt: Optional[str] = None,
    user_prompt_template: Optional[str] = None,
) -> str:
    """
    Call local Ollama chat API to generate documentation from a workflow JSON.
    Supports extra generation parameters and overridable prompts.
    """
    url = f"{host}/api/chat"
    logger.debug("Calling Ollama at %s with model=%s for file=%s", url, model, filename)
    logger.debug("Prompt JSON length: %d characters", len(json_str))

    sys_prompt = system_prompt or SYSTEM_PROMPT
    usr_template = user_prompt_template or USER_PROMPT_TEMPLATE

    options: dict = {}
    if temperature is not None:
        options["temperature"] = temperature
    if top_p is not None:
        options["top_p"] = top_p
    if num_predict is not None:
        options["num_predict"] = num_predict
    if num_ctx is not None:
        options["num_ctx"] = num_ctx
    if repeat_penalty is not None:
        options["repeat_penalty"] = repeat_penalty

    payload: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {
                "role": "user",
                "content": usr_template.format(
                    filename=filename,
                    workflow_json=json_str,
                ),
            },
        ],
        "stream": False,
    }

    if options:
        logger.debug("Using Ollama options: %s", options)
        payload["options"] = options

    resp = requests.post(url, json=payload)
    logger.debug("Ollama HTTP status: %s", resp.status_code)
    resp.raise_for_status()
    data = resp.json()

    if "message" not in data or "content" not in data["message"]:
        logger.error("Unexpected Ollama response structure for %s: %s", filename, data)
        raise RuntimeError("Unexpected Ollama response structure")

    logger.debug(
        "Ollama response content length for %s: %d characters",
        filename,
        len(data["message"]["content"]),
    )
    return data["message"]["content"]


def is_json_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() == ".json"


def find_json_files(path: Path) -> List[Path]:
    logger.debug("Searching for JSON workflow files under: %s", path)
    if path.is_file() and is_json_file(path):
        logger.debug("Single JSON file input detected: %s", path)
        return [path]
    if path.is_dir():
        files = sorted([p for p in path.rglob("*.json") if p.is_file()])
        logger.debug("Found %d JSON files under directory %s", len(files), path)
        return files
    logger.warning("Input path is neither a file nor a directory: %s", path)
    return []


def load_json_pretty(path: Path) -> str:
    """
    Load JSON and pretty-print it for a cleaner prompt.
    """
    logger.debug("Loading JSON workflow: %s", path)
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    json_str = json.dumps(obj, indent=2, ensure_ascii=False)
    logger.debug("Loaded JSON from %s (pretty-printed length=%d)", path, len(json_str))
    return json_str


def write_markdown(
    output_root: Path,
    base_input: Path,
    json_path: Path,
    content: str,
) -> Path:
    """
    Write one Markdown file per JSON workflow as its description.

    The markdown file name is <json_stem>.md.

    Directory structure under output_root mirrors the structure under base_input.
    """
    logger.debug("Preparing to write markdown for %s", json_path)

    # Compute relative path of the JSON file under the base_input
    rel = (
        json_path.relative_to(base_input)
        if json_path.is_relative_to(base_input)
        else json_path.name
    )
    if isinstance(rel, Path):
        rel_dir = rel.parent
        rel_stem = json_path.stem
    else:
        # In case relative_to was not applicable, fall back to flat structure
        rel_dir = Path(".")
        rel_stem = json_path.stem

    out_dir = output_root / rel_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    logger.debug("Output directory ensured: %s", out_dir)

    out_name = rel_stem + ".md"
    out_path = out_dir / out_name

    logger.debug("Writing markdown file: %s", out_path)
    with out_path.open("w", encoding="utf-8") as f:
        f.write(content)

    logger.debug("Finished writing markdown for %s", json_path)
    return out_path


def process_workflow_file(
    path: Path,
    output_root: Path,
    base_input: Path,
    model: str,
    host: str,
    dry_run: bool = False,
    num_predict: Optional[int] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    num_ctx: Optional[int] = None,
    repeat_penalty: Optional[float] = None,
    system_prompt: Optional[str] = None,
    user_prompt_template: Optional[str] = None,
) -> bool:
    """
    Process a single workflow file.

    Returns True on success, False on failure or if dry_run.
    """
    logger.debug("Starting processing of workflow file: %s", path)

    try:
        json_str = load_json_pretty(path)

        if dry_run:
            logger.info("[DRY RUN] Would analyze: %s", path)
            return False

        logger.info("Analyzing workflow: %s", path)
        doc_markdown = call_ollama(
            json_str=json_str,
            filename=path.name,
            model=model,
            host=host,
            num_predict=num_predict,
            temperature=temperature,
            top_p=top_p,
            num_ctx=num_ctx,
            repeat_penalty=repeat_penalty,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
        )

        out_path = write_markdown(
            output_root=output_root,
            base_input=base_input,
            json_path=path,
            content=doc_markdown,
        )

        logger.info("Markdown description exported: %s", out_path)
        logger.debug("Successfully processed workflow file: %s", path)
        return True

    except Exception as exc:
        logger.exception("Failed to process workflow file %s: %s", path, exc)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate Markdown description documentation for n8n workflow JSON files "
            "using a local Ollama model."
        )
    )
    parser.add_argument(
        "input_path",
        type=str,
        help="Path to a single JSON file or a directory containing JSON workflow files.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default="generated",
        help="Root directory where Markdown description files will be written. Default: generated",
    )
    parser.add_argument(
        "-m",
        "--model",
        type=str,
        default=None,
        help=f"Ollama model name to use. Default: value from config or {DEFAULT_OLLAMA_MODEL}",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Base URL of the local Ollama server. Default: value from config or http://localhost:11434",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List the JSON workflow files that would be analyzed without calling Ollama.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG-level) logging.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help=f"Path to JSON config file. Default: {DEFAULT_CONFIG_PATH.name} next to core.py",
    )
    # LLM tuning parameters
    parser.add_argument(
        "--num-predict",
        type=int,
        default=None,
        help="Maximum number of tokens to generate (num_predict). Default: model or config default",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Sampling temperature. Default: model or config default",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=None,
        help="Top-p nucleus sampling parameter. Default: model or config default",
    )
    parser.add_argument(
        "--num-ctx",
        type=int,
        default=None,
        help="Context window size (num_ctx). Default: model or config default",
    )
    parser.add_argument(
        "--repeat-penalty",
        type=float,
        default=None,
        help="Repeat penalty for tokens. Default: model or config default",
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")

    cfg_path = Path(args.config).expanduser().resolve() if args.config else None
    config = load_config(cfg_path)

    # Merge config and CLI
    host = args.host or config.get("host") or "http://localhost:11434"
    model = args.model or config.get("model") or DEFAULT_OLLAMA_MODEL
    num_predict = args.num_predict if args.num_predict is not None else config.get("num_predict")
    temperature = args.temperature if args.temperature is not None else config.get("temperature")
    top_p = args.top_p if args.top_p is not None else config.get("top_p")
    num_ctx = args.num_ctx if args.num_ctx is not None else config.get("num_ctx")
    repeat_penalty = (
        args.repeat_penalty if args.repeat_penalty is not None else config.get("repeat_penalty")
    )

    system_prompt = config.get("system_prompt", SYSTEM_PROMPT)
    user_prompt_template = config.get("user_prompt_template", USER_PROMPT_TEMPLATE)

    input_path = Path(args.input_path).expanduser().resolve()
    output_root = Path(args.output_dir).expanduser().resolve()

    logger.debug("Resolved input path: %s", input_path)
    logger.debug("Resolved output root: %s", output_root)
    logger.debug("Using model: %s", model)
    logger.debug("Using host: %s", host)
    logger.debug("Dry run: %s", args.dry_run)
    logger.debug("num_predict: %s", num_predict)
    logger.debug("temperature: %s", temperature)
    logger.debug("top_p: %s", top_p)
    logger.debug("num_ctx: %s", num_ctx)
    logger.debug("repeat_penalty: %s", repeat_penalty)

    json_files = find_json_files(input_path)
    if not json_files:
        logger.warning("No JSON workflow files found under: %s", input_path)
        return

    logger.info("Found %d workflow JSON file(s) to analyze.", len(json_files))

    processed_count = 0
    failed_count = 0

    for p in tqdm(json_files, desc="Processing workflows", unit="file"):
        success = process_workflow_file(
            path=p,
            output_root=output_root,
            base_input=input_path if input_path.is_dir() else p.parent,
            model=model,
            host=host,
            dry_run=args.dry_run,
            num_predict=num_predict,
            temperature=temperature,
            top_p=top_p,
            num_ctx=num_ctx,
            repeat_penalty=repeat_penalty,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
        )
        if success:
            processed_count += 1
        else:
            failed_count += 1

    logger.info(
        "Processing complete. Total files: %d, succeeded: %d, failed: %d",
        len(json_files),
        processed_count,
        failed_count,
    )

    if args.dry_run:
        logger.info(
            "Dry run mode was enabled. No calls were made to Ollama and no markdown files were written."
        )


if __name__ == "__main__":
    main()
