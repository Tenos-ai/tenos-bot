import requests
import json
import traceback
import os
import asyncio


try:
    from bot_config_loader import config
except ImportError:
    
    print("LLMEnhancer Warning: Could not import from bot_config_loader. Attempting direct load of config.json from parent directory.")
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
    """Loads llm_prompts.json safely."""
    default_flux_prompt = """Your designated function is Flux Prompt Alchemist. Your input is raw user text; your output is a single, optimized text prompt meticulously crafted for Flux.1 Dev via ComfyUI. Your prime directive is to generate prompts that yield visually harmonious, impactful, and coherent images, while rigorously preserving the user's core concept and explicit constraints.

Evaluate user input detail to select your operational mode: Fidelity Enhancement or Creative Construction.

Fidelity Enhancement Mode (Detailed User Input): User specifics are paramount. Retain all stated subjects, actions, settings, styles, and details. Your enhancements are targeted augmentations, adding value *without* altering the user's foundational request. Achieve this by:
1.  **Infusing Integrated Visual Specificity:** Describe elements with precision. For **lighting**, detail its source, direction, quality (soft/hard), color temperature, and how it interacts with surfaces (e.g., creating specific shadow patterns, highlights, or atmospheric effects). For **color**, define palettes not just by hue but by saturation, value, and relationship (harmony, contrast, temperature). For **textures and materials**, describe their tangible surface qualities and how light interacts with them. For **atmosphere**, depict its visual indicators (e.g., density of fog, presence of particles, heat haze distortion). Descriptions must feel intrinsic to the scene, not arbitrarily appended.
2.  **Ensuring Concrete Depiction:** Verify all descriptions correspond to seeable phenomena.
3.  **Employing Fluid Natural Language:** Structure the prompt with coherent, descriptive sentences that naturally convey relationships between elements, optimized for Flux's encoders.
4.  **Respecting User's Style:** Accurately retain and position any user-provided allowed style terms (Photograph, Oil Painting, etc.).

Creative Construction Mode (Vague/Simple User Input): User brevity implies creative license. Retain the core subject. Your task is comprehensive scene creation:
1.  **Select Foundational Style:** Choose one appropriate, allowed visual style term (e.g., 'Detailed digital painting', 'Atmospheric photograph') that sets a strong aesthetic direction.
2.  **Architect a Complete Scene:** Establish a compelling setting. Define an evocative, specific lighting scheme. Choose and describe a harmonious color palette. Detail key textures and materials. Suggest contextually relevant character poses/expressions if applicable. Ensure elements form a well-composed, visually engaging whole.
3.  **Construct with Rich Language:** Use vivid, descriptive sentences to build the scene layer by layer.

Universal Directives:
1.  **Visual Primacy (Show, Don't Tell):** Your foundation is purely visual. Translate *all* non-visual concepts (emotions, ideas, abstractions) into their corresponding, observable visual elements and scene characteristics. look for deeper artistic meaning in users prompts and amplify that, users will sometimes ask for things indirectly eg "a 2045 Toyota Tacoma" would really mean that the user wants you to imagine what that would look like even if it does not exist.
2.  **Natural Language Cohesion:** Utilize grammatically sound, descriptive sentences. Avoid keyword lists. Structure sentences to imply relationships and interactions between scene elements, leveraging Flux's natural language understanding. Place core concepts logically within the flow, generally earlier when natural.
3.  **Terminology Discipline:** Allowed style descriptors (Photograph, Illustration, etc.) are tools for rendering intent—use them purposefully. Forbidden quality/fidelity terms (realistic, 4k, masterpiece, highly detailed, etc.) are strictly prohibited. 'Cinematic' is forbidden except for specific visual references (cinematic lighting, film still).
4.  **External Elements Constraint:** Artist names and camera/lens specifics are forbidden unless explicitly provided by the user; if given, retain them verbatim.
5.  **Output Protocol:** Your entire response is exclusively the final prompt text. No extraneous characters, formatting, or conversation.

Execute this process with the precision of a visual synthesizer, translating user intent into executable instructions for impactful and harmonious Flux image generation.
"""
    default_sdxl_prompt = """You are an expert prompt enhancer for SDXL text-to-image generation. Your input is raw user text; your output is a single, optimized text prompt meticulously crafted for SDXL via ComfyUI. Your prime directive is to generate prompts that yield visually striking and coherent images, adhering to SDXL's preference for descriptive keywords and booru-style tags, while rigorously preserving the user's core concept and explicit constraints.

Evaluate user input detail to select your operational mode: Tag Expansion or Creative Tagging.

Tag Expansion Mode (Detailed User Input): User specifics are paramount. Retain all stated subjects, actions, settings, styles, and details. Your enhancements involve:
1.  **Keyword Extraction & Augmentation:** Identify core subjects, actions, and elements. Augment with relevant descriptive keywords and common booru tags. For example, if the user says "a cat sitting on a windowsill in the sun", you might expand to "1cat, solo, sitting, windowsill, sun, sunlight, indoors, detailed fur, whiskers, relaxed pose".
2.  **Style and Quality Tags:** Add relevant style tags (e.g., "anime style", "photorealistic", "oil painting (medium)") and general quality tags (e.g., "masterpiece", "best quality", "highres") if not contradictory to user's intent. Be mindful of over-tagging.
3.  **Visual Specificity through Tags:** Use tags to describe lighting (e.g., "dramatic lighting", "rim lighting", "volumetric lighting"), color palettes (e.g., "monochrome", "vibrant colors", "pastel colors"), textures ("smooth skin", "rough metal"), and atmosphere ("foggy", "glowing particles").
4.  **Respecting User's Style Terms:** If the user provides explicit style terms like "Photograph" or "Oil Painting", translate them into appropriate tags or incorporate them directly if they function well as tags.

Creative Tagging Mode (Vague/Simple User Input): User brevity implies creative license. Retain the core subject. Your task is to build a rich tagged scene:
1.  **Select Foundational Style:** Choose an appropriate primary style tag (e.g., "fantasy art", "sci-fi concept art", "impressionist painting") that sets a strong aesthetic direction.
2.  **Construct a Complete Scene with Tags:** Establish a setting using tags (e.g., "forest", "cityscape", "outer space"). Define lighting ("golden hour"), color ("cool color palette"), key textures ("metallic sheen"), and relevant character details ("long hair", "blue eyes", "holding sword") using tags.
3.  **Prioritize Impactful Tags:** Focus on tags known to produce strong visual results in SDXL.

Universal Directives:
1.  **Tag-Based Structure:** Your output should primarily consist of comma-separated keywords and tags. Natural language phrases can be used for complex concepts but should be concise.
2.  **Visual Focus:** All tags should describe visual elements. Translate non-visual concepts into visual tags. For abstract ideas like "sadness," use tags like "crying," "tear-filled eyes," "downcast expression," "rainy day."
3.  **No Forbidden Terms (unless they are effective tags):** While some terms like "realistic" or "masterpiece" are discouraged in natural language prompts for other models, they can be effective as tags for SDXL. Use your judgment. Avoid "cinematic" unless referring to "cinematic lighting" as a tag.
4.  **External Elements Constraint:** Artist names and camera/lens specifics are forbidden unless explicitly provided by the user; if given, incorporate them as tags.
5.  **Output Protocol:** Your entire response is exclusively the final prompt text (comma-separated tags/keywords). No extraneous characters, formatting, or conversation.
6.  **Negative Prompts:** Do *NOT* generate negative prompts. Only provide the positive prompt.

Execute this process to convert user intent into an effective, tagged prompt for high-quality SDXL image generation.
"""
    default_config = {
        "enhancer_system_prompt": default_flux_prompt,
        "enhancer_system_prompt_sdxl": default_sdxl_prompt
    }
    try:
        if not os.path.exists('llm_prompts.json'):
            print("LLMEnhancer: llm_prompts.json not found. Creating with default prompts.")
            with open('llm_prompts.json', 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config

        with open('llm_prompts.json', 'r') as f:
            prompts = json.load(f)

        if not isinstance(prompts, dict):
            print("LLMEnhancer Error: llm_prompts.json invalid structure. Using default.")
            return default_config

        updated = False
        if "enhancer_system_prompt" not in prompts or not isinstance(prompts["enhancer_system_prompt"], str):
            print("LLMEnhancer Warning: 'enhancer_system_prompt' missing or invalid. Using default Flux prompt.")
            prompts["enhancer_system_prompt"] = default_flux_prompt
            updated = True
        if "enhancer_system_prompt_sdxl" not in prompts or not isinstance(prompts["enhancer_system_prompt_sdxl"], str):
            print("LLMEnhancer Warning: 'enhancer_system_prompt_sdxl' missing or invalid. Using default SDXL prompt.")
            prompts["enhancer_system_prompt_sdxl"] = default_sdxl_prompt
            updated = True

        if updated:
            try:
                with open('llm_prompts.json', 'w') as f:
                    json.dump(prompts, f, indent=2)
                print("LLMEnhancer: llm_prompts.json updated with missing default prompts.")
            except OSError as e_write:
                print(f"LLMEnhancer Error: Could not write updated llm_prompts.json: {e_write}")

        return prompts
    except (OSError, json.JSONDecodeError) as e:
        print(f"LLMEnhancer Error loading llm_prompts.json: {e}. Using default.")
        return default_config
    except Exception as e:
        print(f"LLMEnhancer Unexpected error loading llm_prompts.json: {e}")
        traceback.print_exc()
        return default_config

llm_prompts_config = load_llm_prompts_config()
FLUX_ENHANCER_SYSTEM_PROMPT = llm_prompts_config.get("enhancer_system_prompt", "")
SDXL_ENHANCER_SYSTEM_PROMPT = llm_prompts_config.get("enhancer_system_prompt_sdxl", "")

if not FLUX_ENHANCER_SYSTEM_PROMPT:
    print("LLMEnhancer FATAL WARNING: Could not load Flux enhancer system prompt!")
    FLUX_ENHANCER_SYSTEM_PROMPT = "Enhance the following prompt for Flux.1 image generation AI, focusing on natural language visual descriptions:"
if not SDXL_ENHANCER_SYSTEM_PROMPT:
    print("LLMEnhancer FATAL WARNING: Could not load SDXL enhancer system prompt!")
    SDXL_ENHANCER_SYSTEM_PROMPT = "Enhance the following prompt for SDXL image generation AI, focusing on descriptive keywords and booru-style tags:"


async def _enhance_with_gemini(original_prompt: str, model_name: str, system_instruction_text: str) -> tuple[str | None, str | None]:
    if not GEMINI_API_KEY:
        return None, "Google Gemini API key is missing in config.json."

    API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    headers = {'Content-Type': 'application/json'}
    params = {'key': GEMINI_API_KEY}

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": system_instruction_text + "\n\nEnhance this prompt:\n" + original_prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 1,
            "maxOutputTokens": 524,
        }
    }

    try:
        print(f"Sending prompt to Google Gemini API ({model_name}) for enhancement: '{original_prompt}'")
        response = await asyncio.to_thread(
            requests.post, API_URL, headers=headers, params=params, json=payload, timeout=30
        )
        response.raise_for_status()
        response_json = response.json()

        if 'candidates' in response_json and response_json['candidates']:
            candidate = response_json['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content'] and candidate['content']['parts']:
                enhanced_prompt = candidate['content']['parts'][0].get('text', '').strip()
                if enhanced_prompt:
                    enhanced_prompt = enhanced_prompt.strip('`"\' ')
                    if len(enhanced_prompt) > 2000:
                        print("Warning: Google Gemini API enhanced prompt > 2000 chars, truncating.")
                        enhanced_prompt = enhanced_prompt[:2000] + "..."
                    print(f"Google Gemini API Enhancement Successful: '{enhanced_prompt}'")
                    return enhanced_prompt, None
                else: return None, "Google Gemini API returned empty content."
            else: return None, "Google Gemini API response missing expected content structure."
        elif 'error' in response_json:
            error_info = response_json['error']
            print(f"Google Gemini API Error: {error_info.get('code')} - {error_info.get('message')}")
            return None, f"Google Gemini API Error: {error_info.get('message', 'Unknown API error')}"
        else:
            print(f"Google Gemini API response format unexpected: {response_json}")
            return None, "Google Gemini API response format unexpected."
    except requests.exceptions.Timeout:
        print("Error: Timeout connecting to Google Gemini API.")
        return None, "Timeout connecting to enhancement service (Google Gemini API)."
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Google Gemini API: {e}")
        error_details = "Unknown connection error"
        if e.response is not None:
            status_code = e.response.status_code
            try: error_details = e.response.json().get('error', {}).get('message', e.response.text)
            except json.JSONDecodeError: error_details = e.response.text
            print(f"  Status Code: {status_code}, Details: {error_details}")
            if status_code == 400: return None, f"Invalid request to Google Gemini API ({error_details})."
            if status_code in [401, 403]: return None, "Authentication error with Google Gemini API (check API key)."
            if status_code == 429: return None, "Rate limit exceeded for Google Gemini API."
            error_details = f"Google Gemini API connection error ({status_code})."
        else: error_details = "Network error connecting to Google Gemini API."
        return None, error_details
    except Exception as e:
        print(f"Unexpected error during Google Gemini API enhancement: {e}")
        traceback.print_exc()
        return None, "Unexpected error during enhancement (Google Gemini API)."


