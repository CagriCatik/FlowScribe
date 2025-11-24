analyse this readme, consider this as requirements list. implement a core.py and ui.py and main.py
i have already
# n8n Workflow Documentation Generator

Generate implementation-level Markdown documentation for n8n workflow JSON files using a local Ollama model.  
Each workflow JSON becomes a self-contained Markdown document with a fixed structure and Mermaid diagrams.

---

## Overview

This tool:

- Scans a single `.json` file or a directory tree of `.json` files.
- Sends each JSON workflow definition to a local Ollama model via its `/api/chat` endpoint.
- Receives Markdown documentation from the model (including Mermaid diagrams).
- Writes one `.md` file per workflow, mirroring the input directory structure under an output root.

Typical use case: you already have n8n workflows stored as JSON, and you want consistent, engineer-focused documentation generated automatically.

---

## Features

- Recursive discovery of `.json` workflow files.
- One Markdown document per workflow.
- Fixed documentation structure enforced via a system prompt:
  - Title  
  - Overview  
  - Triggers and entry points  
  - Inputs and outputs  
  - Node-by-node flow  
  - Control flow and logic  
  - External integrations  
  - Error handling and retries  
  - Configuration and deployment notes  
  - Security and data protection  
  - Limitations and extension points  
  - Visual diagrams (with Mermaid)
- Mermaid diagrams:
  - At least one flowchart (flowchart LR).
  - Optional sequence diagrams.
- Dry-run mode (no API calls, no writes).
- Rich logging with optional verbose (DEBUG) output.
- Progress bar for workflow processing.

---

## Requirements

- Python 3.9 or newer  
  (required for `pathlib.Path.is_relative_to`)
- A running local Ollama instance exposing:
  - `POST /api/chat`
- Python packages:
  - `requests`
  - `tqdm`
  - `rich`

Install dependencies:

```bash
pip install requests tqdm rich
````

---

## Installation

Clone or copy this script into your project. Assume the script file is named `n8n_doc_gen.py` [Inference].

Recommended layout:

```text
project-root/
  workflows/          # your n8n JSON workflows
  n8n_doc_gen.py     # this script
```

---

## Usage

### Basic command

```bash
python n8n_doc_gen.py INPUT_PATH [options]
```

`INPUT_PATH` can be:

- A single `.json` file.
- A directory containing `.json` workflow files (searched recursively).

### Common examples

#### 1. Single workflow file

```bash
python n8n_doc_gen.py workflows/order_processing.json
```

Output (default):

```text
docs_n8n/
  order_processing.md
```

#### 2. Directory of workflows

```bash
python n8n_doc_gen.py workflows/
```

If `workflows/` contains:

```text
workflows/
  order_processing.json
  subflows/
    notify_customer.json
```

Output structure:

```text
docs_n8n/
  order_processing.md
  subflows/
    notify_customer.md
```

The directory structure under `docs_n8n` mirrors the structure under `workflows`.

#### 3. Custom output directory and model

```bash
python n8n_doc_gen.py workflows/ \
  --output-dir n8n_docs \
  --model llama3 \
  --host http://localhost:11434
```

---

## Command-line options

- `input_path` (positional)
  Path to a `.json` file or a directory containing `.json` workflow files.

- `-o`, `--output-dir PATH`
  Root directory where Markdown files will be written.
  Default: `docs_n8n`

- `-m`, `--model NAME`
  Ollama model name to use.
  Default: `llama3.2:1b`

- `--host URL`
  Base URL of the local Ollama server.
  Default: `http://localhost:11434`

- `--dry-run`
  Do not call Ollama and do not write any files.
  Lists the `.json` workflows that would be processed.

- `-v`, `--verbose`
  Enable DEBUG-level logging for detailed diagnostics.

---

## Output structure

For each input JSON file:

- Input:

  - `BASE_INPUT/some/path/workflow.json`
- Output:

  - `OUTPUT_ROOT/some/path/workflow.md`

Where:

- `BASE_INPUT` is:

  - The directory passed as `input_path` if `input_path` is a directory, or
  - The parent directory of the file if `input_path` is a single file.
