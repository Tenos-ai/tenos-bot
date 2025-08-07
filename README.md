# Tenosai-Bot: ComfyUI API Discord Bot for Flux & SDXL Image Generation

## Updates

**COMPLETED UPDATES**

**7/29/25**
- **Update 4**: **Version 1.2.4**

This update introduces a more organized and powerful configuration experience, adds dedicated settings for Kontext editing, and refines the user interface.

-   **Tabbed Bot Settings in Configurator:** The "Bot Settings" tab in the GUI has been reorganized into five distinct sub-tabs for clarity:
    -   **General:** Core model selections, VAE, variation settings, batch sizes, MP size, and upscale factor.
    -   **Flux:** Default style, steps, guidance specifically for Flux generations.
    -   **SDXL:** Default style, steps, guidance, and negative prompt for SDXL generations.
    -   **Kontext:** New dedicated settings for the `/edit` command, including default steps, guidance, and MP size.
    -   **LLM:** Settings for the prompt enhancer and display preferences. Added support for OpenAI oss models and all other thinking models via Groq.

-   **Model-Specific Default Styles:** The single `default_style` setting has been split. You can now set a `default_style_flux` and a `default_style_sdxl` independently in the configurator. The bot will automatically apply the correct default style based on the model being used.

-   **Advanced MP Size Control:** In the configurator, the "Default MP Size" fields are now float values instead of a dropdown, allowing for more precise control over generation resolution (e.g., `1.15`). The `/settings` command in Discord retains the user-friendly dropdown.

-   **Variation Batch Size:** A new setting for "Variation Batch Size" has been added for future features.

-   **UI & Bug Fixes:**
    -   The variation buttons on generation results have been refined. Single-image results (like variations or reruns) now correctly show distinct `Vary W 🤏` and `Vary S 💪` buttons. Multi-image (batch) results correctly show simplified `V1`, `V2`, etc., which dynamically use your current default variation setting.
    -   Fixed a bug where the `MP` value was not displayed correctly in the final completion message.
    -   Fixed a visual bug in the configurator where the Bot Settings page would not refresh correctly after being changed via the `/settings` command in Discord.
    -   The file scanner now correctly recognizes completed Kontext jobs (prefixed with `EDIT_`).

**7/6/25**
- **Update 3**:
  - fixed a few bugs, official V1.2.3 update now has all features working with no bugs, as of today this will be stable release 1. Update tool will pull updates on the next numbered release (1.2.4).

**7/4/25**
- **Update 2**:
  - added auto update feature so the app and repo stay in sync without needing to download the zip over and over as I add features. The automatic update on startup can be turned on and off in `main config` > `app settings`. Updates can also be triggered manually via `Tools` > `Update Application`.
  - added sub tabs to the LLM prompts so that its easier to manage.

**7/2/25**
- **Update 1**: Integrated **FLUX Kontext** for powerful instruction-based image editing and stitching via the new `/edit` command. The LLM Enhancer now supports multi-modal vision to better interpret edit instructions.
- **Hotfix 1**: Fixed a job cancellation issue, improved first-time setup with venv creation, enhanced LLM support for new models, and added a tool to pull complete LLM model lists from the GUI.

----------
**KNOWN BUGS**

- None(?)

**PLANED UPDATES**

- New GUI
- Metadata `on/off` toggle for all jobs

----------

