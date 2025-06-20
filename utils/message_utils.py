# --- START OF FILE utils/message_utils.py ---
import discord
import textwrap
import traceback

async def send_long_message(user: discord.User | discord.Member, content: str, max_length=2000):
    """
    Sends a long message to a user, splitting it into chunks if necessary.
    Handles DM permissions.
    Returns a list of sent message objects, or None if DMs are blocked/failed.
    """
    if not isinstance(user, (discord.User, discord.Member)):
        print(f"Error (send_long_message): Invalid user type: {type(user)}")
        return None
    if not content or not isinstance(content, str):
        print("Error (send_long_message): Invalid or empty content.")
        return None

    sent_messages = []
    try:
        if len(content) <= max_length:
            msg = await user.send(content)
            if msg: sent_messages.append(msg)
        else:
            # Use textwrap to split, preserving words and newlines as much as possible
            chunks = textwrap.wrap(content, max_length, replace_whitespace=False, drop_whitespace=False, break_long_words=False, break_on_hyphens=False)
            for chunk_num, chunk_content in enumerate(chunks):
                if not chunk_content.strip(): # Skip empty chunks
                    continue
                # print(f"DEBUG: Sending chunk {chunk_num+1}/{len(chunks)} of length {len(chunk_content)} to {user.name}")
                msg = await user.send(chunk_content)
                if msg: sent_messages.append(msg)
        return sent_messages if sent_messages else None # Return list or None if nothing was sent
    except discord.errors.Forbidden:
        print(f"Error (send_long_message): Cannot send DM to {user.name} ({user.id}). DMs may be disabled or bot blocked.")
        return None
    except discord.errors.HTTPException as http_err:
        print(f"Error (send_long_message): HTTPException sending DM chunk to {user.name} ({user.id}): {http_err.status} - {http_err.text}")
        return None # Indicate failure, but don't stop the bot for this.
    except Exception as e:
        print(f"Error (send_long_message): Unexpected error sending DM to {user.name} ({user.id}): {e}")
        traceback.print_exc()
        return None

async def safe_interaction_response(interaction: discord.Interaction, content: str, view: discord.ui.View = None, ephemeral: bool = False, files: list[discord.File] = None):
    """
    Safely sends a response to an interaction, handling whether it's already been responded to
    and common webhook errors by falling back to channel.send.
    Returns the message object sent, or None on failure.
    """
    sent_message = None
    try:
        kwargs = {"content": content, "ephemeral": ephemeral}
        if view is not None: kwargs["view"] = view
        if files is not None: kwargs["files"] = files

        if interaction.response.is_done():
            # print(f"DEBUG (safe_interaction_response): Interaction for '{interaction.command.name if interaction.command else 'button'}' is done, using followup.")
            sent_message = await interaction.followup.send(**kwargs, wait=True if files else False)
        else:
            # print(f"DEBUG (safe_interaction_response): Interaction for '{interaction.command.name if interaction.command else 'button'}' not done, using response.send_message.")
            await interaction.response.send_message(**kwargs)
            if not ephemeral: # Only get original response if not ephemeral (followup.send for ephemeral is fine)
                sent_message = await interaction.original_response()
            # For ephemeral, response.send_message doesn't return the message,
            # and followup is generally preferred for ephemeral messages if the initial response is just a defer.
            # If the send_message IS the final ephemeral response, getting the message object is tricky.

    except discord.errors.InteractionResponded: # Should be caught by is_done(), but as a safeguard
        # print(f"DEBUG (safe_interaction_response): InteractionResponded caught, trying followup again for '{interaction.command.name if interaction.command else 'button'}'.")
        try: # Try followup again
            kwargs = {"content": content, "ephemeral": ephemeral} # Reset kwargs
            if view is not None: kwargs["view"] = view
            if files is not None: kwargs["files"] = files
            sent_message = await interaction.followup.send(**kwargs, wait=True if files else False)
        except Exception as e_followup_reraise:
             print(f"Error (safe_interaction_response): Followup failed after InteractionResponded: {e_followup_reraise}")
             # Fall through to channel send as last resort if possible

    except discord.errors.NotFound as e_notfound: # Often "Unknown Webhook" or "Unknown Interaction"
        print(f"Error (safe_interaction_response): NotFound error ({e_notfound.code} - {e_notfound.text}). Falling back to channel.send for '{interaction.command.name if interaction.command else 'button'}'.")
        if interaction.channel:
            try:
                sent_message = await interaction.channel.send(content=content, view=view, files=files)
            except Exception as e_channel_send_fb:
                print(f"Error (safe_interaction_response): Fallback channel.send also failed: {e_channel_send_fb}")
        else:
            print("Error (safe_interaction_response): interaction.channel is None, cannot fallback.")
    except discord.HTTPException as http_err:
        print(f"Error (safe_interaction_response): HTTPException ({http_err.status} - {http_err.text}). Falling back to channel.send for '{interaction.command.name if interaction.command else 'button'}'.")
        if interaction.channel:
            try:
                sent_message = await interaction.channel.send(content=content, view=view, files=files)
            except Exception as e_channel_send_fb_http:
                print(f"Error (safe_interaction_response): Fallback channel.send after HTTPException also failed: {e_channel_send_fb_http}")
        else:
            print("Error (safe_interaction_response): interaction.channel is None, cannot fallback.")

    except Exception as e_general:
        print(f"Error (safe_interaction_response): General error for '{interaction.command.name if interaction.command else 'button'}': {e_general}")
        traceback.print_exc()
        if interaction.channel: # Last resort fallback
            try:
                sent_message = await interaction.channel.send(content=f"{content}\n(Note: Had to use a fallback message method due to an error)", view=view, files=files)
            except Exception as e_critical_fallback:
                print(f"Error (safe_interaction_response): CRITICAL - All messaging methods failed: {e_critical_fallback}")
    return sent_message
# --- END OF FILE utils/message_utils.py ---