async def _enhance_with_groq(original_prompt: str, model_name: str, system_instruction_text: str) -> tuple[str | None, str | None]:
    if not GROQ_API_KEY:
        return None, "Groq API key is missing in config.json."

    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        'Authorization': f'Bearer {GROQ_API_KEY}',
        'Content-Type': 'application/json'
    }

    payload = {
        "messages": [
            {"role": "system", "content": system_instruction_text},
            {"role": "user", "content": "Enhance this prompt:\n" + original_prompt}
        ],
        "model": model_name,
        "temperature": 1,
        "max_tokens": 512,
    }

    try:
        print(f"Sending prompt to Groq ({model_name}) for enhancement: '{original_prompt}'")
        response = await asyncio.to_thread(
            requests.post, API_URL, headers=headers, json=payload, timeout=30
        )
        response.raise_for_status()
        response_json = response.json()

        if 'choices' in response_json and response_json['choices']:
            choice = response_json['choices'][0]
            if 'message' in choice and 'content' in choice['message']:
                enhanced_prompt = choice['message']['content'].strip()
                if enhanced_prompt:
                    enhanced_prompt = enhanced_prompt.strip('`"\' ')
                    if len(enhanced_prompt) > 2000:
                        print("Warning: Groq enhanced prompt > 2000 chars, truncating.")
                        enhanced_prompt = enhanced_prompt[:2000] + "..."
                    print(f"Groq Enhancement Successful: '{enhanced_prompt}'")
                    return enhanced_prompt, None
                else: return None, "Groq returned empty content."
            else: return None, "Groq response missing expected message content."
        elif 'error' in response_json:
            error_info = response_json['error']
            print(f"Groq API Error: {error_info.get('type')} - {error_info.get('message')}")
            return None, f"Groq API Error: {error_info.get('message', 'Unknown API error')}"
        else:
            print(f"Groq response format unexpected: {response_json}")
            return None, "Groq response format unexpected."
    except requests.exceptions.Timeout:
        print("Error: Timeout connecting to Groq API.")
        return None, "Timeout connecting to enhancement service (Groq)."
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Groq API: {e}")
        error_details = "Unknown connection error"
        if e.response is not None:
            status_code = e.response.status_code
            try: error_details = e.response.json().get('error', {}).get('message', e.response.text)
            except json.JSONDecodeError: error_details = e.response.text
            print(f"  Status Code: {status_code}, Details: {error_details}")
            if status_code == 400: return None, f"Invalid request to Groq ({error_details})."
            if status_code == 401: return None, "Authentication error with Groq (check API key)."
            if status_code == 403: return None, f"Permission error with Groq ({error_details})."
            if status_code == 429: return None, "Rate limit exceeded for Groq."
            error_details = f"Groq connection error ({status_code})."
        else: error_details = "Network error connecting to Groq."
        return None, error_details
    except Exception as e:
        print(f"Unexpected error during Groq enhancement: {e}")
        traceback.print_exc()
        return None, "Unexpected error during enhancement (Groq)."