|||
|---|---|
|<img width="1004" height="1079" alt="image" src="https://github.com/user-attachments/assets/edb97a3f-bba6-4674-a2c6-dbbb97832156" />|<img width="1272" height="1466" alt="image" src="https://github.com/user-attachments/assets/9d0911cb-9443-484f-a2e6-dcc48f91e57f" />|
|![image](https://github.com/user-attachments/assets/ae767ff0-edbc-4164-a218-a874c96c12ff)|![image](https://github.com/user-attachments/assets/c7f21488-9351-4ab1-93f5-a0f545aec8fb)|

## First-Time Setup

**(IF YOU DO NOT HAVE A DISCORD BOT ACCOUNT ALREADY CREATED, OPEN "HOW TO DISCORD BOT.txt" AND FOLLOW INSTRUCTIONS)**

Make sure you already have ComfyUI installed. If you need ComfyUI still, you can download it [`HERE`](https://www.comfy.org/download).

Download the portable zip from this repository via the "Code" button at the top of the page, or click [`HERE`](https://github.com/Tenos-ai/tenos-bot/archive/refs/heads/main.zip) to download the zip directly. I recommend placing it in your ComfyUI Portable folder, but you can put it anywhere and it should work just fine.

![image](https://github.com/user-attachments/assets/56fd503b-ac57-4c00-a854-b84983ce823b)

  - The bot requires specific custom nodes. You can install them manually by cloning the following GitHub repositories into your `ComfyUI/custom_nodes` folder, or by using the Configurator's "Install/Update Custom Nodes" tool (under the "Tools" menu):
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
- **Input the admin's Discord User ID** into the `ADMIN` -> `ID` field in "Main Config".
- **Optionally input API Keys** for Google Gemini, Groq, and/or OpenAI in the `LLM_ENHANCER` section of "Main Config" if you plan to use the LLM Prompt Enhancer feature.

This step is crucial for the bot to function correctly. After initial setup, use the "Bot Control" tab in the configurator to start the bot. The bot uses the model selected via `/settings` or the Configurator as the default for new generations.

### OPTIONAL: Download the Tenos Official Flux Dev Finetune from Huggingface [`HERE`](https://huggingface.co/Tenos-ai/Tenos)
|||
|---|---|
|![GEN_UP_d2617aa5_from_img3_srcID49b5195c_00001_](https://github.com/user-attachments/assets/4ae5190c-31bf-409f-97b1-bc86c3a10f46)|![GEN_UP_9e781f69_from_img1_srcIDdd942772_00001_](https://github.com/user-attachments/assets/51da3345-0a04-4322-a752-507dec753703)|
|![GEN_UP_d1cd670a_from_img1_srcID1f65a8b2_00001_](https://github.com/user-attachments/assets/073dc426-fc17-4d72-bb32-a4bddbeb25c8)|![GEN_UP_eaaae372_from_img1_srcID59bbc663_00001_](https://github.com/user-attachments/assets/dc624227-5438-46a1-b15c-ffadbce66a68)|
|![GEN_UP_2a4b938f_from_img3_srcID72bdcd57_00001_](https://github.com/user-attachments/assets/8f238a2a-0af4-4dd7-b097-266e7c57ee49)|![GEN_UP_14d8816e_from_img4_srcID2bc0af53_00001_](https://github.com/user-attachments/assets/1c6e45cb-5516-4c4e-a5c8-590ed3d49364)|

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

Example: `/gen a majestic lion --ar 16:9 --seed 1234 --style realistic --g_sdxl 6.5`
Example (SDXL with custom negative): `/gen cyberpunk city --no "trees, nature, day"`

**LLM Prompt Enhancer:**
- An admin can enable a prompt enhancer via `/settings`.
- If enabled, your initial prompt may be rewritten by the selected LLM (Google Gemini, Groq, or OpenAI) to be more descriptive. This applies to `/gen` and `/edit` commands.
- Generated messages will have a ✨ icon if the enhancer was used successfully.
- Edit the system prompts used by the enhancer via the Configurator's "LLM Prompts" tab.

### 2. Image Editing with Kontext
Command: `/edit`
Usage: `/edit [instruction] [image1] [image2] [image3] [image4] [options]`

This powerful feature uses FLUX Kontext to edit up to 4 images based on your text instructions. You can blend images, change objects, alter styles, and much more.

Options:
- `--g [number]`: Set guidance scale for the edit (e.g., `3.0`).
- `--ar [W:H]`: Set aspect ratio for the final output canvas.
- `--steps [number]`: Set the number of steps for the generation.

Example: `/edit instruction:make the cat wear a wizard hat image1:<upload_cat_image>`
Example: `/edit instruction:blend these two styles image1:<upload_style1_image> image2:<upload_style2_image> --ar 16:9`

### 3. Image Upscaling
Command: Reply with `--up` or click the `Upscale ⬆️` button.
Usage: Reply to a generated image with `--up [options]` or click the button.

Options (for reply command):
- `--seed [number]`: Set a specific seed for the upscale.
- `--style [style_name]`: Apply a different style during the upscale process.

Example (replying to an image): `--up --seed 5678 --style detailed`

### 4. Image Variation
Command: Reply with `--vary [type]` or click the `Vary W 🤏` / `Vary S 💪` buttons.
Usage: Reply to a generated image with `--vary [type] [options]` or click the button.

Types:
- `w`: Weak variation (subtle changes, lower denoise)
- `s`: Strong variation (significant changes, higher denoise)

Options (for reply command):
- `--prompt "[new_prompt]"`: If Remix Mode is ON (via `/settings`), use this new prompt for the variation.
- `--no "[negative_prompt_text]"`: **(SDXL Variation Only)** Sets/replaces the negative prompt for this variation.
- `--style [style_name]`: Apply a different style to the variation.

**Remix Mode:**
- If "Variation Remix Mode" is ON (via `/settings`), clicking a Vary button (🤏/💪) will open a modal to edit the prompt before generating.

### 5. Rerunning & Editing
- **Rerun 🔄**: Reruns the original generation prompt and parameters with a new seed.
- **Edit ✏️**: Opens a modal to perform a new **Kontext Edit** on the selected image(s). You can provide new instructions and even add more images to blend.

### 6. Utility Commands
- `/styles`: View available style presets via DM.
- `/ping`: Check bot latency.
- `/help`: Show this help information.

### 7. Deleting & Managing Jobs
- **Delete 🗑️ / Reply `--delete`**: (Admin/Owner only) Deletes generated image file(s) AND the Discord message.
- **React with 🗑️**: (Admin/Owner only) Same as the Delete button.
- **Reply `--remove`**: (Admin/Owner only) Removes the Discord message only (files remain).
- **Cancel ⏸️**: (Admin/Owner of job only) Appears on queued messages to cancel the job in ComfyUI.
- **`--show` (Reply)**: (Admin only) Get a DM with the full prompt string used for a generation.

### 8. Admin Commands
- `/settings`: Configure default models (Flux, SDXL, Kontext), CLIPs, generation parameters, LLM enhancer, and more.
- `/sheet [src]`: Queue prompts from a TSV file (URL or Discord Message ID/Link).
- `/clear`: Clear the ComfyUI processing queue.
- `/models`: List models available to ComfyUI via DM.

### 9. Configuration and Management (Configurator Tool)
The Configurator Tool (`TENOSAI-BOT.bat` or `python config-editor-script.py`) allows admins to:
- **Main Config:** Update all critical paths, Bot Token, Admin ID, and LLM API Keys.
- **Bot Settings:** Set global defaults for all generation parameters (mirrors `/settings`).
- **LoRA Styles:** Create, edit, and favorite LoRA style presets.
- **Favorites:** Mark favorite Models, CLIPs, and Styles for easier selection in menus.
- **LLM Prompts:** Edit the powerful system prompts used by the LLM Enhancer.
- **Bot Control:** Start/Stop the bot script and view its live log output.
- **Tools Menu:** Install/Update Custom Nodes, Scan for new models/checkpoints/CLIPs, and refresh the LLM models list.

**Important Notes:**
- Changes made in the Configurator (especially paths and API keys) require **restarting the bot script** to take effect (use the "Bot Control" tab).
- The bot distinguishes between Flux and SDXL workflows based on the model selected in `/settings`. Ensure your selected model has the correct prefix (e.g., "Flux: model.gguf" or "SDXL: checkpoint.safetensors").

Enjoy creating! ❤️ BobsBlazed @Tenos.ai
