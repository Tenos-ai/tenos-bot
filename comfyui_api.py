import json
from urllib import request, error
import ssl
import os
import requests 
import traceback
import time
from socket import error as SocketError
from urllib.error import URLError
from websocket_client import get_initialized_websocket_client

class ConnectionRefusedError(Exception):
    """Custom exception for connection refused errors."""
    pass

try:
    if not os.path.exists('config.json'):
        raise FileNotFoundError("config.json not found.")
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
    if not isinstance(config, dict):
         raise ValueError("config.json is not a valid dictionary.")
    COMFYUI_HOST = config.get('COMFYUI_HOST', '127.0.0.1')
    COMFYUI_PORT = config.get('COMFYUI_PORT', 8188)
    if not isinstance(COMFYUI_PORT, int):
        try:
            COMFYUI_PORT = int(COMFYUI_PORT)
        except (ValueError, TypeError):
            print(f"Warning: Invalid COMFYUI_PORT '{COMFYUI_PORT}' in config. Using default 8188.")
            COMFYUI_PORT = 8188
except (FileNotFoundError, json.JSONDecodeError, ValueError, TypeError) as e:
    print(f"ERROR loading config.json in comfyui_api: {e}")
    COMFYUI_HOST = '127.0.0.1'
    COMFYUI_PORT = 8188
except Exception as e:
    print(f"UNEXPECTED ERROR loading config.json in comfyui_api: {e}")
    traceback.print_exc()
    COMFYUI_HOST = '127.0.0.1'
    COMFYUI_PORT = 8188

def update_last_prompt(prompt):
    try:
        with open('lastprompt.json', 'w') as f:
            json.dump(prompt, f, indent=2)
    except Exception as e:
        print(f"Error updating lastprompt.json: {e}")
        traceback.print_exc()

def validate_prompt_before_sending(prompt_dict):
    if not isinstance(prompt_dict, dict):
        return False, "Prompt is not a dictionary."

    try:
        for node_id, node in prompt_dict.items():
            if not isinstance(node, dict):
                 return False, f"Node {node_id} is not a dictionary."
            if "inputs" not in node:
                return False, f"Node {node_id} missing 'inputs' field"
            if not isinstance(node["inputs"], dict):
                return False, f"Node {node_id} 'inputs' field is not a dictionary."

            for key, value in node["inputs"].items():
                if key in ["text", "filename_prefix", "url_or_path"] and value is None:
                    node["inputs"][key] = ""
                elif key in ["seam_fix_mode"] and value == "None":
                     pass

            if "filename_prefix" in node["inputs"]:
                path = node["inputs"]["filename_prefix"]
                if isinstance(path, str) and "\\" in path:
                    if path.startswith('\\\\'):
                        fixed_path = '\\\\' + path[2:].replace("\\", "/")
                    else:
                        fixed_path = path.replace("\\", "/")
                    node["inputs"]["filename_prefix"] = fixed_path

        return True, None
    except Exception as e:
        print(f"Error during prompt validation: {e}")
        traceback.print_exc()
        return False, f"Prompt validation error: {str(e)}"