async def _enhance_with_openai(original_prompt: str, model_name: str, system_instruction_text: str) -> tuple[str | None, str | None]:
    if not OPENAI_API_KEY:
        return None, "OpenAI API key is missing in config.json."

    API_URL = "https://api.openai.com/v1/chat/completions"
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }

    payload = {
        "messages": [
            {"role": "system", "content": system_instruction_text},
            {"role": "user", "content": "Enhance this prompt:\n" + original_prompt}
        ],
        "model": model_name,
        "temperature": 1,
        "max_tokens": 524,
    }

    try:
        print(f"Sending prompt to OpenAI ({model_name}) for enhancement: '{original_prompt}'")
        response = await asyncio.to_thread(
            requests.post, API_URL, headers=headers, json=payload, timeout=30
        )
        response.raise_for_status()
        response_json = response.json()

        if 'choices' in response_json and response_json['choices']:
            choice = response_json['choices'][0]
            if 'message' in choice and 'content' in choice['message']:
                enhanced_prompt = choice['message']['content'].strip()
                if enhanced_prompt:
                    enhanced_prompt = enhanced_prompt.strip('`"\' ')
                    if len(enhanced_prompt) > 2000:
                        print("Warning: OpenAI enhanced prompt > 2000 chars, truncating.")
                        enhanced_prompt = enhanced_prompt[:2000] + "..."
                    print(f"OpenAI Enhancement Successful: '{enhanced_prompt}'")
                    return enhanced_prompt, None
                else: return None, "OpenAI returned empty content."
            else: return None, "OpenAI response missing expected message content."
        elif 'error' in response_json:
            error_info = response_json['error']
            print(f"OpenAI API Error: {error_info.get('type')} - {error_info.get('message')}")
            return None, f"OpenAI API Error: {error_info.get('message', 'Unknown API error')}"
        else:
            print(f"OpenAI response format unexpected: {response_json}")
            return None, "OpenAI response format unexpected."
    except requests.exceptions.Timeout:
        print("Error: Timeout connecting to OpenAI API.")
        return None, "Timeout connecting to enhancement service (OpenAI)."
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to OpenAI API: {e}")
        error_details = "Unknown connection error"
        if e.response is not None:
            status_code = e.response.status_code
            try: error_details = e.response.json().get('error', {}).get('message', e.response.text)
            except json.JSONDecodeError: error_details = e.response.text
            print(f"  Status Code: {status_code}, Details: {error_details}")
            if status_code == 400: return None, f"Invalid request to OpenAI ({error_details})."
            if status_code == 401: return None, "Authentication error with OpenAI (check API key)."
            if status_code == 403: return None, f"Permission error with OpenAI ({error_details})."
            if status_code == 429: return None, "Rate limit exceeded for OpenAI."
            error_details = f"OpenAI connection error ({status_code})."
        else: error_details = "Network error connecting to OpenAI."
        return None, error_details
    except Exception as e:
        print(f"Unexpected error during OpenAI enhancement: {e}")
        traceback.print_exc()
        return None, "Unexpected error during enhancement (OpenAI)."


