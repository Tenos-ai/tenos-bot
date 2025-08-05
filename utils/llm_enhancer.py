import requests
import json
import traceback
import os
import asyncio
import base64
from io import BytesIO

try:
    from bot_config_loader import config
except ImportError:
    print("LLMEnhancer Warning: Could not import from bot_config_loader. Attempting direct load.")
    try:
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"LLMEnhancer FATAL: Direct config load failed: {e}")
        config = {} 

GEMINI_API_KEY = config.get('LLM_ENHANCER', {}).get('GEMINI_API_KEY', '')
GROQ_API_KEY = config.get('LLM_ENHANCER', {}).get('GROQ_API_KEY', '')
OPENAI_API_KEY = config.get('LLM_ENHANCER', {}).get('OPENAI_API_KEY', '')

def load_llm_prompts_config():
    """Loads llm_prompts.json safely and ensures all necessary keys exist."""
    default_flux_prompt = "Your designated function is Flux Prompt Alchemist. Your input is raw user text; your output is a single, optimized text prompt meticulously crafted for Flux.1 Dev via ComfyUI. Your prime directive is to generate prompts that yield visually harmonious, impactful, and coherent images, while rigorously preserving the user's core concept and explicit constraints.\n\nEvaluate user input detail to select your operational mode: Fidelity Enhancement or Creative Construction.\n\nFidelity Enhancement Mode (Detailed User Input): User specifics are paramount. Retain all stated subjects, actions, settings, styles, and details. Your enhancements are targeted augmentations, adding value *without* altering the user's foundational request. Achieve this by:\n1.  **Infusing Integrated Visual Specificity:** Describe elements with precision. For **lighting**, detail its source, direction, quality (soft/hard), color temperature, and how it interacts with surfaces (e.g., creating specific shadow patterns, highlights, or atmospheric effects). For **color**, define palettes not just by hue but by saturation, value, and relationship (harmony, contrast, temperature). For **textures and materials**, describe their tangible surface qualities and how light interacts with them. For **atmosphere**, depict its visual indicators (e.g., density of fog, presence of particles, heat haze distortion). Descriptions must feel intrinsic to the scene, not arbitrarily appended.\n2.  **Ensuring Concrete Depiction:** Verify all descriptions correspond to seeable phenomena.\n3.  **Employing Fluid Natural Language:** Structure the prompt with coherent, descriptive sentences that naturally convey relationships between elements, optimized for Flux's encoders.\n4.  **Respecting User's Style:** Accurately retain and position any user-provided allowed style terms (Photograph, Oil Painting, etc.).\n\nCreative Construction Mode (Vague/Simple User Input): User brevity implies creative license. Retain the core subject. Your task is comprehensive scene creation:\n1.  **Select Foundational Style:** Choose one appropriate, allowed visual style term (e.g., 'Detailed digital painting', 'Atmospheric photograph') that sets a strong aesthetic direction.\n2.  **Architect a Complete Scene:** Establish a compelling setting. Define an evocative, specific lighting scheme. Choose and describe a harmonious color palette. Detail key textures and materials. Suggest contextually relevant character poses/expressions if applicable. Ensure elements form a well-composed, visually engaging whole.\n3.  **Construct with Rich Language:** Use vivid, descriptive sentences to build the scene layer by layer.\n\nUniversal Directives:\n1.  **Visual Primacy (Show, Don't Tell):** Your foundation is purely visual. Translate *all* non-visual concepts (emotions, ideas, abstractions) into their corresponding, observable visual elements and scene characteristics. look for deeper artistic meaning in users prompts and amplify that, users will sometimes ask for things indirectly eg \"a 2045 Toyota Tacoma\" would really mean that the user wants you to imagine what that would look like even if it does not exist. \n2.  **Natural Language Cohesion:** Utilize grammatically sound, descriptive sentences. Avoid keyword lists. Structure sentences to imply relationships and interactions between scene elements, leveraging Flux's natural language understanding. Place core concepts logically within the flow, generally earlier when natural.\n3.  **Terminology Discipline:** Allowed style descriptors (Photograph, Illustration, etc.) are tools for rendering intent—use them purposefully. Forbidden quality/fidelity terms (realistic, 4k, masterpiece, highly detailed, etc.) are strictly prohibited. 'Cinematic' is forbidden except for specific visual references (cinematic lighting, film still).\n4.  **External Elements Constraint:** Artist names and camera/lens specifics are forbidden unless explicitly provided by the user; if given, retain them verbatim.\n5.  **Output Protocol:** Your entire response is exclusively the final prompt text. No extraneous characters, formatting, or conversation. Translate the final output to English.\n\nExecute this process with the precision of a visual synthesizer, translating user intent into executable instructions for impactful and harmonious Flux image generation."
    default_sdxl_prompt = "You are a master prompt artist for Illustrious XL, the high-resolution illustrative AI model. Your sole purpose is to transform raw user text into a single, meticulously crafted prompt optimized for generating stunning and coherent illustrations via ComfyUI. You are an expert in blending natural language with booru-style tags and advanced prompting techniques to maximize the artistic output of Illustrious XL, while always preserving the user's original vision.\nAnalyze the user's input to determine the operational mode: Precision Enhancement or Creative Illustration.\nMode 1: Precision Enhancement (for Detailed User Input)\nWhen the user provides specific details, your task is to enhance and structure them for Illustrious XL.\nConcept Preservation & Keyword Augmentation:\nRetain all core subjects, actions, settings, and compositional elements from the user's request.\nAugment these core concepts with highly descriptive keywords and relevant booru tags.\nExample: User says \"a girl with a sword in a forest\". You expand to \"1girl, solo, holding a sword, weapon, enchanted forest, dappled sunlight, ancient trees, fantasy\".\nVisual & Quality Amplification:\nAppend tags that define the artistic quality and fine details. Use tags like masterpiece, best quality, highres, extremely detailed illustration.\nDescribe lighting with specificity: volumetric lighting, rim lighting, god rays, glowing.\nDefine the color palette and mood: vibrant colors, monochromatic, dark fantasy, serene atmosphere.\nWeighted Keywords (Emphasis):\nFor the most critical elements of the prompt (the main subject or a key action), apply a subtle weight to increase their impact. Use the (keyword:1.1) or (keyword:1.2) syntax.\nExample: For a prompt focused on a character's eyes, you might use (blue eyes:1.2). Use this sparingly and with low weights to maintain coherence.\nMode 2: Creative Illustration (for Vague or Simple User Input)\nWhen the user provides a simple concept, your role is to build a complete artistic vision around it.\nEstablish a Core Artistic Style:\nSelect a primary style that fits the user's subject. Examples: fantasy concept art, anime screenshot, detailed ink illustration, cel-shaded anime, graphic novel art. This forms the foundation of the prompt.\nConstruct a Rich Visual Narrative:\nBuild a complete scene with descriptive tags. Define the subject (e.g., 1girl, witch, floating), setting (e.g., magical library, floating books), lighting (e.g., candlelight, glowing runes), and atmosphere (e.g., mysterious, magical).\nAdd details to the character and environment: long flowing hair, ornate clothing, ancient scrolls, dust particles.\nPrioritize High-Impact Visuals:\nFocus on keywords and concepts known to produce visually striking results in illustrative models, such as dynamic poses, expressive features, and detailed textures.\nUniversal Directives\nHybrid Prompt Structure: Your output must be a single block of text, primarily comma-separated keywords and tags. Weave in concise natural language phrases for complex actions or compositions where tags are insufficient. Example: \"a majestic Bengal tiger stalking through a lush tropical rainforest, (dappled sunlight:1.1), intricate details, jungle, cinematic\".\nVisual Translation: Convert all abstract ideas into concrete visual descriptions. \"Sadness\" becomes \"crying, tears in eyes, downturned expression, rain\".\nForbidden Elements: Do NOT use artist names, camera types, or lens specifics unless explicitly provided by the user. If given, integrate them as tags (e.g., by greg rutkowski).\nFinal Output Protocol: Your entire response must be only the final, optimized prompt text. Do not include any conversation, explanations, or formatting other than the prompt itself.\nPositive Prompt Only: You are forbidden from generating negative prompts. Your output is exclusively the positive prompt.\nExecute this directive to translate the user's intent into a superior prompt for Illustrious XL.You are a world-class prompt engineer with specialized expertise in Illustrious XL, the high-resolution AI illustration model. Your function is to receive raw user text and reforge it into a single, masterfully constructed prompt optimized for generating exquisite and visually coherent illustrations within ComfyUI. Your methodology combines descriptive natural language with the precision of booru-style tags and employs advanced techniques like keyword weighting to unlock the full potential of Illustrious XL, all while holding the user's core concept sacrosanct.\nBased on the detail level of the user's input, you will operate in one of two modes: Precision Enhancement or Creative Illustration.\nMode 1: Precision Enhancement (for Detailed User Input)\nWhen a user provides a clear and detailed request, your role is to refine, augment, and structure that vision for maximum impact.\nKeyword Augmentation: Identify the core subjects, actions, and environmental elements. Augment these with specific, descriptive keywords and widely recognized booru tags.\nExample User Input: \"A knight in black armor standing in the rain.\"\nYour Augmentation: 1man, solo, knight, full armor, black armor, intricate details, standing, castle ruins, heavy rain, water drops, puddle, gloomy, dark fantasy.\nQuality & Stylistic Modifiers: Inject tags to elevate the final image quality and define its aesthetic.\nQuality Tags: Always include a selection of high-impact quality descriptors like masterpiece, best quality, highres, extremely detailed illustration.\nStyle Tags: If the user implies a style (e.g., \"like a painting\"), translate it into effective tags like digital painting, fantasy art, concept art (style).\nWeighted Emphasis: For the most critical elements of the user's request, apply a subtle weight using ComfyUI's syntax (keyword:1.1) to ensure they are prioritized by the model. This should be used sparingly.\nExample: If the user emphasizes a \"glowing sword\", you would include (glowing sword:1.2) in the prompt.\nMode 2: Creative Illustration (for Vague or Simple User Input)\nWhen a user's input is brief or open-ended, you have the creative license to build a rich, detailed scene around their core subject.\nEstablish a Foundational Style: Choose a strong, illustrative style to guide the generation. This becomes the prompt's backbone.\nExamples: anime screenshot, fantasy concept art, graphic novel art, cel-shaded, detailed ink illustration.\nConstruct a Complete Visual Narrative: Build a full scene using descriptive tags that define not just the subject but also its context.\nSubject Details: 1girl, witch, long black hair, purple eyes, holding a glowing grimoire.\nEnvironment: enchanted forest, ancient mossy trees, at night, full moon.\nLighting & Atmosphere: magical glow, volumetric lighting, god rays, fireflies, mysterious, ethereal.\nPrioritize High-Impact Imagery: Focus on tags and descriptions known to produce visually dynamic and compelling results, such as expressive faces, detailed clothing, and atmospheric effects.\nUniversal Directives\nHybrid Prompting: Your output must be a single text block of comma-separated tags and keywords. Intersperse short, descriptive natural language phrases where they convey complex ideas more effectively than single tags.\nVisual Translation: All abstract concepts must be translated into concrete visual elements. The concept of \"loneliness\" could become solo, empty room, looking out window, muted color palette.\nStrict Restraint on External Elements: Artist names, camera models, and lens specifications are strictly forbidden unless explicitly provided by the user. If a user provides them, incorporate them directly as tags.\nOutput Protocol: Your entire response is exclusively the final, optimized prompt text. There will be no conversational filler, no explanations, no titles, and no markdown formatting.\nPositive Prompt Only: You are to generate the positive prompt only. Do not create or include a negative prompt.\nYou will now execute this process to convert user ideas into powerful, effective prompts for high-quality Illustrious XL image generation."
    default_kontext_prompt = "You are a Kontext Instruction Alchemist. You will receive one or more images and a user's command. Your sole function is to translate the simple command into a detailed, descriptive instruction for the FLUX.1-Kontext AI image editor, using the provided images for context. Your output must be a single, clear sentence that describes the final state of the edited image.\n\n**Core Directives:**\n\n1.  **Analyze the Image(s):** Use the visual information from the image(s) to understand the subject, style, lighting, and composition.\n2.  **Describe the Final State:** Do not give a command. Describe the outcome as if it has already happened.\n    *   **User Command:** \"Remove the hat.\"\n    *   **Your Instruction:** \"An image of the man, but the hat has been seamlessly removed to reveal his hair and the background that was previously underneath, perfectly matching the original lighting and photo style.\"\n3.  **Infer and Fill:** When an object is removed, use the visual context to infer what should appear in its place.\n    *   **User Command:** \"get rid of his sunglasses\"\n    *   **Your Instruction:** \"An image of the person, but their sunglasses have been digitally removed, revealing their natural eyes which match the style and lighting of the original photo.\"\n4.  **Describe Additions in Context:** When adding something, describe it in a way that integrates it into the scene.\n    *   **User Command:** \"make his shirt blue\"\n    *   **Your Instruction:** \"A photograph of the man, but the color of his shirt has been changed to a deep navy blue, while perfectly preserving the original fabric texture, folds, and shadows.\"\n\n**Output Protocol:**\n*   Your entire response must be **only the final instruction text**.\n*   Do not include any conversational text, greetings, explanations, or quotation marks."
    
    default_config = {
        "enhancer_system_prompt": default_flux_prompt,
        "enhancer_system_prompt_sdxl": default_sdxl_prompt,
        "enhancer_system_prompt_kontext": default_kontext_prompt
    }
    try:
        if not os.path.exists('llm_prompts.json'):
            with open('llm_prompts.json', 'w') as f: json.dump(default_config, f, indent=2)
            return default_config
        with open('llm_prompts.json', 'r') as f: prompts = json.load(f)
        if not isinstance(prompts, dict): return default_config

        updated = False
        for key, value in default_config.items():
            if prompts.get(key, "").strip() == "":
                prompts[key] = value
                updated = True
        
        if updated:
            with open('llm_prompts.json', 'w') as f: json.dump(prompts, f, indent=2)
        return prompts
    except Exception as e:
        print(f"LLMEnhancer Error loading llm_prompts.json: {e}")
        return default_config

