"""Regression tests for workflow template wiring."""

import json
import sys
import types
import unittest

if "discord" not in sys.modules:
    discord_stub = types.ModuleType("discord")

    class _DummySelectOption:
        def __init__(self, label=None, value=None, default=None, *args, **kwargs):
            self.label = label
            self.value = value
            self.default = default

    discord_stub.SelectOption = _DummySelectOption
    sys.modules["discord"] = discord_stub

if "numpy" not in sys.modules:
    numpy_stub = types.ModuleType("numpy")

    def _arange(start, stop=None, step=1.0):
        if stop is None:
            stop = float(start)
            start = 0.0
        values = []
        current = float(start)
        step = float(step)
        comparator = (lambda a, b: a < b) if step > 0 else (lambda a, b: a > b)
        while comparator(current, float(stop)) or abs(current - float(stop)) < 1e-9:
            values.append(current)
            current += step
        return values

    numpy_stub.arange = _arange
    sys.modules["numpy"] = numpy_stub

from model_registry import (
    MODEL_REGISTRY,
    copy_generation_template,
    copy_variation_template,
    copy_upscale_template,
    copy_animation_template,
    resolve_model_type_from_prefix,
)
import prompt_templates
from qwen_editing import (
    modify_qwen_edit_prompt,
    QWEN_EDIT_SAMPLING_NODE,
    QWEN_POS_PROMPT_NODE,
)


def _contains_class(template: dict, class_name: str) -> bool:
    """Return True if any node in the template uses the given class."""
    for node in template.values():
        if isinstance(node, dict) and node.get("class_type") == class_name:
            return True
    return False


