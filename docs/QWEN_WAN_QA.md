# Qwen Image & WAN 2.2 QA Checklist

Use this checklist after updating the bot or ComfyUI workflows to ensure the new model families stay healthy.

## Pre-flight

1. Verify the Qwen and WAN checkpoints are present inside the paths configured in the Configurator (`Main Config -> Models`).
2. Confirm the following custom nodes load without runtime errors when ComfyUI starts:
   - `BobsLatentNodeAdvanced` (from BobsBlazed/Bobs_Latent_Optimizer)
   - `TenosResizeToTargetPixels` (from Tenos-ai/Tenos-Resize-to-1-M-Pixels)
   - `ModelSamplingAuraFlow` (bundled with recent ComfyUI builds)
   - `ModelSamplingSD3` (bundled with the WAN 2.2 release package)
3. Launch the Discord bot and ensure `/settings` displays Qwen Image and WAN 2.2 in the model dropdown.

## Qwen Image validation

1. Queue `/gen` with a Qwen Image model selected and confirm the job completes.
2. Inspect the `🧠 Enhancer` field in the queue log—verify it shows the Qwen-specific enhancer label when enabled.
3. Trigger an Img2Img remix with Qwen (`--img` option or `Vary` button) and check the resize node log mentions "Tenos Resize".
4. Run `/edit` against an existing asset and ensure the edit preview respects the Tenos resize dimensions.

## WAN 2.2 validation

1. Queue `/gen` with a WAN 2.2 model and confirm the completion message highlights the animation-ready badge.
2. Click the `🎞️` button on the generation result and ensure the follow-up job enqueues successfully.
3. Execute a WAN variation (`Vary W`/`Vary S`) and confirm the job metadata shows `ModelSamplingSD3` in the ComfyUI log.
4. Upscale the WAN output with `--up` and verify the Bob's latent helper parameters display the WAN family label.

## Regression spot-checks

1. Switch back to Flux or SDXL models and verify `/gen`, variation, and `--up` still succeed.
2. Confirm that WAN and Qwen defaults persist after restarting the bot by reopening `/settings` and the Configurator.
3. Check that completed jobs write metadata files to the expected output folder for all four model families.

Document any failures along with the ComfyUI console output to speed up debugging.
