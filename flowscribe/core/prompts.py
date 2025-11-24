"""Prompt handling and building."""
from __future__ import annotations

from dataclasses import dataclass

from ..config.model import PromptConfig
from ..logging import get_logger
from .json_io import WorkflowDocument

logger = get_logger(__name__)


@dataclass(slots=True)
class PromptBundle:
    system: str
    user: str


class PromptBuilder:
    def __init__(self, config: PromptConfig) -> None:
        self.config = config

    def build(self, workflow: WorkflowDocument) -> PromptBundle:
        user_prompt = self.config.user_prompt_template.format(
            filename=workflow.filename, workflow_json=workflow.pretty
        )
        logger.debug("Built user prompt for %s (length=%d)", workflow.filename, len(user_prompt))
        return PromptBundle(system=self.config.system_prompt, user=user_prompt)