class WorkflowTemplateTests(unittest.TestCase):
    """Validate that shared workflow requirements stay present."""

    def test_generation_templates_include_latent_helper(self) -> None:
        for key, spec in MODEL_REGISTRY.items():
            with self.subTest(model=key, flow="text2img"):
                template = copy_generation_template(spec.generation, is_img2img=False)
                if key == "wan":
                    self.assertTrue(
                        _contains_class(template, "WanVideoEmptyEmbeds"),
                        msg="WAN generation template must seed a WanVideoEmptyEmbeds node",
                    )
                else:
                    self.assertTrue(
                        _contains_class(template, "BobsLatentNodeAdvanced"),
                        msg=f"{key} generation template lost the Bob's latent helper",
                    )

    def test_img2img_templates_include_tenos_resize(self) -> None:
        for key, spec in MODEL_REGISTRY.items():
            with self.subTest(model=key, flow="img2img"):
                template = copy_generation_template(spec.generation, is_img2img=True)
                self.assertTrue(
                    _contains_class(template, "TenosResizeToTargetPixels"),
                    msg=f"{key} img2img template missing Tenos resize node",
                )

    def test_variation_templates_include_tenos_resize(self) -> None:
        for key, spec in MODEL_REGISTRY.items():
            for strength, template in spec.variation.templates.items():
                with self.subTest(model=key, flow=f"variation:{strength}"):
                    self.assertTrue(
                        _contains_class(template, "TenosResizeToTargetPixels"),
                        msg=(
                            f"{key} variation template '{strength}' missing Tenos resize node"
                        ),
                    )

    def test_upscale_templates_include_bobs_helper(self) -> None:
        for key, spec in MODEL_REGISTRY.items():
            with self.subTest(model=key, flow="upscale"):
                if spec.upscale is None:
                    self.assertEqual(
                        key,
                        "wan",
                        msg="Only WAN should omit an upscale template",
                    )
                    continue
                template = copy_upscale_template(spec.upscale)
                self.assertTrue(
                    _contains_class(template, "BobsLatentNodeAdvanced"),
                    msg=f"{key} upscale template missing Bob's latent helper",
                )

    def test_upscale_templates_wire_helper_outputs(self) -> None:
        for key, spec in MODEL_REGISTRY.items():
            with self.subTest(model=key, flow="upscale-helper-wiring"):
                if spec.upscale is None:
                    self.assertEqual(key, "wan")
                    continue

                template = copy_upscale_template(spec.upscale)
                upscale_node_key = spec.upscale.upscale_node
                helper_node_key = spec.upscale.helper_latent_node
                upscale_node = template.get(upscale_node_key, {})
                helper_refs = {
                    "tile_width": [helper_node_key, 1],
                    "tile_height": [helper_node_key, 2],
                    "upscale_by": [helper_node_key, 3],
                }

                inputs = upscale_node.get("inputs", {})
                for field, expected in helper_refs.items():
                    self.assertEqual(
                        inputs.get(field),
                        expected,
                        msg=f"{key} upscale '{field}' should reference {expected}",
                    )

                self.assertEqual(
                    inputs.get("mode_type"),
                    "linear",
                    msg=f"{key} upscale should default to linear blending mode",
                )

    def test_upscale_templates_match_primary_sampler(self) -> None:
        for key, spec in MODEL_REGISTRY.items():
            with self.subTest(model=key, flow="upscale-sampler-sync"):
                if spec.upscale is None:
                    self.assertEqual(key, "wan")
                    continue

                upscale_template = copy_upscale_template(spec.upscale)
                gen_template = copy_generation_template(spec.generation, is_img2img=False)
                upscale_inputs = upscale_template[spec.upscale.upscale_node]["inputs"]
                ksampler_inputs = gen_template[spec.generation.ksampler_node]["inputs"]

                for field in ("sampler_name", "scheduler", "cfg"):
                    self.assertEqual(
                        upscale_inputs.get(field),
                        ksampler_inputs.get(field),
                        msg=(
                            f"{key} upscale {field} ({upscale_inputs.get(field)}) "
                            f"should match generation KSampler ({ksampler_inputs.get(field)})"
                        ),
                    )

    def test_qwen_edit_template_uses_tenos_resize(self) -> None:
        self.assertTrue(
            _contains_class(prompt_templates.qwen_edit_prompt, "TenosResizeToTargetPixels"),
            msg="Qwen edit prompt must pass through Tenos resize",
        )
        sampling_inputs = prompt_templates.qwen_edit_prompt[str(prompt_templates.QWEN_EDIT_SAMPLING_NODE)]["inputs"]
        self.assertEqual(
            sampling_inputs.get("cfg_rescale"),
            1.0,
            msg="Qwen edit sampling node should default cfg_rescale to 1.0",
        )

    def test_animation_flag_present_for_wan_only(self) -> None:
        self.assertTrue(
            MODEL_REGISTRY["wan"].supports_animation,
            "WAN should be flagged as animation-capable",
        )
        for key, spec in MODEL_REGISTRY.items():
            if key == "wan":
                continue
            with self.subTest(model=key):
                self.assertFalse(
                    spec.supports_animation,
                    msg=f"{key} should not be marked animation-capable by default",
                )

    def test_qwen_templates_include_loader_nodes(self) -> None:
        qwen_spec = MODEL_REGISTRY["qwen"]
        gen_template = copy_generation_template(qwen_spec.generation, is_img2img=False)
        self.assertTrue(_contains_class(gen_template, "UNETLoader"))
        self.assertTrue(_contains_class(gen_template, "CLIPLoader"))
        self.assertTrue(_contains_class(gen_template, "VAELoader"))

        var_template = copy_variation_template(qwen_spec.variation)
        self.assertTrue(_contains_class(var_template, "UNETLoader"))
        self.assertTrue(_contains_class(var_template, "CLIPLoader"))
        self.assertTrue(_contains_class(var_template, "VAELoader"))

        upscale_template = copy_upscale_template(qwen_spec.upscale)
        self.assertTrue(_contains_class(upscale_template, "UNETLoader"))
        self.assertTrue(_contains_class(upscale_template, "CLIPLoader"))
        self.assertTrue(_contains_class(upscale_template, "VAELoader"))

        img2img_template = copy_generation_template(qwen_spec.generation, is_img2img=True)
        sampling_inputs = img2img_template[str(prompt_templates.QWEN_SAMPLING_NODE)]["inputs"]
        self.assertNotIn(
            "clip",
            sampling_inputs,
            msg="Qwen img2img sampling node should no longer take a direct clip input",
        )
        self.assertEqual(
            sampling_inputs.get("model"),
            [str(prompt_templates.QWEN_LORA_NODE), 0],
            msg="Qwen img2img sampling node must still receive the LoRA model output",
        )
        self.assertNotIn(
            "cfg_rescale",
            sampling_inputs,
            msg="Qwen img2img sampling node should no longer define cfg_rescale",
        )
        self.assertEqual(
            sampling_inputs.get("shift"),
            0.0,
            msg="Qwen img2img sampling node should seed shift to 0.0",
        )

        pos_prompt_inputs = img2img_template[str(prompt_templates.QWEN_POS_PROMPT_NODE)]["inputs"]
        self.assertEqual(
            pos_prompt_inputs.get("clip"),
            [str(prompt_templates.QWEN_LORA_NODE), 1],
            msg="Qwen positive prompt must continue to consume the LoRA clip output",
        )

    def test_wan_templates_use_video_wrapper_nodes(self) -> None:
        wan_spec = MODEL_REGISTRY["wan"]

        gen_template = copy_generation_template(wan_spec.generation, is_img2img=False)
        self.assertTrue(_contains_class(gen_template, "WanVideoModelLoader"))
        self.assertTrue(_contains_class(gen_template, "LoadWanVideoT5TextEncoder"))
        self.assertTrue(_contains_class(gen_template, "WanVideoVAELoader"))
        self.assertTrue(_contains_class(gen_template, "WanVideoEmptyEmbeds"))
        loader_inputs = gen_template[str(prompt_templates.WAN_MODEL_LOADER_NODE)]["inputs"]
        self.assertEqual(
            loader_inputs.get("model"),
            "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors",
            msg="WAN t2v workflow should default to the WAN 2.2 high-noise 14B checkpoint",
        )
        self.assertEqual(loader_inputs.get("base_precision"), "fp16_fast")
        self.assertEqual(loader_inputs.get("quantization"), "fp8_e4m3fn_scaled")
        self.assertEqual(loader_inputs.get("attention_mode"), "sageattn")
        t5_inputs = gen_template[str(prompt_templates.WAN_T5_LOADER_NODE)]["inputs"]
        self.assertEqual(
            t5_inputs.get("model_name"),
            "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
            msg="WAN workflows should load the fp8 WAN 2.2 text encoder by default",
        )
        vae_inputs = gen_template[str(prompt_templates.WAN_VAE_LOADER_NODE)]["inputs"]
        self.assertEqual(
            vae_inputs.get("model_name"),
            "wan2.2_vae.safetensors",
            msg="WAN workflows should load the WAN 2.2 VAE by default",
        )
        sampler_inputs = gen_template[str(prompt_templates.WAN_SAMPLER_NODE)]["inputs"]
        self.assertEqual(
            sampler_inputs.get("model"),
            [str(prompt_templates.WAN_MODEL_LOADER_NODE), 0],
            msg="WAN sampler should consume the WanVideoModelLoader output",
        )
        self.assertEqual(
            sampler_inputs.get("image_embeds"),
            [str(prompt_templates.WAN_IMAGE_EMBEDS_NODE), 0],
            msg="WAN sampler should consume the WanVideoEmptyEmbeds output",
        )
        self.assertEqual(
            sampler_inputs.get("text_embeds"),
            [str(prompt_templates.WAN_TEXT_ENCODER_NODE), 0],
            msg="WAN sampler should consume the WanVideoTextEncode output",
        )
        self.assertEqual(
            sampler_inputs.get("denoise_strength"),
            1.0,
            msg="WAN sampler should default denoise strength to 1.0",
        )
        self.assertNotIn(
            "samples",
            sampler_inputs,
            msg="Text-to-video template should not attach latent samples to the sampler",
        )

        img2img_template = copy_generation_template(wan_spec.generation, is_img2img=True)
        encode_node_id = str(prompt_templates.WAN_IMAGE_ENCODE_NODE)
        img_loader_inputs = img2img_template[str(prompt_templates.WAN_MODEL_LOADER_NODE)]["inputs"]
        self.assertEqual(
            img_loader_inputs.get("model"),
            "wan2.2_i2v_high_noise_14B_fp16.safetensors",
            msg="WAN img2img workflow should default to the WAN 2.2 i2v high-noise checkpoint",
        )
        self.assertEqual(img_loader_inputs.get("base_precision"), "fp16_fast")
        self.assertEqual(img_loader_inputs.get("quantization"), "disabled")
        self.assertEqual(img_loader_inputs.get("attention_mode"), "sageattn")
        img_sampler_inputs = img2img_template[str(prompt_templates.WAN_SAMPLER_NODE)]["inputs"]
        self.assertEqual(
            img_sampler_inputs.get("samples"),
            [encode_node_id, 0],
            msg="WAN img2img sampler should consume the WanVideoEncode output",
        )
        embeds_inputs = img2img_template[str(prompt_templates.WAN_IMAGE_EMBEDS_NODE)]["inputs"]
        self.assertEqual(
            embeds_inputs.get("extra_latents"),
            [encode_node_id, 0],
            msg="WAN img2img embeds should forward the encoded latent",
        )

        var_template = copy_variation_template(wan_spec.variation)
        self.assertTrue(_contains_class(var_template, "WanVideoEncode"))
        var_sampler_inputs = var_template[str(prompt_templates.WAN_SAMPLER_NODE)]["inputs"]
        self.assertEqual(
            var_sampler_inputs.get("samples"),
            [encode_node_id, 0],
            msg="WAN variation sampler should reuse the encoded latent",
        )

        anim_template = copy_animation_template(wan_spec)
        anim_sampler_inputs = anim_template[str(prompt_templates.WAN_SAMPLER_NODE)]["inputs"]
        self.assertEqual(
            anim_sampler_inputs.get("samples"),
            [encode_node_id, 0],
            msg="WAN animation sampler should consume the WanVideoEncode output",
        )
        anim_embed_inputs = anim_template[str(prompt_templates.WAN_IMAGE_EMBEDS_NODE)]["inputs"]
        self.assertEqual(
            anim_embed_inputs.get("extra_latents"),
            [encode_node_id, 0],
            msg="WAN animation embeds should include the encoded latent",
        )

    def test_qwen_edit_falls_back_when_lora_missing(self) -> None:
        original_template = prompt_templates.qwen_edit_prompt
        qwen_module = None
        try:
            patched_template = json.loads(json.dumps(original_template))
            patched_template.pop(str(prompt_templates.QWEN_LORA_NODE), None)
            prompt_templates.qwen_edit_prompt = patched_template
            import qwen_editing as qwen_module  # type: ignore
            qwen_module.qwen_edit_prompt = patched_template

            settings = {
                "default_qwen_checkpoint": "qwen_image_fp8_e4m3fn.safetensors",
                "default_qwen_clip": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                "default_qwen_vae": "qwen_image_vae.safetensors",
            }

            _, workflow, _, _ = modify_qwen_edit_prompt(
                image_urls=["https://example.com/test.png"],
                instruction="make it brighter",
                user_settings=settings,
                base_seed=42,
                steps_override=20,
                guidance_override=5.5,
                denoise_override=0.6,
                cfg_rescale_override=1.0,
            )

            sampling_inputs = workflow[str(QWEN_EDIT_SAMPLING_NODE)]["inputs"]
            self.assertEqual(
                sampling_inputs.get("model"),
                [str(prompt_templates.QWEN_UNET_LOADER_NODE), 0],
            )
            self.assertNotIn(
                "clip",
                sampling_inputs,
                msg="Qwen edit sampling node should not require a clip input",
            )

            pos_inputs = workflow[str(QWEN_POS_PROMPT_NODE)]["inputs"]
            self.assertEqual(
                pos_inputs.get("clip"),
                [str(prompt_templates.QWEN_CLIP_LOADER_NODE), 0],
            )
        finally:
            prompt_templates.qwen_edit_prompt = original_template
            if qwen_module is not None:
                qwen_module.qwen_edit_prompt = original_template


