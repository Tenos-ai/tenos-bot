# --- START OF FILE utils/prompt_utils.py ---
# utils/prompt_utils.py

import discord
from discord.ui import Button, View
import io

MAX_PROMPT_LENGTH = 300

def truncate_prompt_and_add_button(prompt):
    """
    Truncates a prompt string if it exceeds MAX_PROMPT_LENGTH and adds
    a button to view the full prompt in a text file via ephemeral message.

    Args:
        prompt (str): The full prompt text.

    Returns:
        tuple: (truncated_prompt_string, discord.ui.View | None)
               The view contains the button if the prompt was truncated.
    """
    truncated_prompt = prompt
    view = None

    if len(prompt) > MAX_PROMPT_LENGTH:
        truncated_prompt = prompt[:MAX_PROMPT_LENGTH].strip() + "..."
        button = Button(label="View Entire Prompt", style=discord.ButtonStyle.primary, custom_id="view_full_prompt")

        async def button_callback(interaction: discord.Interaction):
            if not prompt:
                 await interaction.response.send_message("Error: Cannot view an empty prompt.", ephemeral=True)
                 return

            try:
                prompt_bytes = io.BytesIO(prompt.encode('utf-8'))
                file = discord.File(fp=prompt_bytes, filename="full_prompt.txt")
                await interaction.response.send_message("Full prompt text:", file=file, ephemeral=True)
            except Exception as e:
                 print(f"Error creating/sending full prompt file: {e}")
                 await interaction.response.send_message("Sorry, could not display the full prompt.", ephemeral=True)

        button.callback = button_callback
        view = View(timeout=None)
        view.add_item(button)

    return truncated_prompt, view

def create_truncated_response(user_mention, prompt, additional_info=""):
    """
    Creates a response string with a potentially truncated prompt and a view
    containing a button to see the full prompt if truncated.

    Args:
        user_mention (str): The user mention string.
        prompt (str): The full prompt text.
        additional_info (str, optional): Extra text to append after the prompt part. Defaults to "".

    Returns:
        tuple: (response_string, discord.ui.View | None)
    """
    truncated_prompt, view = truncate_prompt_and_add_button(prompt)
    response = f"{user_mention}: Your prompt `{truncated_prompt}` has been queued"
    if additional_info:
        response += f" {additional_info}"
    return response, view
# --- END OF FILE utils/prompt_utils.py ---