"""Typed configuration models for FlowScribe."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

DEFAULT_SYSTEM_PROMPT = (
    "You are an expert technical writer, systems architect, and diagram designer.\n"
    "Your job is to read n8n workflow JSON definitions and produce precise, implementation-level documentation for engineers.\n\n"
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
    "- Use valid Mermaid syntax. When parentheses are used, ensure that \"\" are placed around their contents.\n"
    "- Wrap each diagram in a fenced Markdown code block: ```mermaid on its own line, then the diagram, then ``` on its own line.\n"
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

DEFAULT_USER_PROMPT = """You are given an n8n workflow JSON definition.

Using only the information in this JSON and following your system instructions,
generate the complete Markdown documentation for this workflow, including the
required Mermaid diagram(s) in the Visual diagrams section.

Workflow file name: {filename}

Here is the JSON:

```json
{workflow_json}
```"""


@dataclass(slots=True)
class PathsConfig:
    input_path: Optional[Path] = None
    output_dir: Path = Path("generated")


@dataclass(slots=True)
class PromptConfig:
    profile: str = "n8n-doc"
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    user_prompt_template: str = DEFAULT_USER_PROMPT


@dataclass(slots=True)
class GenerationConfig:
    dry_run: bool = False
    verbose: bool = False


@dataclass(slots=True)
class LLMOptions:
    num_predict: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    num_ctx: Optional[int] = None
    repeat_penalty: Optional[float] = None


@dataclass(slots=True)
class LLMConfig:
    host: str = "http://localhost:11434"
    model: str = "llama3.2:1b"
    options: LLMOptions = field(default_factory=LLMOptions)


@dataclass(slots=True)
class AppConfig:
    paths: PathsConfig = field(default_factory=PathsConfig)
    prompts: PromptConfig = field(default_factory=PromptConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)

    def merge(self, other: "AppConfig") -> "AppConfig":
        """Merge another config into this one, overriding where values are provided."""

        merged = AppConfig(
            paths=PathsConfig(
                input_path=other.paths.input_path or self.paths.input_path,
                output_dir=other.paths.output_dir or self.paths.output_dir,
            ),
            prompts=PromptConfig(
                profile=other.prompts.profile or self.prompts.profile,
                system_prompt=other.prompts.system_prompt or self.prompts.system_prompt,
                user_prompt_template=other.prompts.user_prompt_template
                or self.prompts.user_prompt_template,
            ),
            generation=GenerationConfig(
                dry_run=other.generation.dry_run or self.generation.dry_run,
                verbose=other.generation.verbose or self.generation.verbose,
            ),
            llm=LLMConfig(
                host=other.llm.host or self.llm.host,
                model=other.llm.model or self.llm.model,
                options=LLMOptions(
                    num_predict=other.llm.options.num_predict
                    if other.llm.options.num_predict is not None
                    else self.llm.options.num_predict,
                    temperature=other.llm.options.temperature
                    if other.llm.options.temperature is not None
                    else self.llm.options.temperature,
                    top_p=other.llm.options.top_p
                    if other.llm.options.top_p is not None
                    else self.llm.options.top_p,
                    num_ctx=other.llm.options.num_ctx
                    if other.llm.options.num_ctx is not None
                    else self.llm.options.num_ctx,
                    repeat_penalty=other.llm.options.repeat_penalty
                    if other.llm.options.repeat_penalty is not None
                    else self.llm.options.repeat_penalty,
                ),
            ),
        )
        return merged