def queue_prompt(prompt, comfyui_host=COMFYUI_HOST, comfyui_port=COMFYUI_PORT, ignore_ssl_verify=False):
    response_data = ""
    try:
        is_valid, error_msg = validate_prompt_before_sending(prompt)
        if not is_valid:
            print(f"Error validating prompt: {error_msg}")
            update_last_prompt({"error": "Validation Failed", "message": error_msg, "invalid_prompt": prompt})
            return None

        update_last_prompt(prompt)

        ws_client = get_initialized_websocket_client()
        client_id = ws_client.client_id if ws_client and ws_client.is_connected else None
        
        p = {"prompt": prompt}
        if client_id:
            p['client_id'] = client_id
            print(f"Queueing prompt with WebSocket client ID: {client_id}")
        else:
            print("Warning: Queueing prompt without WebSocket client ID. Progress updates will not work.")
        data = json.dumps(p, ensure_ascii=False).encode('utf-8')
        api_url = f"http://{comfyui_host}:{comfyui_port}/prompt"
        req = request.Request(api_url, data=data, headers={'Content-Type': 'application/json'})

        ctx = ssl._create_unverified_context() if ignore_ssl_verify else None
        response = None

        try:
            response = request.urlopen(req, timeout=20)
        except error.URLError as e_url:
             if isinstance(e_url.reason, SocketError) and e_url.reason.errno == 111: 
                 print(f"ERROR: Connection refused at {api_url}. Is ComfyUI running?")
                 raise ConnectionRefusedError(f"Connection refused at {api_url}") from e_url
             elif isinstance(e_url.reason, OSError) and hasattr(e_url.reason, 'winerror') and e_url.reason.winerror == 10061: 
                  print(f"ERROR: Connection refused at {api_url}. Is ComfyUI running?")
                  raise ConnectionRefusedError(f"Connection refused at {api_url}") from e_url
             elif isinstance(e_url.reason, ssl.SSLCertVerificationError):
                 print("SSL verification failed. Trying with unverified context...")
                 if ctx:
                     try:
                         response = request.urlopen(req, context=ctx, timeout=20)
                         print("Successfully connected using unverified context.")
                     except error.URLError as inner_err:
                         if isinstance(inner_err.reason, SocketError) and inner_err.reason.errno == 111: 
                             print(f"ERROR: Connection refused at {api_url} (SSL fallback).")
                             raise ConnectionRefusedError(f"Connection refused at {api_url} (SSL fallback)") from inner_err
                         elif isinstance(inner_err.reason, OSError) and hasattr(inner_err.reason, 'winerror') and inner_err.reason.winerror == 10061: # type: ignore
                             print(f"ERROR: Connection refused at {api_url} (SSL fallback).")
                             raise ConnectionRefusedError(f"Connection refused at {api_url} (SSL fallback)") from inner_err
                         else:
                             print(f"Failed even with unverified context: {inner_err.reason}")
                             raise inner_err
                     except Exception as e_unverified:
                          print(f"Unexpected error during SSL fallback: {e_unverified}")
                          raise e_unverified
                 else:
                     print("SSL error occurred but ignore_ssl_verify is False. Cannot proceed.")
                     raise e_url
             else:
                  print(f"URLError during ComfyUI request: {e_url.reason}")
                  raise e_url
        except ConnectionRefusedError: 
             raise

        if response is None:
            print("Error: Could not get a valid response from ComfyUI API (response is None).")
            return None

        response_data = response.read().decode('utf-8')
        response_json = json.loads(response_data)

        if 'prompt_id' in response_json:
            print(f"Successfully queued prompt. ComfyUI Prompt ID: {response_json['prompt_id']}")
            return response_json['prompt_id']
        elif 'error' in response_json:
            print(f"Error from ComfyUI API: {response_json['error']}")
            if 'node_errors' in response_json:
                 print(f"Node Errors: {json.dumps(response_json['node_errors'], indent=2)}")
                 error_prompt = prompt.copy()
                 error_prompt["__COMFYUI_ERROR__"] = response_json
                 update_last_prompt(error_prompt)
            return None
        else:
            print(f"Unexpected response from ComfyUI API: {response_data}")
            error_prompt = prompt.copy()
            error_prompt["__COMFYUI_UNEXPECTED_RESPONSE__"] = response_data
            update_last_prompt(error_prompt)
            return None

    except ConnectionRefusedError:
        raise 
    except error.URLError as e:
        print(f"Error sending prompt (URLError): {e.reason} at {api_url}. Is ComfyUI running/reachable?");
        raise Exception(f"Network error connecting to ComfyUI: {e.reason}") from e
    except error.HTTPError as e:
         print(f"Error sending prompt (HTTPError): {e.code} {e.reason} at {api_url}")
         try: print(f"Response body: {e.read().decode()}")
         except: pass
         raise Exception(f"HTTP error from ComfyUI ({e.code}): {e.reason}") from e
    except json.JSONDecodeError as e_json: 
         print(f"Error decoding ComfyUI API response: {e_json}"); print(f"Received: {response_data}");
         raise Exception("Invalid response from ComfyUI API.") from e_json
    except requests.exceptions.Timeout: 
        print(f"Error: Request timed out connecting to {api_url}.");
        raise Exception(f"Timeout connecting to ComfyUI at {api_url}.") 
    except Exception as e_final: 
        print(f"Unexpected error sending prompt: {type(e_final).__name__} - {e_final}"); traceback.print_exc();
        raise