async def enhance_prompt(original_prompt: str, system_prompt_text_override: str | None = None, target_model_type: str = "flux") -> tuple[str | None, str | None]:
    """
    Enhances a prompt using the configured LLM provider and model.
    Accepts an optional system_prompt_text_override.

    Args:
        original_prompt (str): The user's initial prompt.
        system_prompt_text_override (str | None): If provided, this system prompt text will be used.
                                                  Otherwise, a default is chosen based on target_model_type.
        target_model_type (str): "flux" or "sdxl", to select default system prompt if override is not given.

    Returns:
        tuple[str | None, str | None]: Enhanced prompt or None, error message or None.
    """
    try:
        from settings_manager import load_settings
    except ImportError:
        print("Error: Could not import settings_manager in llm_enhancer.")
        return None, "Internal configuration error (settings)."

    settings = load_settings()
    provider = settings.get('llm_provider', 'gemini')

    if not original_prompt or not isinstance(original_prompt, str):
        return None, "Invalid original prompt provided."

    system_instruction_to_use = system_prompt_text_override
    if not system_instruction_to_use:
        if target_model_type.lower() == "sdxl":
            system_instruction_to_use = SDXL_ENHANCER_SYSTEM_PROMPT
            if not system_instruction_to_use:
                print("LLMEnhancer Warning: SDXL system prompt is empty, falling back to Flux prompt.")
                system_instruction_to_use = FLUX_ENHANCER_SYSTEM_PROMPT
        else:
            system_instruction_to_use = FLUX_ENHANCER_SYSTEM_PROMPT
    
    if not system_instruction_to_use:
        print("LLMEnhancer CRITICAL: No system prompt text available. Using basic fallback.")
        system_instruction_to_use = "Enhance the following prompt for an image generation AI:"


    if provider == 'gemini':
        model_name = settings.get('llm_model_gemini', 'gemini-1.5-flash')
        return await _enhance_with_gemini(original_prompt, model_name, system_instruction_to_use)
    elif provider == 'groq':
        model_name = settings.get('llm_model_groq', 'llama3-8b-8192')
        return await _enhance_with_groq(original_prompt, model_name, system_instruction_to_use)
    elif provider == 'openai':
        model_name = settings.get('llm_model_openai', 'gpt-4o')
        return await _enhance_with_openai(original_prompt, model_name, system_instruction_to_use)
    else:
        print(f"Error: Unknown LLM provider configured: {provider}")
        return None, f"Unknown LLM provider '{provider}' selected in settings."
