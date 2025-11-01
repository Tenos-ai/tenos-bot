import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
import traceback
from aiohttp import web
from ipaddress import ip_address


from bot_config_loader import (
    BOT_TOKEN, ADMIN_USERNAME, print_startup_info,
    BOT_INTERNAL_API_HOST, BOT_INTERNAL_API_PORT, BOT_INTERNAL_API_TOKEN
)


from file_management import extract_job_id
from queue_manager import queue_manager
from settings_manager import load_settings


from bot_events import on_bot_ready, on_bot_message, on_bot_reaction_add
from bot_slash_commands import setup_slash_commands
from bot_commands import setup_bot_commands, register_bot_instance as register_bot_for_commands
from bot_core_logic import check_output_folders, update_job_progress
from websocket_client import WebsocketClient


intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
intents.guilds = True
intents.members = True
intents.reactions = True

class TenosBot(commands.Bot):
    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix=command_prefix, intents=intents)
        self.commands_module = None
        self.dm_history = {}
        self.api_runner = None
        self.update_job_progress = self.create_update_job_progress()

    def create_update_job_progress(self):
        async def updater(prompt_id, current_step, max_steps, image_data):
            await update_job_progress(self, prompt_id, current_step, max_steps, image_data)
        return updater
        
    async def setup_hook(self):
        self.loop.create_task(setup_internal_api(self))

    async def close(self):
        if self.api_runner:
            try:
                await self.api_runner.cleanup()
                print("Internal API server shut down.")
            except Exception as e_cleanup:
                print(f"Warning: Error while cleaning up internal API server: {e_cleanup}")
            finally:
                self.api_runner = None
        await super().close()

bot = TenosBot(command_prefix='/', intents=intents)


register_bot_for_commands(bot)


async def handle_get_guilds(request):
    bot_instance = request.app['bot']
    guilds_data = [{"id": str(g.id), "name": g.name} for g in sorted(bot_instance.guilds, key=lambda g: g.name.lower())]
    return web.json_response(guilds_data)

async def handle_get_members(request):
    guild_id = request.match_info.get('guild_id')
    if not guild_id or not guild_id.isdigit():
        return web.json_response({"error": "Invalid Guild ID"}, status=400)
    
    bot_instance = request.app['bot']
    guild = bot_instance.get_guild(int(guild_id))
    if not guild:
        return web.json_response({"error": "Guild not found"}, status=404)
        
    members_data = []
    sorted_members = sorted(guild.members, key=lambda m: (m.bot, m.display_name.lower()))
    for m in sorted_members:
        members_data.append({
            "id": str(m.id),
            "name": m.name,
            "display_name": m.display_name,
            "discriminator": m.discriminator,
            "is_bot": m.bot
        })
    return web.json_response(members_data)

async def handle_get_dms(request):
    bot_instance = request.app['bot']
    dms_data = []
    sorted_dms = sorted(bot_instance.dm_history.values(), key=lambda m: m.created_at, reverse=True)
    for msg in sorted_dms:
        dms_data.append({
            "author_id": str(msg.author.id),
            "author_name": msg.author.name,
            "timestamp": msg.created_at.isoformat(),
            "content": msg.content
        })
    return web.json_response(dms_data)

async def handle_leave_guild(request):
    guild_id = request.match_info.get('guild_id')
    if not guild_id or not guild_id.isdigit():
        return web.json_response({"error": "Invalid Guild ID"}, status=400)
    
    bot_instance = request.app['bot']
    guild = bot_instance.get_guild(int(guild_id))
    if not guild:
        return web.json_response({"error": "Guild not found"}, status=404)
    
    try:
        await guild.leave()
        return web.json_response({"status": "success", "message": f"Left guild {guild.name}"})
    except Exception as e:
        return web.json_response({"error": f"Failed to leave guild: {e}"}, status=500)

