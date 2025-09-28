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

DEFAULT_QWEN_IMAGE_EDIT_PROMPT = (
    "You are a Qwen Image Edit director. You receive a user's instruction and one reference image. "
    "Rewrite the instruction as a clear description of the desired final image, explicitly preserving key "
    "subjects, composition, lighting, and style from the source. Mention any additions or removals as if "
    "they already occurred and keep the tone concise and professional."
)

def load_llm_prompts_config():
    """Loads llm_prompts.json safely and ensures all necessary keys exist."""
    default_flux_prompt = "Your designated function is Flux Prompt Alchemist..." # Collapsed for brevity
    default_sdxl_prompt = "You are a master prompt artist for Illustrious XL..." # Collapsed for brevity
    default_kontext_prompt = "You are a Kontext Instruction Alchemist..." # Collapsed for brevity

    default_config = {
        "enhancer_system_prompt": default_flux_prompt,
        "enhancer_system_prompt_sdxl": default_sdxl_prompt,
        "enhancer_system_prompt_kontext": default_kontext_prompt,
        "enhancer_system_prompt_qwen_edit": DEFAULT_QWEN_IMAGE_EDIT_PROMPT,
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
QWEN_IMAGE_EDIT_ENHANCER_SYSTEM_PROMPT = llm_prompts_config.get(
    "enhancer_system_prompt_qwen_edit", DEFAULT_QWEN_IMAGE_EDIT_PROMPT
)

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

    incompatible_keywords = ['tts', 'image-generation']
    if any(keyword in model_name for keyword in incompatible_keywords):
        return None, f"Model '{model_name}' is not suitable for prompt enhancement. Please select a text or multimodal generation model."

    if image_urls and "vision" not in model_name and "flash" not in model_name and "pro" not in model_name:
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
        response = await asyncio.to_thread(requests.post, API_URL, headers=headers, params=params, json=payload, timeout=90)
        response.raise_for_status()
        response_json = response.json()
        
        if 'candidates' in response_json and response_json['candidates']:
            enhanced_prompt = response_json['candidates'][0].get('content', {}).get('parts', [{}])[0].get('text', '').strip()
            return enhanced_prompt.strip('`"\' '), None

        return None, f"Google Gemini API response format unexpected or empty. Full response: {response_json}"
    except Exception as e:
        return None, f"Error with Gemini API: {e}"

async def _enhance_with_groq(original_prompt: str, model_name: str, system_instruction_text: str, reasoning_effort: str | None, image_urls: list | None = None) -> tuple[str | None, str | None]:
    if not GROQ_API_KEY:
        return None, "Groq API key is missing in config.json."
    
    incompatible_keywords = ['whisper', 'tts', 'guard']
    if any(keyword in model_name for keyword in incompatible_keywords):
        return None, f"Model '{model_name}' is not suitable for prompt enhancement. Please select a text generation model."

    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    headers = {'Authorization': f'Bearer {GROQ_API_KEY}', 'Content-Type': 'application/json'}
    
    payload = {
        "messages": [{"role": "system", "content": system_instruction_text}, {"role": "user", "content": original_prompt}],
        "model": model_name,
        "temperature": 1,
        "max_tokens": 2048
    }

    if "gpt-oss" in model_name and reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort

    try:
        response = await asyncio.to_thread(requests.post, API_URL, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        response_json = response.json()
        if 'choices' in response_json and response_json['choices']:
            enhanced_prompt = response_json['choices'][0].get('message', {}).get('content', '').strip()
            return enhanced_prompt.strip('`"\' '), None
        return None, f"Groq response format unexpected: {response_json}"
    except Exception as e:
        return None, f"Error with Groq API: {e}"

async def _enhance_with_openai(original_prompt: str, model_name: str, system_instruction_text: str, image_urls: list | None = None) -> tuple[str | None, str | None]:
    if not OPENAI_API_KEY:
        return None, "OpenAI API key is missing."

    incompatible_keywords = ['-tts', '-transcribe', '-audio', '-realtime', '-search', '-instruct']
    if any(keyword in model_name for keyword in incompatible_keywords):
        return None, f"Model '{model_name}' is not suitable for prompt enhancement. Please select a text generation model."

    headers = {'Authorization': f'Bearer {OPENAI_API_KEY}', 'Content-Type': 'application/json'}
    payload = {}
    API_URL = ""

    if any(model_name.startswith(pref) for pref in ('o1','o3','o4','gpt-4.1','gpt-5')):
        API_URL = "https://api.openai.com/v1/responses"
        payload = {
            "model": model_name,
            "input": [{"role": "user", "content": original_prompt}],
            "instructions": system_instruction_text,
        }
        if image_urls:
             print(f"LLMEnhancer Warning: Image URLs are currently ignored for OpenAI o-series models.")

    else:
        API_URL = "https://api.openai.com/v1/chat/completions"
        # Determine if the model supports multimodal input (i.e., Vision)
        is_vision_model = model_name in ["gpt-4o", "gpt-4-turbo", "gpt-4o-mini"] or "vision" in model_name
        
        # Default to simple text content for the user message
        user_content = original_prompt
        
        # Build a multimodal payload only when the model supports it
        if image_urls and is_vision_model:
            user_content = [{"type": "text", "text": original_prompt}]
            for url in image_urls:
                user_content.append({"type": "image_url", "image_url": {"url": url}})
        elif image_urls:
            # Warn the caller that the images will be ignored
            print(f"LLMEnhancer Warning: Image URLs are ignored for non‑vision OpenAI model '{model_name}'.")
        
        # Newer reasoning models (o‑series, gpt‑4.1+, gpt‑5+) expect 'max_completion_tokens'
        reasoning_models = ('gpt-5', 'gpt-4.1', 'o1', 'o3', 'o4')
        token_key = "max_completion_tokens" if any(rm in model_name for rm in reasoning_models) else "max_tokens"
        
        payload = {
            "model": model_name,
            "messages": [{"role": "system", "content": system_instruction_text},
                         {"role": "user", "content": user_content}],
            token_key: 2048
        }
        
    try:
        response = await asyncio.to_thread(requests.post, API_URL, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        response_json = response.json()
        
        # **FIX START**: Correct parsing logic for both API response types.
        enhanced_prompt = None
        # Standard API parsing
        if 'choices' in response_json and response_json['choices']:
            enhanced_prompt = response_json['choices'][0].get('message', {}).get('content', '')

        # /v1/responses API parsing
        elif 'output' in response_json and isinstance(response_json['output'], list):
            for part in response_json['output']:
                if part.get('type') == 'message' and part.get('content'):
                    for content_item in part['content']:
                        if content_item.get('type') == 'output_text' and content_item.get('text'):
                            enhanced_prompt = content_item['text']
                            break  # Found the text, no need to look further
                if enhanced_prompt:
                    break
        
        if enhanced_prompt:
            return enhanced_prompt.strip('`"\' '), None
        # **FIX END**

        return None, f"OpenAI response format unexpected: {json.dumps(response_json)}" # Log the full unexpected response
    except Exception as e:
        if isinstance(e, requests.HTTPError):
            error_body = e.response.text
            if e.response.status_code == 404:
                return None, f"Error with OpenAI API (404 Not Found): The model '{model_name}' does not exist or you do not have access to it."
            elif e.response.status_code == 400:
                return None, f"Error with OpenAI API (400 Bad Request): The data sent to '{API_URL}' for model '{model_name}' was invalid. Full error: {error_body}"
        return None, f"Error with OpenAI API: {e}"

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
        elif target_model_type.lower() == "qwen_edit":
            system_instruction_to_use = QWEN_IMAGE_EDIT_ENHANCER_SYSTEM_PROMPT
        else:
            system_instruction_to_use = FLUX_ENHANCER_SYSTEM_PROMPT
    
    if not system_instruction_to_use:
        system_instruction_to_use = "Enhance the following text for an image generation AI:"

    if provider == 'gemini':
        model_name = settings.get('llm_model_gemini', 'gemini-1.5-flash-latest')
        return await _enhance_with_gemini(final_prompt_for_llm, model_name, system_instruction_to_use, image_urls)
    elif provider == 'groq':
        model_name = settings.get('llm_model_groq', 'llama3-8b-8192')
        reasoning_effort = settings.get('llm_groq_reasoning_effort', None)
        return await _enhance_with_groq(final_prompt_for_llm, model_name, system_instruction_to_use, reasoning_effort, image_urls)
    elif provider == 'openai':
        model_name = settings.get('llm_model_openai', 'gpt-4o')
        return await _enhance_with_openai(final_prompt_for_llm, model_name, system_instruction_to_use, image_urls)
    else:
        return None, f"Unknown LLM provider '{provider}' selected in settings."
