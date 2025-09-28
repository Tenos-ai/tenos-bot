import unittest

from qwen_editing import modify_qwen_edit_prompt


class ModifyQwenEditPromptTests(unittest.TestCase):
    def test_requires_single_image(self):
        job_id, workflow, message, details = modify_qwen_edit_prompt(
            image_urls=[],
            instruction="paint the sky",
            user_settings={},
            base_seed=42,
            steps_override=25,
            guidance_override=5.5,
            denoise_override=0.5,
        )
        self.assertIsNone(job_id)
        self.assertIsNone(workflow)
        self.assertIn("At least one reference image", message)
        self.assertIsNone(details)

    def test_rejects_multiple_images(self):
        job_id, workflow, message, details = modify_qwen_edit_prompt(
            image_urls=["path1", "path2"],
            instruction="swap background",
            user_settings={"preferred_model_qwen": "Qwen: local.ckpt"},
            base_seed=7,
            steps_override=20,
            guidance_override=4.0,
            denoise_override=0.4,
        )
        self.assertIsNone(job_id)
        self.assertIsNone(workflow)
        self.assertIn("single base image", message)
        self.assertIsNone(details)

    def test_builds_qwen_workflow(self):
        settings = {"preferred_model_qwen": "Qwen: demo.ckpt", "default_qwen_negative_prompt": "low quality"}
        job_id, workflow, message, details = modify_qwen_edit_prompt(
            image_urls=["/tmp/image.png"],
            instruction="brighten the portrait",
            user_settings=settings,
            base_seed=99,
            steps_override=33,
            guidance_override=6.7,
            denoise_override=0.55,
        )
        self.assertIsNotNone(job_id)
        self.assertIsInstance(workflow, dict)
        ckpt_inputs = workflow["qwen_ckpt"]["inputs"]
        self.assertEqual(ckpt_inputs["ckpt_name"], "demo.ckpt")
        sampler_inputs = workflow["qwen_ksampler"]["inputs"]
        self.assertEqual(sampler_inputs["seed"], 99)
        self.assertEqual(sampler_inputs["steps"], 33)
        self.assertAlmostEqual(sampler_inputs["denoise"], 0.55)
        pos_inputs = workflow["qwen_pos_prompt"]["inputs"]
        self.assertIn("brighten", pos_inputs["text"])
        neg_inputs = workflow["qwen_neg_prompt"]["inputs"]
        self.assertEqual(neg_inputs["text"], "low quality")
        filename_prefix = workflow["qwen_save"]["inputs"]["filename_prefix"]
        self.assertIn("QWEN_EDIT_", filename_prefix)
        self.assertEqual(details["qwen_model_used"], "demo.ckpt")
        self.assertEqual(details["model_type_for_enhancer"], "qwen_edit")


if __name__ == "__main__":
    unittest.main()
