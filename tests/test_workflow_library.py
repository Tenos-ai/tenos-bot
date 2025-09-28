from prompt_templates import (
    QWEN_UPSCALE_HELPER_LATENT_NODE,
    QWEN_UPSCALE_LOAD_IMAGE_NODE,
)
from services.workflow_library_service import WorkflowLibraryService
from workflows.workflow_library import load_workflow_catalogue
from workflows.qwen_templates import qwen_upscale_template


def test_workflow_descriptor_returns_fresh_templates():
    catalogue = load_workflow_catalogue()
    assert catalogue, "Expected curated workflow catalogue to be present"

    first_group = catalogue[0]
    assert first_group.workflows, "Expected workflows within the first group"

    descriptor = first_group.workflows[0]

    template_one = descriptor.build_template()
    template_two = descriptor.build_template()

    # Ensure each invocation produces a distinct workflow dictionary so
    # callers can mutate the result without affecting cached state.
    assert template_one is not template_two

    sample_key = next(iter(template_one))
    template_one[sample_key]["_meta"]["title"] = "modified"

    assert template_two[sample_key]["_meta"]["title"] != "modified"


def test_qwen_upscale_uses_standard_nodes():
    template = qwen_upscale_template()

    helper_node = template[str(QWEN_UPSCALE_HELPER_LATENT_NODE)]
    assert helper_node["class_type"] == "BobsLatentNodeAdvanced"
    helper_inputs = helper_node.get("inputs", {})
    assert helper_inputs.get("model_type") == "QWEN"
    assert float(helper_inputs.get("upscale_by", 0)) >= 1.0

    loader_node = template[str(QWEN_UPSCALE_LOAD_IMAGE_NODE)]
    assert loader_node["class_type"] == "LoadImageFromUrlOrPath"
    assert "url_or_path" in loader_node.get("inputs", {})


def test_workflow_search_matches_titles_and_use_cases():
    service = WorkflowLibraryService()

    all_workflows = service.list_workflows()
    assert len(all_workflows) >= 1

    cinematic = service.search_workflows("cinematic")
    assert any("cinematic" in wf.slug for wf in cinematic)

    use_case_matches = service.search_workflows("marketing")
    assert use_case_matches, "Expected use-case search to return results"

    flux_matches = service.search_workflows("flux", group_key="flux")
    assert flux_matches, "Expected Flux group to return workflows when filtered"