def _extract_and_flatten_options(data_source):
    options_list = []
    if isinstance(data_source, list):
        potential_options = data_source
    elif isinstance(data_source, dict):
        potential_options = data_source.get("options", [])
        if not isinstance(potential_options, list):
             potential_options = []
    else:
        potential_options = []

    for item in potential_options:
        if isinstance(item, str):
            options_list.append(item)
        elif isinstance(item, list): 
            for sub_item in item:
                if isinstance(sub_item, str):
                    options_list.append(sub_item)
    return list(set(options_list))


def get_available_comfyui_models(host=COMFYUI_HOST, port=COMFYUI_PORT, suppress_summary_print=False):
    final_unet_list = [] 
    final_checkpoint_list = [] 
    final_clip_list = []
    final_vae_list = []
    final_upscaler_list = [] 
    max_retries = 3
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            api_url = f"http://{host}:{port}/object_info"
            response = requests.get(api_url, timeout=15)
            response.raise_for_status()
            data = response.json()

            unet_sources = {
                "UnetLoaderGGUF": "unet_name",
                "UNETLoader": "unet_name",
            }
            temp_unet_list = []
            for loader_name, field_name in unet_sources.items():
                if loader_name in data:
                    loader_data = data.get(loader_name, {})
                    input_data = loader_data.get("input", {})
                    required_data = input_data.get("required", {})
                    if field_name in required_data:
                        options_data = required_data.get(field_name, [])
                        temp_unet_list.extend(_extract_and_flatten_options(options_data))
            final_unet_list = sorted(list(set(temp_unet_list)), key=str.lower)

            if "CheckpointLoaderSimple" in data:
                loader_data = data.get("CheckpointLoaderSimple", {})
                input_data = loader_data.get("input", {})
                required_data = input_data.get("required", {})
                if "ckpt_name" in required_data:
                    options_data = required_data.get("ckpt_name", [])
                    final_checkpoint_list = sorted(_extract_and_flatten_options(options_data), key=str.lower)


            temp_clip_list = []
            clip_sources = { 
                "DualCLIPLoader": ["clip_name1", "clip_name2"],
                "CLIPSetLastLayer": ["clip_name"], 
                "CheckpointLoaderSimple": ["ckpt_name"] 
            }
            for loader_name, field_names in clip_sources.items():
                 if loader_name in data:
                     loader_data = data.get(loader_name, {})
                     input_data = loader_data.get("input", {})
                     required_data = input_data.get("required", {})
                     for field_name in field_names:
                          if field_name in required_data:
                              options_data = required_data.get(field_name, [])
                              temp_clip_list.extend(_extract_and_flatten_options(options_data))
            final_clip_list = sorted(list(set(temp_clip_list)), key=str.lower)

            temp_vae_list = []
            vae_sources = {
                "VAELoader": ["vae_name"],
                "CheckpointLoaderSimple": ["ckpt_name"] 
            }
            for loader_name, field_names in vae_sources.items():
                 if loader_name in data:
                     loader_data = data.get(loader_name, {})
                     input_data = loader_data.get("input", {})
                     required_data = input_data.get("required", {})
                     for field_name in field_names:
                          if field_name in required_data:
                              options_data = required_data.get(field_name, [])
                              temp_vae_list.extend(_extract_and_flatten_options(options_data))
            final_vae_list = sorted(list(set(temp_vae_list)), key=str.lower)

            if "UpscaleModelLoader" in data:
                loader_data = data.get("UpscaleModelLoader", {})
                input_data = loader_data.get("input", {})
                required_data = input_data.get("required", {})
                if "model_name" in required_data:
                    options_data = required_data.get("model_name", [])
                    final_upscaler_list = sorted(_extract_and_flatten_options(options_data), key=str.lower)

            if not suppress_summary_print:
                print(f"ComfyAPI: Found {len(final_unet_list)} UNETs (Flux), {len(final_checkpoint_list)} Checkpoints (SDXL), {len(final_clip_list)} CLIPs, {len(final_vae_list)} VAEs, {len(final_upscaler_list)} Upscalers.")
            break 

        except requests.exceptions.Timeout:
            print(f"Attempt {attempt+1}/{max_retries}: Timeout connecting to ComfyUI API at {api_url}.")
            if attempt == max_retries - 1: print("Max retries reached. Could not connect.")
            else: time.sleep(retry_delay)
        except requests.exceptions.ConnectionError:
             print(f"Attempt {attempt+1}/{max_retries}: Connection error connecting to ComfyUI API at {api_url}. Is ComfyUI running?")
             if attempt == max_retries - 1: print("Max retries reached. Could not connect.")
             else: time.sleep(retry_delay)
        except requests.exceptions.RequestException as e_req: 
            print(f"Attempt {attempt+1}/{max_retries}: Error connecting to ComfyUI API at {api_url}: {e_req}")
            if attempt == max_retries - 1: print("Max retries reached. Giving up.")
            else: time.sleep(retry_delay)
        except json.JSONDecodeError as e_json_decode: 
            print(f"Error decoding ComfyUI API response from {api_url}: {e_json_decode}. Maybe ComfyUI is starting?")
            break 
        except Exception as e_generic: 
            print(f"Error getting available ComfyUI models: {e_generic}")
            traceback.print_exc()
            break 

    return {
        "unet": final_unet_list,
        "checkpoint": final_checkpoint_list, 
        "clip": final_clip_list,
        "vae": final_vae_list,
        "upscaler": final_upscaler_list
    }


