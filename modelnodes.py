import json
import os
import traceback

def load_model_node_templates():
    default_templates = {
        "MODELNODES": {
            "GGUF_GENERATION": {
                "NODE_NUMBER": {
                    "inputs": {"unet_name": "model_file_name"},
                    "class_type": "UnetLoaderGGUF",
                    "_meta": {"title": "Unet Loader (GGUF)"}
                }
            },
            "SAFETENSORS_GENERATION": {
                 "NODE_NUMBER": {
                    "inputs": {"unet_name": "model_file_name", "weight_dtype": "default"},
                    "class_type": "UNETLoader",
                    "_meta": {"title": "Load Diffusion Model"}
                }
            },
            "SDXL_CHECKPOINT_GENERATION": {
                "NODE_NUMBER": {
                    "inputs": {"ckpt_name": "model_file_name"},
                    "class_type": "CheckpointLoaderSimple",
                    "_meta": {"title": "Load Checkpoint"}
                }
            },
            "QWEN_IMAGE_GENERATION": {
                "NODE_NUMBER": {
                    "inputs": {"ckpt_name": "model_file_name"},
                    "class_type": "CheckpointLoaderSimple",
                    "_meta": {"title": "Load Qwen Checkpoint"}
                }
            }
        }
    }
    try:
        if not os.path.exists('modelnodes.json'):
            print("Error: modelnodes.json not found. Creating default templates.")
            with open('modelnodes.json', 'w') as f:
                json.dump(default_templates, f, indent=2)
            return default_templates
        with open('modelnodes.json', 'r') as f:
            templates = json.load(f)

        if not isinstance(templates, dict) or "MODELNODES" not in templates:
            print("Error: Invalid structure in modelnodes.json. Using default templates.")
            return default_templates

        missing_keys = []
        for key_name in ("SDXL_CHECKPOINT_GENERATION", "QWEN_IMAGE_GENERATION"):
            if key_name not in templates["MODELNODES"]:
                print(f"Warning: {key_name} template missing. Adding default.")
                templates["MODELNODES"][key_name] = default_templates["MODELNODES"][key_name]
                missing_keys.append(key_name)
        if missing_keys:
            try:
                with open('modelnodes.json', 'w') as f:
                    json.dump(templates, f, indent=2)
            except Exception as e_write:
                print(f"Error writing updated modelnodes.json: {e_write}")
        return templates
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error loading modelnodes.json: {e}. Using default templates.")
        return default_templates
    except Exception as e:
        print(f"Unexpected error loading modelnodes.json: {e}")
        traceback.print_exc()
        return default_templates

model_node_templates = load_model_node_templates()

def get_model_node(model_name_with_prefix: str, node_number_str: str):
    try:
        templates = model_node_templates
        model_type_lc = None 
        actual_model_name = model_name_with_prefix 

        norm_model_name_with_prefix = model_name_with_prefix.strip()

        if norm_model_name_with_prefix.upper().startswith("FLUX:"):
            model_type_lc = "flux"
            actual_model_name = norm_model_name_with_prefix[len("FLUX:"):].strip()
        elif norm_model_name_with_prefix.upper().startswith("SDXL:"):
            model_type_lc = "sdxl"
            actual_model_name = norm_model_name_with_prefix[len("SDXL:"):].strip()
        elif norm_model_name_with_prefix.upper().startswith("QWEN:"):
            model_type_lc = "qwen"
            actual_model_name = norm_model_name_with_prefix[len("QWEN:"):].strip()
        else:
            actual_model_name = norm_model_name_with_prefix
            print(f"Warning: Model '{norm_model_name_with_prefix}' has no recognized type prefix. Inferring from extension.")
            if actual_model_name.lower().endswith((".gguf", ".sft")):
                model_type_lc = "flux"
            elif actual_model_name.lower().endswith((".safetensors", ".ckpt", ".pth")):
                print(f"Assuming SDXL for extension on '{actual_model_name}' due to missing prefix.")
                model_type_lc = "sdxl"
            else:
                raise ValueError(f"Unsupported model type or missing prefix and cannot infer from extension: {actual_model_name}")

        template_key = None
        input_key_for_model_name = "unet_name"

        if model_type_lc == "flux":
            if actual_model_name.lower().endswith('.gguf'):
                template_key = 'GGUF_GENERATION'
            elif actual_model_name.lower().endswith('.safetensors') or actual_model_name.lower().endswith('.sft'):
                template_key = 'SAFETENSORS_GENERATION'
            else:
                raise ValueError(f"Unsupported Flux model extension for '{actual_model_name}'")
            input_key_for_model_name = "unet_name"
        elif model_type_lc == "sdxl":
            template_key = 'SDXL_CHECKPOINT_GENERATION'
            input_key_for_model_name = "ckpt_name"
        elif model_type_lc == "qwen":
            template_key = 'QWEN_IMAGE_GENERATION'
            input_key_for_model_name = "ckpt_name"
        else:
             raise ValueError(f"Internal error: model_type_lc '{model_type_lc}' not recognized.")


        if 'MODELNODES' not in templates or template_key not in templates['MODELNODES']:
            raise KeyError(f"Missing '{template_key}' configuration in modelnodes.json")

        template_section = templates['MODELNODES'][template_key]
        if not template_section or not isinstance(template_section, dict):
             raise KeyError(f"Invalid structure for '{template_key}' in modelnodes.json")

        placeholder_key = next(iter(template_section))
        node_template = template_section[placeholder_key]
        node = json.loads(json.dumps(node_template))

        if "inputs" in node and isinstance(node["inputs"], dict):
             node['inputs'][input_key_for_model_name] = actual_model_name
        else:
             node['inputs'] = {input_key_for_model_name: actual_model_name}

        return {str(node_number_str): node}

    except (KeyError, ValueError) as e:
        print(f"Error in get_model_node for '{model_name_with_prefix}': {e}")
        raise
    except Exception as e:
        print(f"Unexpected error in get_model_node for model '{model_name_with_prefix}': {e}")
        traceback.print_exc()
        raise
