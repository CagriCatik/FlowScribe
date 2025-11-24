"""Core orchestration engine."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from ..config.model import AppConfig
from ..logging import get_logger
from ..llm.base import LLMClient, LLMGenerationOptions, LLMRequest
from ..llm.ollama_client import OllamaConfig, OllamaLLMClient
from .discovery import DiscoveryError, discover_workflows, filter_selection
from .json_io import JSONLoadError, load_workflow
from .outputs import MarkdownDocument, OutputWriteError, write_markdown
from .prompts import PromptBuilder

logger = get_logger(__name__)


@dataclass(slots=True)
class ProcessResult:
    workflow: Path
    succeeded: bool
    error: Optional[str] = None
    output: Optional[MarkdownDocument] = None


@dataclass(slots=True)
class RunResult:
    total: int
    processed: int
    failed: int
    details: List[ProcessResult]


class WorkflowEngine:
    def __init__(self, config: AppConfig, llm_client: Optional[LLMClient] = None) -> None:
        self.config = config
        self.llm_client = llm_client or self._build_default_client(config.llm.model, config.llm.host)
        self.prompt_builder = PromptBuilder(config.prompts)

    @staticmethod
    def _build_default_client(model: str, host: str) -> LLMClient:
        return OllamaLLMClient(OllamaConfig(host=host, model=model))

    def _build_llm_options(self) -> LLMGenerationOptions:
        opts = self.config.llm.options
        return LLMGenerationOptions(
            num_predict=opts.num_predict,
            temperature=opts.temperature,
            top_p=opts.top_p,
            num_ctx=opts.num_ctx,
            repeat_penalty=opts.repeat_penalty,
        )

    def process_workflow(self, workflow_path: Path, base_input: Path, output_root: Path) -> ProcessResult:
        try:
            workflow = load_workflow(workflow_path)
            prompts = self.prompt_builder.build(workflow)
            if self.config.generation.dry_run:
                logger.info("[DRY RUN] Would analyze: %s", workflow_path)
                return ProcessResult(workflow=workflow_path, succeeded=False)

            result = self.llm_client.generate(
                LLMRequest(system_prompt=prompts.system, user_prompt=prompts.user),
                self._build_llm_options(),
            )
            output_doc = write_markdown(output_root, base_input, workflow_path, result.content)
            return ProcessResult(workflow=workflow_path, succeeded=True, output=output_doc)

        except (JSONLoadError, OutputWriteError, DiscoveryError) as exc:
            logger.exception("Failed processing %s", workflow_path)
            return ProcessResult(workflow=workflow_path, succeeded=False, error=str(exc))
        except Exception as exc:
            logger.exception("Unexpected error processing %s", workflow_path)
            return ProcessResult(workflow=workflow_path, succeeded=False, error=str(exc))

    def run_batch(self, input_path: Path, output_root: Path, selection: Optional[Iterable[Path]] = None) -> RunResult:
        workflows = discover_workflows(input_path)
        workflows = filter_selection(workflows, selection)
        total = len(workflows)
        processed = 0
        failed = 0
        details: List[ProcessResult] = []

        if not workflows:
            raise DiscoveryError("No workflow JSON files found")

        for wf in workflows:
            result = self.process_workflow(wf, base_input=input_path if input_path.is_dir() else input_path.parent, output_root=output_root)
            details.append(result)
            if result.succeeded:
                processed += 1
            else:
                failed += 1
        return RunResult(total=total, processed=processed, failed=failed, details=details)
