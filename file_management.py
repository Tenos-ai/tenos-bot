# --- START OF FILE file_management.py ---
import os
import discord
import re
import json
from queue_manager import queue_manager
import traceback

try:
    if not os.path.exists('config.json'):
        print("FATAL ERROR: config.json not found in file_management.py. The bot cannot function without it.")
        config = {"OUTPUTS": {}} 
    else:
        with open('config.json', 'r') as config_file:
            config = json.load(config_file)
    
    OUTPUT_FOLDERS = [
        config.get('OUTPUTS', {}).get('GENERATIONS'),
        config.get('OUTPUTS', {}).get('UPSCALES'),
        config.get('OUTPUTS', {}).get('VARIATIONS')
    ]
    OUTPUT_FOLDERS = [f for f in OUTPUT_FOLDERS if f and isinstance(f, str)]
    if not OUTPUT_FOLDERS:
        print("Warning: No valid output folders found in config.json for file_management.")
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"Error loading config.json in file_management: {e}")
    config = {"OUTPUTS": {}}
    OUTPUT_FOLDERS = []
except Exception as e:
    print(f"Unexpected error loading config in file_management: {e}")
    config = {"OUTPUTS": {}}
    OUTPUT_FOLDERS = []


def extract_job_id(filename):
    if not filename:
        return None

    # Standardized prefixes:
    # GEN_UP_ + job_id
    # GEN_VAR_ + job_id
    # GEN_I2I_ + job_id (for img2img generations)
    # GEN_ + job_id (for text2img generations)
    
    # Regex to capture the 8-character hex job ID after one of the standard prefixes
    # It ensures the prefix is at the beginning of the filename (^)
    # and that the job ID is exactly 8 hex characters.
    match = re.search(
        r'^(GEN_UP_|GEN_VAR_|GEN_I2I_|GEN_)([a-f0-9]{8})',
        filename, re.IGNORECASE
    )
    
    if match:
        return match.group(2) # Group 2 is the job_id
        
    # print(f"DEBUG extract_job_id: No specific pattern matched for '{filename}'")
    return None


def find_all_files_for_job(job_id):
    found_files = []
    if not job_id:
        return found_files

    job_id_lower = job_id.lower()

    for folder in OUTPUT_FOLDERS:
        if not folder or not os.path.isdir(folder):
            continue
        try:
            abs_folder = os.path.abspath(folder)
        except Exception as e_abs:
            print(f"Error processing folder path '{folder}': {e_abs}")
            continue

        try:
            for filename in os.listdir(abs_folder):
                extracted_id = extract_job_id(filename)
                if extracted_id and extracted_id.lower() == job_id_lower:
                    full_path = os.path.join(abs_folder, filename)
                    if os.path.isfile(full_path):
                        norm_path = os.path.normpath(full_path)
                        if norm_path not in found_files:
                            found_files.append(norm_path)
        except OSError as e:
            print(f"Error accessing folder {abs_folder}: {e}")
        except Exception as e:
            print(f"Unexpected error searching folder {abs_folder}: {e}")
            traceback.print_exc()
    return found_files


async def delete_job_files_and_message(job_id: str, message: discord.Message, interaction: discord.Interaction = None):
    delete_success = False
    file_feedback = ""
    message_deleted = False
    message_error = None

    if not job_id:
        print("Delete error: No job_id provided.")
        if interaction:
            try:
                if interaction.response.is_done():
                    await interaction.followup.send("Error: Cannot delete without Job ID.", ephemeral=True)
                else:
                    await interaction.response.send_message("Error: Cannot delete without Job ID.", ephemeral=True)
            except discord.NotFound: 
                if message and message.channel: await message.channel.send("Error: Cannot delete without Job ID (interaction expired).", delete_after=10)
            except Exception as e_int_send: print(f"Error sending no job_id feedback via interaction: {e_int_send}")
        elif message and message.channel:
            await message.channel.send("Error: Cannot delete without Job ID.", delete_after=10)
        return False

    files_to_delete = find_all_files_for_job(job_id)
    deleted_count = 0
    failed_count = 0

    if files_to_delete:
        print(f"Found {len(files_to_delete)} files for job {job_id} to delete.")
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
                deleted_count += 1
            except OSError as e:
                print(f"Failed to delete file {file_path}: {e}")
                failed_count += 1
            except Exception as e:
                print(f"Unexpected error deleting file {file_path}: {e}")
                failed_count += 1
        file_feedback = f"({deleted_count} deleted, {failed_count} failed)" if failed_count > 0 else f"({deleted_count} deleted)"
        delete_success = failed_count == 0
    else:
        file_feedback = "(no files found in storage)"
        delete_success = True

    if message:
        try:
            await message.delete()
            print(f"Deleted Discord message ID {message.id}")
            message_deleted = True
        except discord.errors.Forbidden: message_error = "lack permission to delete the message"; print(f"Error: Bot lacks permission to delete message {message.id}.")
        except discord.errors.NotFound: message_error = "message already gone"; print(f"Message {message.id} already deleted.")
        except Exception as e: message_error = "error during message deletion"; print(f"Unexpected error deleting message {message.id}: {e}"); traceback.print_exc()

    if interaction:
        feedback_message_content = ""
        if delete_success and message_deleted: feedback_message_content = f"Deleted job `{job_id}` files {file_feedback} and message."
        elif delete_success and message_error: feedback_message_content = f"Deleted job `{job_id}` files {file_feedback}, but {message_error}."
        elif not delete_success and message_deleted: feedback_message_content = f"Deleted message, but failed to delete job `{job_id}` files {file_feedback}."
        elif not delete_success and message_error: feedback_message_content = f"Failed to delete job `{job_id}` files {file_feedback}, and {message_error}."
        else: feedback_message_content = f"Job `{job_id}` file deletion: {file_feedback}."
        try:
            if interaction.response.is_done(): await interaction.followup.send(feedback_message_content, ephemeral=True)
            else: await interaction.response.send_message(feedback_message_content, ephemeral=True)
        except discord.NotFound:
            if message and message.channel: await message.channel.send(f"Delete status for job `{job_id}`: {feedback_message_content}", delete_after=20)
        except Exception as e_fb: print(f"Error sending delete followup/response: {e_fb}")
    return delete_success and (message_deleted or message_error == "message already gone")

async def remove_message(message_to_delete: discord.Message, command_message: discord.Message):
    if not message_to_delete: return
    try:
        await message_to_delete.delete()
        if command_message and command_message.channel:
             try: await command_message.channel.send("Removed bot message.", delete_after=10)
             except Exception as e_send_confirm: print(f"Error sending 'Removed bot message' confirmation: {e_send_confirm}")
    except discord.errors.Forbidden:
        if command_message and command_message.channel:
             try: await command_message.channel.send("I don't have permission to delete that message.", delete_after=10)
             except Exception as e_send_perm_err: print(f"Error sending 'no permission' message: {e_send_perm_err}")
    except discord.errors.NotFound: pass
    except Exception as e:
        print(f"Error removing message: {e}"); traceback.print_exc()
        if command_message and command_message.channel:
            try: await command_message.channel.send("An error occurred while removing the message.", delete_after=10)
            except Exception as e_send_gen_err: print(f"Error sending 'an error occurred' message: {e_send_gen_err}")
# --- END OF FILE file_management.py ---