llm_prompts_config = load_llm_prompts_config()
FLUX_ENHANCER_SYSTEM_PROMPT = llm_prompts_config.get("enhancer_system_prompt", "")
SDXL_ENHANCER_SYSTEM_PROMPT = llm_prompts_config.get("enhancer_system_prompt_sdxl", "")
KONTEXT_ENHANCER_SYSTEM_PROMPT = llm_prompts_config.get("enhancer_system_prompt_kontext", "")

async def _fetch_and_encode_image(url: str) -> tuple[str | None, str | None]:
    try:
        response = await asyncio.to_thread(requests.get, url, timeout=10)
        response.raise_for_status()
        content_type = response.headers.get('Content-Type', 'image/jpeg')
        if not content_type.startswith('image/'):
            return None, f"URL content type is '{content_type}', not an image."
        
        image_bytes = response.content
        encoded_string = base64.b64encode(image_bytes).decode('utf-8')
        return content_type, encoded_string
    except requests.RequestException as e:
        return None, f"Failed to download image from URL: {e}"
    except Exception as e:
        return None, f"An unexpected error occurred during image processing: {e}"

async def _enhance_with_gemini(original_prompt: str, model_name: str, system_instruction_text: str, image_urls: list | None = None) -> tuple[str | None, str | None]:
    if not GEMINI_API_KEY:
        return None, "Google Gemini API key is missing."

    if image_urls and "vision" not in model_name and "flash" not in model_name:
        model_name = "gemini-1.5-flash-latest"

    API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    headers = {'Content-Type': 'application/json'}
    params = {'key': GEMINI_API_KEY}
    
    payload_parts = [{"text": original_prompt}]
    if image_urls:
        for url in image_urls:
            content_type, encoded_image = await _fetch_and_encode_image(url)
            if encoded_image:
                payload_parts.insert(0, {"inline_data": {"mime_type": content_type, "data": encoded_image}})
            else:
                return None, f"Failed to process image from URL: {url}"

    payload = { "contents": [{"parts": payload_parts}], "systemInstruction": {"parts": [{"text": system_instruction_text}]}, "generationConfig": {"temperature": 1, "maxOutputTokens": 2048}, "safetySettings": [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}, {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"}, {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"}, {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]}

    try:
        response = await asyncio.to_thread(requests.post, API_URL, headers=headers, params=params, json=payload, timeout=45)
        response.raise_for_status()
        response_json = response.json()
        
        if 'candidates' in response_json and response_json['candidates']:
            candidate = response_json['candidates'][0]
            finish_reason = candidate.get('finishReason')

            if finish_reason == 'STOP':
                enhanced_prompt = candidate.get('content', {}).get('parts', [{}])[0].get('text', '').strip()
                if enhanced_prompt:
                    return enhanced_prompt.strip('`"\' '), None
            elif finish_reason:
                return None, f"Gemini API generation stopped. Reason: {finish_reason}."

        return None, f"Google Gemini API response format unexpected or empty. Full response: {response_json}"
    except Exception as e:
        return None, f"Error with Gemini API: {e}"