class ModelTypeResolutionTests(unittest.TestCase):
    """Ensure model type resolution works for prefixed and legacy names."""

    def test_qwen_filename_without_prefix_maps_to_qwen(self) -> None:
        model_type, actual = resolve_model_type_from_prefix("qwen_image_fp8_e4m3fn.safetensors")
        self.assertEqual(model_type, "qwen")
        self.assertEqual(actual, "qwen_image_fp8_e4m3fn.safetensors")

    def test_wan_filename_without_prefix_maps_to_wan(self) -> None:
        model_type, actual = resolve_model_type_from_prefix("wan2.2_t2v_low_noise_14b_fp8_scaled.safetensors")
        self.assertEqual(model_type, "wan")
        self.assertEqual(actual, "wan2.2_t2v_low_noise_14b_fp8_scaled.safetensors")

    def test_path_components_are_considered_for_family_detection(self) -> None:
        model_type, actual = resolve_model_type_from_prefix("C:/models/QWEN/qwen_image_fp8_e4m3fn.safetensors")
        self.assertEqual(model_type, "qwen")
        self.assertEqual(actual, "C:/models/QWEN/qwen_image_fp8_e4m3fn.safetensors")

    def test_default_to_sdxl_when_no_family_hint_present(self) -> None:
        model_type, actual = resolve_model_type_from_prefix("sdxl_base_1.0.safetensors")
        self.assertEqual(model_type, "sdxl")
        self.assertEqual(actual, "sdxl_base_1.0.safetensors")

    def test_flux_extensions_remain_supported(self) -> None:
        model_type, actual = resolve_model_type_from_prefix("flux1-dev.sft")
        self.assertEqual(model_type, "flux")
        self.assertEqual(actual, "flux1-dev.sft")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