def print_available_models(host=COMFYUI_HOST, port=COMFYUI_PORT): 
    try:
        api_url = f"http://{host}:{port}/object_info"
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()

        print("\n=== Available Models (from ComfyUI API - Explicit Print) ===")

        def print_options_detailed(loader_name, field_name, title_override=None):
            print(f"\n--- {title_override or (loader_name + ' / ' + field_name)} ---")
            options_list = []
            if loader_name in data:
                loader_data = data.get(loader_name, {})
                input_data = loader_data.get("input", {})
                target_input_section = None 
                if field_name in input_data.get("required", {}):
                     target_input_section = input_data["required"]
                elif field_name in input_data.get("optional", {}): 
                     target_input_section = input_data["optional"]

                if target_input_section and field_name in target_input_section:
                    options_data = target_input_section.get(field_name, [])
                    options_list = _extract_and_flatten_options(options_data)
                else: print(f"(Field '{field_name}' not found in required/optional inputs of '{loader_name}')")
            else: print(f"(Loader '{loader_name}' not found in API response)")

            if options_list:
                 for model in sorted(options_list, key=str.lower): print(f"- {model}")
            else: print("(No options listed or extracted for this field)")

        print_options_detailed("UnetLoaderGGUF", "unet_name", title_override="Flux Models (GGUF)")
        print_options_detailed("UNETLoader", "unet_name", title_override="Flux Models (Safetensors/SFT)")
        print_options_detailed("CheckpointLoaderSimple", "ckpt_name", title_override="SDXL Checkpoints (also provide CLIP/VAE)")
        print_options_detailed("DualCLIPLoader", "clip_name1", title_override="CLIP Models (T5/CLIP-G type via DualCLIPLoader)")
        print_options_detailed("DualCLIPLoader", "clip_name2", title_override="CLIP Models (CLIP-L type via DualCLIPLoader)")
        print_options_detailed("VAELoader", "vae_name", title_override="Standalone VAE Models")
        print_options_detailed("UpscaleModelLoader", "model_name", title_override="Upscaler Models")


        print("\n--- UltimateSDUpscale / seam_fix_mode ---")
        if "UltimateSDUpscale" in data:
            usdu_data = data.get("UltimateSDUpscale", {})
            usdu_input = usdu_data.get("input", {})
            usdu_req = usdu_input.get("required", {})
            if "seam_fix_mode" in usdu_req:
                 sf_options_data = usdu_req.get("seam_fix_mode", [])
                 sf_options = _extract_and_flatten_options(sf_options_data)
                 if sf_options: print(f"Seam fix modes: {', '.join(sf_options)}")
                 else: print("(No seam_fix_mode options found)")
            else: print("(seam_fix_mode field not found in UltimateSDUpscale)")
        else: print("(UltimateSDUpscale node info not found)")


        print("\n========================================================")

    except requests.exceptions.RequestException as e_req_print: 
        print(f"Error connecting to ComfyUI API at {api_url} to print models: {e_req_print}")
    except Exception as e_print: 
        print(f"Error printing available models: {e_print}")
        traceback.print_exc()