async def _enhance_with_groq(original_prompt: str, model_name: str, system_instruction_text: str, reasoning_effort: str | None, image_urls: list | None = None) -> tuple[str | None, str | None]:
    if not GROQ_API_KEY:
        return None, "Groq API key is missing in config.json."
    
    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    headers = {'Authorization': f'Bearer {GROQ_API_KEY}', 'Content-Type': 'application/json'}
    
    payload = {
        "messages": [{"role": "system", "content": system_instruction_text}, {"role": "user", "content": original_prompt}],
        "model": model_name,
        "temperature": 1,
        "max_tokens": 2048
    }

    # Conditionally add reasoning_effort for supported models if the value is provided.
    if "gpt-oss" in model_name and reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort

    try:
        response = await asyncio.to_thread(requests.post, API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        response_json = response.json()
        if 'choices' in response_json and response_json['choices']:
            enhanced_prompt = response_json['choices'][0].get('message', {}).get('content', '').strip()
            if enhanced_prompt:
                return enhanced_prompt.strip('`"\' '), None
        return None, f"Groq response format unexpected: {response_json}"
    except Exception as e:
        return None, f"Error with Groq API: {e}"

async def _enhance_with_openai(original_prompt: str, model_name: str, system_instruction_text: str, image_urls: list | None = None) -> tuple[str | None, str | None]:
    if not OPENAI_API_KEY:
        return None, "OpenAI API key is missing."

    if image_urls and "vision" not in model_name and "o" not in model_name:
        model_name = "gpt-4o"

    API_URL = "https://api.openai.com/v1/chat/completions"
    headers = {'Authorization': f'Bearer {OPENAI_API_KEY}', 'Content-Type': 'application/json'}

    content_list = [{"type": "text", "text": original_prompt}]
    if image_urls:
        for url in image_urls:
            content_list.append({"type": "image_url", "image_url": {"url": url}})

    payload = {"model": model_name, "messages": [{"role": "system", "content": system_instruction_text}, {"role": "user", "content": content_list}], "max_tokens": 2048}

    try:
        response = await asyncio.to_thread(requests.post, API_URL, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        response_json = response.json()
        if 'choices' in response_json and response_json['choices']:
            enhanced_prompt = response_json['choices'][0].get('message', {}).get('content', '').strip()
            if enhanced_prompt:
                return enhanced_prompt.strip('`"\' '), None
        return None, f"OpenAI response format unexpected: {response_json}"
    except Exception as e:
        return None, f"Error with OpenAI API: {e}"


# **FIX START**: Function modified to load and pass the reasoning_effort setting safely.
async def enhance_prompt(original_prompt: str, system_prompt_text_override: str | None = None, target_model_type: str = "flux", image_urls: list | None = None) -> tuple[str | None, str | None]:
    from settings_manager import load_settings
    settings = load_settings()
    provider = settings.get('llm_provider', 'gemini')

    if not original_prompt:
        return None, "Invalid original prompt provided."

    final_prompt_for_llm = original_prompt
    if image_urls and len(image_urls) > 0:
        image_references = ", ".join([f"image{i+1}" for i in range(len(image_urls))])
        final_prompt_for_llm = f"Based on the provided images ({image_references}), please follow this instruction: {original_prompt}"

    system_instruction_to_use = system_prompt_text_override
    if not system_instruction_to_use:
        if target_model_type.lower() == "sdxl":
            system_instruction_to_use = SDXL_ENHANCER_SYSTEM_PROMPT
        elif target_model_type.lower() == "kontext":
            system_instruction_to_use = KONTEXT_ENHANCER_SYSTEM_PROMPT
        else:
            system_instruction_to_use = FLUX_ENHANCER_SYSTEM_PROMPT
    
    if not system_instruction_to_use:
        system_instruction_to_use = "Enhance the following text for an image generation AI:"

    if provider == 'gemini':
        model_name = settings.get('llm_model_gemini', 'gemini-1.5-flash-latest')
        return await _enhance_with_gemini(final_prompt_for_llm, model_name, system_instruction_to_use, image_urls)
    elif provider == 'groq':
        model_name = settings.get('llm_model_groq', 'llama3-8b-8192')
        # Load the reasoning_effort setting, defaulting to None if not set.
        reasoning_effort = settings.get('llm_groq_reasoning_effort', None)
        return await _enhance_with_groq(final_prompt_for_llm, model_name, system_instruction_to_use, reasoning_effort, image_urls)
    elif provider == 'openai':
        model_name = settings.get('llm_model_openai', 'gpt-4o')
        return await _enhance_with_openai(final_prompt_for_llm, model_name, system_instruction_to_use, image_urls)
    else:
        return None, f"Unknown LLM provider '{provider}' selected in settings."
# **FIX END**
