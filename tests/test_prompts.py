from pathlib import Path
from flowscribe.config.model import PromptConfig
from flowscribe.core.json_io import WorkflowDocument
from flowscribe.core.prompts import PromptBuilder


def test_prompt_builder_inserts_fields():
    cfg = PromptConfig(system_prompt="SYS", user_prompt_template="Hello {filename} {workflow_json}")
    wf = WorkflowDocument(path=Path("sample.json"), raw={}, pretty="{}")
    builder = PromptBuilder(cfg)
    bundle = builder.build(wf)
    assert bundle.system == "SYS"
    assert "sample.json" in bundle.user
    assert "{}" in bundle.user
