import asyncio
import types

import pytest

pytest.importorskip("discord")

from bot_ui_components import GenerationActionsView, queue_manager


class DummyResponse:
    def __init__(self):
        self._done = False

    def is_done(self):
        return self._done

    async def defer(self, **kwargs):
        self._done = True


class DummyInteraction:
    def __init__(self):
        self.response = DummyResponse()


class DummyMessage:
    def __init__(self, message_id=123, channel_id=456):
        self.id = message_id
        self.channel = types.SimpleNamespace(id=channel_id)


class DummyWebsocketClient:
    def __init__(self):
        self.is_connected = False

    async def register_prompt(self, *args, **kwargs):
        return None


@pytest.fixture(autouse=True)
def _event_loop_fixture():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield loop
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        asyncio.set_event_loop(None)


def _patch_queue_lookup(monkeypatch, job_payload):
    monkeypatch.setattr(queue_manager, "get_job_data_by_id", lambda _job_id: job_payload)


def _create_view(loop, job_id):
    holder = {}

    async def _runner():
        holder["view"] = GenerationActionsView(111, 222, job_id, bot_ref=None)

    loop.run_until_complete(_runner())
    return holder["view"]


def test_generation_actions_view_shows_animation_button_for_single_image(monkeypatch, _event_loop_fixture):
    job_payload = {
        "type": "generate",
        "supports_animation": False,
        "followup_animation_workflow": None,
        "batch_size": 1,
        "image_paths": ["result.png"],
    }
    _patch_queue_lookup(monkeypatch, job_payload)
    view = _create_view(_event_loop_fixture, "job-single")
    animate_buttons = [btn for btn in view.children if getattr(btn, "custom_id", "").startswith("animate_")]
    assert len(animate_buttons) == 1
    assert animate_buttons[0].label == "🎞️"


def test_generation_actions_view_hides_animation_button_for_batches(monkeypatch, _event_loop_fixture):
    job_payload = {
        "type": "generate",
        "supports_animation": False,
        "followup_animation_workflow": None,
        "batch_size": 3,
        "image_paths": ["one.png", "two.png", "three.png"],
    }
    _patch_queue_lookup(monkeypatch, job_payload)
    view = _create_view(_event_loop_fixture, "job-batch")
    assert all(not getattr(btn, "custom_id", "").startswith("animate_") for btn in view.children)


def test_generation_actions_view_hides_animation_button_for_animation_jobs(monkeypatch, _event_loop_fixture):
    job_payload = {
        "type": "wan_animation",
        "batch_size": 1,
        "image_paths": ["clip.mp4"],
    }
    _patch_queue_lookup(monkeypatch, job_payload)
    view = _create_view(_event_loop_fixture, "job-wan-animation")
    assert all(not getattr(btn, "custom_id", "").startswith("animate_") for btn in view.children)


def test_process_action_results_includes_animation_note(monkeypatch, _event_loop_fixture):
    job_payload = {
        "type": "generate",
        "supports_animation": False,
        "followup_animation_workflow": None,
        "batch_size": 1,
        "image_paths": ["final.png"],
    }
    _patch_queue_lookup(monkeypatch, job_payload)

    captured_messages = []

    async def fake_safe_interaction_response(interaction, content, view=None, ephemeral=False, files=None):
        captured_messages.append(content)
        return DummyMessage()

    added_jobs = []

    def fake_add_job(job_id, data):
        added_jobs.append((job_id, data))

    monkeypatch.setattr("bot_ui_components.safe_interaction_response", fake_safe_interaction_response)
    monkeypatch.setattr(queue_manager, "add_job", fake_add_job)
    monkeypatch.setattr("bot_ui_components.WebsocketClient", DummyWebsocketClient)

    view = _create_view(_event_loop_fixture, "job-single")
    interaction = DummyInteraction()

    animation_result = [{
        "status": "success",
        "message_content_details": {
            "user_mention": "@user",
            "prompt_to_display": "A scenic vista",
            "seed": 42,
            "style": "default",
            "aspect_ratio": "1:1",
            "steps": 30,
            "guidance_display_label": "Guidance",
            "guidance_display_value": 3.5,
            "mp_size": "1x",
            "is_img2img": False,
            "img_strength_percent": 0,
            "negative_prompt": None,
            "supports_animation": True,
            "followup_animation_workflow": None,
        },
        "job_data_for_qm": {"type": "generate"},
        "job_id": "job-single",
        "view_type": None,
        "view_args": None,
        "comfy_prompt_id": None,
    }]

    _event_loop_fixture.run_until_complete(view._process_and_send_action_results(interaction, animation_result, "Generate"))
    assert any("wan_image_to_video" in message for message in captured_messages)

    captured_messages.clear()
    no_animation_result = [{
        "status": "success",
        "message_content_details": {
            "user_mention": "@user",
            "prompt_to_display": "A scenic vista",
            "seed": 42,
            "style": "default",
            "aspect_ratio": "1:1",
            "steps": 30,
            "guidance_display_label": "Guidance",
            "guidance_display_value": 3.5,
            "mp_size": "1x",
            "is_img2img": False,
            "img_strength_percent": 0,
            "negative_prompt": None,
            "supports_animation": False,
            "followup_animation_workflow": None,
        },
        "job_data_for_qm": {"type": "generate"},
        "job_id": "job-single",
        "view_type": None,
        "view_args": None,
        "comfy_prompt_id": None,
    }]

    _event_loop_fixture.run_until_complete(view._process_and_send_action_results(interaction, no_animation_result, "Generate"))
    assert all("**Animate:**" not in message for message in captured_messages)
    assert added_jobs  # ensure queue manager received the job payload