async def handle_get_user(request):
    user_id = request.match_info.get('user_id')
    if not user_id or not user_id.isdigit():
        return web.json_response({"error": "Invalid User ID"}, status=400)
    
    bot_instance = request.app['bot']
    try:
        user = await bot_instance.fetch_user(int(user_id))
        if user:
            return web.json_response({"id": str(user.id), "name": user.name})
        else:
            return web.json_response({"error": "User not found"}, status=404)
    except discord.NotFound:
        return web.json_response({"error": "User not found"}, status=404)
    except Exception as e:
        return web.json_response({"error": f"An error occurred: {e}"}, status=500)


def _is_loopback_host(host: str) -> bool:
    if not host:
        return False
    lowered = host.lower()
    if lowered == "localhost":
        return True
    try:
        return ip_address(lowered).is_loopback
    except ValueError:
        return False


@web.middleware
async def internal_api_auth_middleware(request, handler):
    if BOT_INTERNAL_API_TOKEN:
        provided_token = request.headers.get("X-Internal-Token")
        if provided_token != BOT_INTERNAL_API_TOKEN:
            return web.json_response({"error": "Unauthorized"}, status=401)
    else:
        peer_info = request.transport.get_extra_info("peername") if request.transport else None
        if peer_info:
            client_host = peer_info[0]
            if not _is_loopback_host(client_host):
                return web.json_response({"error": "Unauthorized"}, status=401)
    return await handler(request)


async def setup_internal_api(bot_instance):
    if not BOT_INTERNAL_API_TOKEN and not _is_loopback_host(BOT_INTERNAL_API_HOST):
        print(
            "CRITICAL ERROR: Refusing to start internal API on a non-loopback host without an AUTH_TOKEN."
        )
        return

    app_api = web.Application(middlewares=[internal_api_auth_middleware])
    app_api['bot'] = bot_instance
    app_api.add_routes([
        web.get('/api/guilds', handle_get_guilds),
        web.get('/api/guilds/{guild_id}/members', handle_get_members),
        web.get('/api/dms', handle_get_dms),
        web.post('/api/guilds/{guild_id}/leave', handle_leave_guild),
        web.get('/api/user/{user_id}', handle_get_user), # <-- ADDED NEW ENDPOINT
    ])
    runner = web.AppRunner(app_api)
    await runner.setup()
    site = web.TCPSite(runner, BOT_INTERNAL_API_HOST, BOT_INTERNAL_API_PORT)
    try:
        await site.start()
        print(f"Internal API server started on http://{BOT_INTERNAL_API_HOST}:{BOT_INTERNAL_API_PORT}")
        bot_instance.api_runner = runner
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to start internal API server: {e}")
        traceback.print_exc()
        try:
            await runner.cleanup()
        except Exception as cleanup_err:
            print(f"Warning: Failed to clean up internal API runner after startup error: {cleanup_err}")


@bot.event
async def on_ready():
    await on_bot_ready(bot)
    for channel in bot.private_channels:
        if isinstance(channel, discord.DMChannel) and channel.recipient:
            try:
                async for message in channel.history(limit=1):
                     if message.author.id != bot.user.id:
                         bot.dm_history[message.author.id] = message
            except Exception:
                continue

@bot.event
async def on_message(message: discord.Message):
    if isinstance(message.channel, discord.DMChannel) and message.author.id != bot.user.id:
        bot.dm_history[message.author.id] = message
    await on_bot_message(bot, message)

@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User | discord.Member):
    await on_bot_reaction_add(bot, reaction, user)


setup_slash_commands(bot.tree, bot)


bot.commands_module = setup_bot_commands(bot)


if __name__ == "__main__":
    if not BOT_TOKEN:
        print("\n" + "=" * 40 + "\n CRITICAL ERROR: BOT_API KEY not found in config.json! \n" + "=" * 40 + "\n")
    else:
        try:
            print("Attempting to connect to Discord...")
            bot.run(BOT_TOKEN)
        except discord.PrivilegedIntentsRequired:
            print("\n" + "=" * 40 + "\n Error: Privileged Intents Required! \n" + "=" * 40 + "\n")
        except discord.LoginFailure:
            print("\n" + "=" * 40 + "\n Error: Invalid Bot Token. \n" + "=" * 40 + "\n")
        except Exception as e:
            print(f"\nUnexpected error running bot: {type(e).__name__} - {e}")
            traceback.print_exc()
