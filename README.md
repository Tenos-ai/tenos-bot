# Tenosai-Bot: ComfyUI API Discord Bot for Flux & SDXL Image Generation
|||
|---|---|
|![Screenshot 2025-06-25 191115](https://github.com/user-attachments/assets/3708790d-1bc8-49cf-aca1-465b739dd0d8)|![Screenshot 2025-06-25 191205](https://github.com/user-attachments/assets/11efb49e-e66d-4748-8d0d-f6980288ad66)|
|![Screenshot 2025-06-25 190919](https://github.com/user-attachments/assets/a6029416-32c5-45b6-906b-5985e1eaef6b)|![Screenshot 2025-06-25 190957](https://github.com/user-attachments/assets/d5edf35e-bec3-4da5-9b09-da7d2393c481)

## First-Time Setup

**(IF YOU DO NOT HAVE A DISCORD BOT ACCOUNT ALREADY CREATED, OPEN "HOW TO DISCORD BOT.txt" AND FOLLOW INSTRUCTIONS)**

Make sure you already have ComfyUI installed. If you need ComfyUI still download it [`HERE`](https://www.comfy.org/download).

Download the portable zip from github via the code button at the top of the model page or click [`HERE`](https://github.com/Tenos-ai/tenos-bot/archive/refs/heads/main.zip) to download the zip. I reccomend placing it in your ComfyUI Portable folder but you can put it anywhere and it should work just fine.

  - The bot requires specific custom nodes. You can install them manually by cloning the following GitHub repositories into your `ComfyUI/custom_nodes` folder, or use the Configurator's "Install/Update Custom Nodes" tool:
      1. `https://github.com/rgthree/rgthree-comfy.git`
      2. `https://github.com/ssitu/ComfyUI_UltimateSDUpscale.git`
      3. `https://github.com/jamesWalker55/comfyui-various.git`
      4. `https://github.com/city96/ComfyUI-GGUF.git`
      5. `https://github.com/tsogzark/ComfyUI-load-image-from-url.git`
      6. `https://github.com/BobsBlazed/Bobs_Latent_Optimizer.git`
      7. `https://github.com/Tenos-ai/Tenos-Resize-to-1-M-Pixels.git`

Before using Tenosai-Bot, you **MUST** run the configurator (`TENOSAI-BOT.bat` or by executing `python config-editor-script.py`) to:

- **Map all necessary file paths** (Outputs, Models, CLIPs, LoRAs, Custom Nodes) under the "Main Config" tab.
- **Input your unique Discord bot token** into the `BOT_API` -> `KEY` field in "Main Config".
- **Input the admin's Discord username** into the `ADMIN` -> `USERNAME` field in "Main Config".
- **Optionally input API Keys** for Google Gemini, Groq, and/or OpenAI in the `LLM_ENHANCER` section of "Main Config" if you plan to use the LLM Prompt Enhancer feature (see `/settings` and the "LLM Prompts" tab in the Configurator).

This step is crucial for the bot to function correctly. After initial setup, use the "Bot Control" tab in the configurator to start the bot. The bot uses the model selected via `/settings` or the Configurator as the default for new generations.

OPTIONAL: download the Tenos Official Flux Dev Finetune from Huggingface [`HERE`](https://huggingface.co/Tenos-ai/Tenos)

## Commands and Features

### 1. Image Generation
Commands: `/gen` or `/please`
Usage: `/gen [prompt] [options]` or `/please [prompt] [options]`

Options:
- `--seed [number]`: Set a specific seed for reproducibility.
- `--g [number]`: Set guidance scale for **Flux** models (e.g., `3.5`). Default in `/settings`.
- `--g_sdxl [number]`: Set guidance scale for **SDXL** models (e.g., `7.0`). Default in `/settings`.
- `--ar [W:H]`: Set aspect ratio (e.g., `--ar 16:9`). Default is `1:1`.
- `--mp [M]`: (Flux & SDXL) Set Megapixel target size (e.g., `0.5`, `1`, `1.75`). Default in `/settings`.
- `--img [strength] [URL]`: **(Flux Only)** Use img2img. Strength `S` (0-100), `URL` of input image.
- `--style [style_name]`: Apply a predefined LoRA style (see `/styles`). Default in `/settings`.
- `--r [N]`: Run the prompt `N` times with different seeds (max 10).
- `--no "[negative_prompt_text]"`: **(SDXL Only)** Provide a negative prompt.
    - For initial `/gen` or `/please`: If used, this text will be appended to your default SDXL negative prompt (set via `/settings` or Configurator). To use *only* your typed negative prompt, or an empty one for the initial generation, use ` --no ""` or just `--no`.
    - For derivative actions (Edit modal, Remix modal, `--no` in replies for Variations): The provided text *replaces* any previous negative prompt.

Example: `/gen a majestic lion --ar 16:9 --seed 1234 --style realistic --g_sdxl 6.5`
Example (SDXL with custom negative): `/gen cyberpunk city --no "trees, nature, day"`

**Optional LLM Prompt Enhancer:**
- An admin can enable an optional prompt enhancer via `/settings`.
- If enabled (and the corresponding API Key is configured), your initial prompt may be automatically rewritten by the selected LLM (Google Gemini, Groq, or OpenAI) to be more descriptive before generation. This applies to both Flux and SDXL, using different system prompts.
- Generated messages will have a ✨ icon if the enhancer was used successfully.
- Configure the LLM provider and specific model via `/settings`.
- Edit the system prompts used by the enhancer via the Configurator's "LLM Prompts" tab.

### 2. Image Upscaling
Command: Reply with `--up` or click the ⬆️ button.
Usage: Reply to a generated image with `--up [options]` or click the button.

Options (for reply command):
- `--seed [number]`: Set a specific seed for the upscale.
- `--style [style_name]`: Apply a different style during the upscale process.

Example (replying to an image): `--up --seed 5678 --style detailed`

### 3. Image Variation
Command: Reply with `--vary [type]` or click the 🤏 (Weak) / 💪 (Strong) buttons.
Usage: Reply to a generated image with `--vary [type] [options]` or click the button.

Types:
- `w`: Weak variation (subtle changes, lower denoise)
- `s`: Strong variation (significant changes, higher denoise)

Options (for reply command):
- `--noprompt`: Generate variation with a blank prompt (uses image context only).
- `--prompt "[new_prompt]"`: If Remix Mode is ON (via `/settings`), use this new prompt for the variation. Enclose multi-word prompts in quotes.
- `--no "[negative_prompt_text]"`: **(SDXL Variation Only)** Sets/replaces the negative prompt for this variation.
- `--style [style_name]`: Apply a different style to the variation.

Example: `--vary s --prompt "a lion in a jungle" --style cartoon` (*If Remix Mode ON*)
Example (SDXL): `--vary w --no "blurry"`

**Remix Mode:**
- If "Variation Remix Mode" is ON (via `/settings`), clicking a Vary button (🤏/💪) or replying with just `--vary w/s` (without `--prompt`) will open a modal. This modal allows you to edit the positive prompt (and negative prompt for SDXL variations) before generating the variation.

### 4. Rerunning & Editing Prompts
- **Rerun Button 🔄 / Reply `--r [N]`**: Reruns the *original unenhanced prompt* and parameters of a generation with a new seed. `N` for multiple runs. The negative prompt used will be the one from the original generation (not re-combined with defaults).
- **Edit Button ✏️**: Opens a modal to edit the full original prompt string (including parameters like seed, style, AR, `--no`, etc.). The edited prompt is then processed as if it were a new `/gen` command, meaning the LLM enhancer (if enabled) might apply, and the `--no` parameter will be combined with the default SDXL negative prompt if it's an SDXL model.

### 5. Viewing Prompts
Command: `--show` (as a reply, Admin only)
Usage: Reply to a generated image with `--show`.
This will send you a DM with the full prompt string (including parameters) that was used to generate that specific image.

### 6. Deleting Images/Messages
- **Delete Button 🗑️ / Reply `--delete`**: (Admin/Owner only) Deletes the generated image file(s) from storage AND removes the bot's message.
- **React with 🗑️**: (Admin/Owner only) Same as Delete Button/`--delete`.
- **Reply `--remove`**: (Admin/Owner only) Removes the bot's message from chat only (files remain).
- **Cancel Button ⏸️**: (Admin/Owner of job only) Appears on "queued" messages. Attempts to cancel the job in ComfyUI and remove it from the bot's queue.

### 7. Admin Commands
- `/settings`: Configure default Model (Flux/SDXL), CLIPs, Steps, Guidance (Flux & SDXL), Default SDXL Negative Prompt, Batch Size, Upscale Factor, Default Style, Variation Mode, Remix Mode, LLM Enhancer settings (Provider, Model, Display Preference).
- `/sheet [src]`: Queue prompts from a TSV file (URL or Discord Message ID/Link). Requires a 'prompt' column.
- `/clear`: Clear the ComfyUI processing queue (cancels pending, interrupts running).
- `/models`: List models available to ComfyUI via DM.
- `/styles`: View available style presets via DM (also available to non-admins).
- `/ping`: Check bot latency.
- `/help`: Show help information.

### 8. Configuration and Management (Configurator Tool)
The Configurator Tool (`TENOSAI-BOT.bat` or `python config-editor-script.py`) allows admins to:
- **Main Config:** Update paths (Outputs, Models, CLIPs, LoRAs, Custom Nodes), Bot Token, Admin Username, LLM API Keys.
- **Bot Settings:** Set global defaults for generation parameters (mirrors most of `/settings`). Includes "Default SDXL Negative Prompt".
- **LoRA Styles:** Create, edit, delete, and favorite LoRA style presets (used by `--style`).
- **Favorites:** Mark favorite Models (Flux & SDXL), CLIPs, and Styles for easier selection in settings dropdowns within the Configurator and the bot's `/settings` command.
- **LLM Prompts:** Edit the system prompts used by the LLM Enhancer for both Flux and SDXL.
- **Bot Control:** Start/Stop the `main_bot.py` script and view its log output.
- **Tools:** Install/Update required Custom Nodes, Scan Models/CLIPs/Checkpoints into JSON lists (used by the bot and configurator for selections).

**Important Notes:**
- Changes made in the Configurator (especially paths, API keys, and LLM Prompts) often require **restarting the `main_bot.py` script** to take effect (use the "Bot Control" tab).
- LoRA Styles (`--style [name]`) apply predefined LoRA configurations. Manage them in the Configurator's "LoRA Styles" tab.
- The bot distinguishes between Flux and SDXL workflows based on the selected model in `/settings` (or via `model_type_override` in certain actions). Ensure your selected model prefix (e.g., "Flux: model.gguf" or "SDXL: checkpoint.safetensors") is correct.

Enjoy creating! ❤️ BobsBlazed @Tenos.ai