- `OUTPUT_ROOT` is the resolved `--output-dir`.

If the file cannot be resolved relative to `BASE_INPUT`, the script falls back to a flat output path using only the file name stem.

---

## How it works

### File discovery

- If `input_path` is a file and ends with `.json`, it is processed directly.
- If `input_path` is a directory, the script uses `Path.rglob("*.json")` to find all JSON files recursively.
- Non-JSON files are ignored.

### JSON handling

- Each JSON file is loaded using `json.load`.
- The JSON object is pretty-printed using `json.dumps(..., indent=2, ensure_ascii=False)` to form the prompt body.
- The pretty-printed string is embedded in a fenced ```json block in the user message.

### Ollama request

The script calls:

```text
POST {host}/api/chat
```

With payload:

```json
{
  "model": "<MODEL_NAME>",
  "messages": [
    {
      "role": "system",
      "content": "<SYSTEM_PROMPT>"
    },
    {
      "role": "user",
      "content": "<USER_PROMPT_WITH_JSON>"
    }
  ],
  "stream": false
}
```

Expected response shape:

```json
{
  "message": {
    "content": "<markdown documentation>"
  }
}
```

If `message` or `message.content` is missing, the script raises an error and logs the unexpected response.

### Documentation structure enforced by the system prompt

The system prompt instructs the model to:

- Act as an expert technical writer, systems architect, and diagram designer.
- Produce a single Markdown document with these sections:

1. Title
2. Overview
3. Triggers and entry points
4. Inputs and outputs
5. Node-by-node flow
6. Control flow and logic
7. External integrations
8. Error handling and retries
9. Configuration and deployment notes
10. Security and data protection
11. Limitations and extension points
12. Visual diagrams

Mermaid rules:

- Use valid Mermaid syntax.
- Wrap diagrams in fenced code blocks:

  ````text
  ```mermaid
  flowchart LR
    ...
  ````

  ```
  ```
- Prefer `flowchart LR` for node graphs.
- Labels should be concise and derived from n8n node names or types.

Content rules:

- No functionality invented beyond what the JSON implies.
- Any reasonable inference must be tagged with `[Inference]` by the model.
- No raw JSON in the output.
- No meta commentary about the generation process.

---

## Logging and progress

- Logger name: `n8n-doc-gen`
- Logging backend: `rich.logging.RichHandler` with rich tracebacks.
- Default level: `INFO`
- With `--verbose`: level is set to `DEBUG`.

Typical log messages:

- Discovery:

  - `Found N workflow JSON file(s) to analyze.`
- Per file:

  - `Analyzing workflow: /path/to/file.json`
  - `Markdown description exported: /path/to/output.md`
- Final summary:

  - `Processing complete. Total files: N, succeeded: X, failed: Y`
- Dry run notice:

  - `Dry run mode was enabled. No calls were made to Ollama and no markdown files were written.`

Progress bar:

- Uses `tqdm` with description `"Processing workflows"` and unit `"file"`.

---

## Error handling

- If no `.json` files are found under `input_path`, a warning is logged and the script exits.
- For each file:

  - Any error (invalid JSON, HTTP issues, unexpected response structure, write errors) is logged with full traceback via `logger.exception`.
  - The file is counted as a failure.
- At the end, the script reports the number of succeeded and failed files.

In `--dry-run` mode:

- JSON files are discovered and logged as:

  - `[DRY RUN] Would analyze: /path/to/file.json`
- No network calls are executed.
- No output files are written.

---

## Limitations

- The script treats every `.json` file as a workflow:

  - It does not validate that the JSON is a valid n8n workflow.
- The quality and correctness of the documentation depend on:

  - The selected Ollama model.
  - The model’s adherence to the system prompt.
- Mermaid diagrams are not validated by the script.
- The tool assumes the Ollama API response format described above; different backends or versions that change this format will cause runtime errors.




python .\n8n_doc_gen.py ..\workflows\renamed\<workflow_name.json> -m <model_name>
python .\n8n_doc_gen.py ..\workflows\renamed\Local_RAG_AI_Agent_1.json -m gpt-oss:20b

