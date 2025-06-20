# --- START OF FILE utils/seed_utils.py ---
import random
import re
from time import time

def generate_seed():
    """
    Generate a random seed for image generation.
    Uses a mix of time() and random to ensure uniqueness.
    """
    seed_base = int(time() * 1000) + random.randint(0, 999999)
    return seed_base % 10**15

def parse_seed_from_message(message_content, default_seed=None):
    """
    Extracts a seed value (--seed N) from a message string.

    Args:
        message_content (str): The message text to parse.
        default_seed (int, optional): Default seed value if none found in message.

    Returns:
        int: The extracted seed or default_seed. Returns default_seed if parsing fails.
    """
    if not message_content or not isinstance(message_content, str):
        return default_seed

    match = re.search(r'--seed\s+(\d+)\b', message_content, re.IGNORECASE)
    if match:
        try:
            seed_val = int(match.group(1))
            return seed_val
        except ValueError:
            print(f"Warning: Invalid integer value found after --seed: {match.group(1)}")
            return default_seed

    return default_seed


def calculate_batch_seeds(base_seed, batch_size=1):
    """
    Calculates an array of seeds for a batch, starting from a base seed.
    Each subsequent seed is incremented by 1.

    Args:
        base_seed (int): The starting seed value for the batch
        batch_size (int): Number of seeds to generate (1-10)

    Returns:
        list: A list of seed values [base_seed, base_seed+1, ...]
    """
    if not isinstance(base_seed, int):
        print("Warning: calculate_batch_seeds received non-integer base_seed. Generating random.")
        base_seed = generate_seed()
    if not isinstance(batch_size, int) or not (1 <= batch_size <= 10):
        print(f"Warning: calculate_batch_seeds received invalid batch_size ({batch_size}). Using 1.")
        batch_size = 1

    return [base_seed + i for i in range(batch_size)]


def add_or_replace_seed_in_prompt(prompt_text, seed_value):
    """
    Adds or replaces a seed value in a prompt string.

    Args:
        prompt_text (str): The original prompt text
        seed_value (int): The seed value to set

    Returns:
        str: Updated prompt with the seed parameter
    """
    seed_param = re.search(r'--seed\s+\d+\b', prompt_text, re.IGNORECASE)
    if seed_param:
        return re.sub(r'--seed\s+\d+\b', f'--seed {seed_value}', prompt_text, flags=re.IGNORECASE)
    else:
        return f"{prompt_text.strip()} --seed {seed_value}"
# --- END OF FILE utils/seed_utils.py ---