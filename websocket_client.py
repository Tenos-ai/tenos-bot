import asyncio
import aiohttp
import json
import weakref
import traceback
import uuid

from bot_config_loader import COMFYUI_HOST, COMFYUI_PORT
from queue_manager import queue_manager

class WebsocketClient:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(WebsocketClient, cls).__new__(cls)
        return cls._instance

    def __init__(self, bot_ref=None):
        if hasattr(self, '_initialized') and self._initialized:
            if bot_ref and (self.bot() is None or self.bot() != bot_ref):
                self.bot = weakref.ref(bot_ref)
                print("WebsocketClient: Bot reference updated.")
            return
        
        if bot_ref is None and not hasattr(self, 'bot'): 
            raise ValueError("WebsocketClient must be initialized with a bot reference on its first instantiation.")
        
        if bot_ref:
            self.bot = weakref.ref(bot_ref)

        if not hasattr(self, "_client_id_ready_event"):
            self._client_id_ready_event = asyncio.Event()
        else:
            self._client_id_ready_event.clear()

        self.client_id_confirmed = False

        self.ws_base_url = f"ws://{COMFYUI_HOST}:{COMFYUI_PORT}/ws"
        if not hasattr(self, "client_id") or self.client_id is None:
            self.client_id = uuid.uuid4().hex
        self.ws_url = f"{self.ws_base_url}?clientId={self.client_id}"
        self.session = None
        self.ws = None
        self.is_connected = False
        self.is_connecting = False
        self.active_prompts = {}
        self._initialized = True
        self.connection_task = None
        self.listener_task = None

    async def connect(self):
        if self.is_connected or self.is_connecting:
            return
        
        bot = self.bot()
        if not bot or bot.is_closed():
            print("WebSocket Error: Bot reference is lost or bot is closing. Cannot connect.")
            self.is_connecting = False 
            return

        self.is_connecting = True
        print("WebSocket: Attempting to connect...")
        self.client_id_confirmed = False
        if hasattr(self, "_client_id_ready_event"):
            self._client_id_ready_event.clear()
        try:
            if self.session is None or self.session.closed:
                connector = aiohttp.TCPConnector(limit_per_host=1)
                self.session = aiohttp.ClientSession(connector=connector)

            # Ensure the websocket URL always includes the latest client ID.
            self.ws_url = f"{self.ws_base_url}?clientId={self.client_id}"
            self.ws = await self.session.ws_connect(self.ws_url, timeout=10)
            self.is_connected = True
            self.is_connecting = False
            print(f"WebSocket: Successfully connected to {self.ws_url}")
            
            if self.listener_task and not self.listener_task.done():
                self.listener_task.cancel() 
            self.listener_task = bot.loop.create_task(self.listen())

        except aiohttp.ClientConnectorError as e:
            print(f"WebSocket Connection Error: Failed to connect to {self.ws_url}. Is ComfyUI running? Details: {e}")
            self.is_connected = False
            self.is_connecting = False
            await self.close_session() 
        except asyncio.TimeoutError:
            print(f"WebSocket Connection Error: Timeout when trying to connect to {self.ws_url}.")
            self.is_connected = False
            self.is_connecting = False
            await self.close_session()
        except Exception as e:
            print(f"WebSocket Error: An unexpected error occurred during connection: {e}")
            traceback.print_exc()
            self.is_connected = False
            self.is_connecting = False
            await self.close_session()


    async def listen(self):
        print("WebSocket: Listener started.")
        if not self.ws or self.ws.closed:
            print("WebSocket Listener Error: WebSocket is not connected or already closed.")
            self.is_connected = False
            return

        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self.handle_message(data)
                    except json.JSONDecodeError:
                        print(f"WebSocket Warning: Received non-JSON message: {msg.data}")
                    except Exception as e_handle:
                         print(f"WebSocket Error: Error handling message: {e_handle}")
                         traceback.print_exc()
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    print("WebSocket: Connection closed by server.")
                    break
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    print(f"WebSocket: Connection error. Exception: {self.ws.exception()}")
                    break
        except asyncio.CancelledError:
            print("WebSocket: Listener task cancelled.")
        except Exception as e:
            print(f"WebSocket Listener Error: An unexpected error occurred: {e}")
            traceback.print_exc()
        finally:
            print("WebSocket: Listener loop terminated.")
            self.is_connected = False

    async def handle_message(self, data):
        bot = self.bot()
        if not bot or bot.is_closed():
            return

        msg_type = data.get('type')
        msg_data_content = data.get('data', {})
        
        

        if msg_type == 'status':
            sid_from_msg = msg_data_content.get('sid') if 'sid' in msg_data_content else data.get('sid')
            if sid_from_msg:
                if not self.client_id:
                    self.client_id = sid_from_msg
                    print(f"WebSocket: Received client ID: {self.client_id}")
                    self.ws_url = f"{self.ws_base_url}?clientId={self.client_id}"
                elif self.client_id != sid_from_msg:
                    print(f"WebSocket Warning: Client ID changed from {self.client_id} to {sid_from_msg}")
                    self.client_id = sid_from_msg
                    self.ws_url = f"{self.ws_base_url}?clientId={self.client_id}"
                self.client_id_confirmed = True
                if hasattr(self, "_client_id_ready_event"):
                    self._client_id_ready_event.set()

        elif msg_type == 'execution_start': 
            prompt_id = msg_data_content.get('prompt_id')
            if prompt_id and prompt_id in self.active_prompts:
                print(f"WebSocket: Job {prompt_id} started execution.")
                for p_id_loop in list(self.active_prompts.keys()): 
                    if p_id_loop == prompt_id:
                        if p_id_loop in self.active_prompts: self.active_prompts[p_id_loop]['status'] = 'executing'
                    elif p_id_loop in self.active_prompts and self.active_prompts[p_id_loop]['status'] == 'executing': 
                        self.active_prompts[p_id_loop]['status'] = 'queued_behind_new_start'

        elif msg_type == 'execution_cached':
            prompt_id = msg_data_content.get('prompt_id')
            if prompt_id and prompt_id in self.active_prompts:
                print(f"WebSocket: Job {prompt_id} is using cached data.")
                if self.active_prompts[prompt_id]['status'] != 'executing':
                    for p_id_loop in list(self.active_prompts.keys()):
                        if p_id_loop == prompt_id:
                            if p_id_loop in self.active_prompts: self.active_prompts[p_id_loop]['status'] = 'executing'
                        elif p_id_loop in self.active_prompts and self.active_prompts[p_id_loop]['status'] == 'executing':
                            self.active_prompts[p_id_loop]['status'] = 'queued_usurped_by_cache_message'
            
        elif msg_type == 'executing': 
            prompt_id = msg_data_content.get('prompt_id')
            if prompt_id and prompt_id in self.active_prompts:
                if self.active_prompts[prompt_id]['status'] != 'executing':
                    for p_id_loop in list(self.active_prompts.keys()):
                         if p_id_loop == prompt_id:
                              if p_id_loop in self.active_prompts: self.active_prompts[p_id_loop]['status'] = 'executing'
                         elif p_id_loop in self.active_prompts and self.active_prompts[p_id_loop]['status'] == 'executing':
                              self.active_prompts[p_id_loop]['status'] = 'queued_usurped' 
            
        elif msg_type == 'executed': 
            prompt_id = msg_data_content.get('prompt_id')
            if prompt_id:
                print(f"WebSocket: Job {prompt_id} finished execution.")
                self.unregister_prompt(prompt_id)

        elif msg_type == 'progress':
            progress_update_data = msg_data_content 
            prompt_id_for_progress = msg_data_content.get('prompt_id') 
            if not prompt_id_for_progress:
                prompt_id_for_progress = next((pid for pid, pdata in self.active_prompts.items() if pdata.get('status') == 'executing'), None)
            
            if prompt_id_for_progress and prompt_id_for_progress in self.active_prompts:
                current_step = progress_update_data.get('value', 0)
                max_steps = progress_update_data.get('max', 1) 
                if max_steps > 0 and hasattr(bot, 'update_job_progress'):
                    try:
                        await bot.update_job_progress(prompt_id_for_progress, current_step, max_steps, None)
                    except Exception as e_upd:
                        print(f"Error calling bot.update_job_progress for {prompt_id_for_progress} from WS progress: {e_upd}")

        elif msg_type == 'preview':
            preview_img_data = msg_data_content 
            prompt_id_for_preview = msg_data_content.get('prompt_id')
            if not prompt_id_for_preview:
                prompt_id_for_preview = next((pid for pid, pdata in self.active_prompts.items() if pdata.get('status') == 'executing'), None)

            if prompt_id_for_preview and prompt_id_for_preview in self.active_prompts:
                if hasattr(bot, 'update_job_progress'):
                    try:
                        await bot.update_job_progress(prompt_id_for_preview, None, None, preview_img_data)
                    except Exception as e_upd_preview:
                        print(f"Error calling bot.update_job_progress for {prompt_id_for_preview} from WS preview: {e_upd_preview}")

        elif msg_type in ['execution_interrupted', 'execution_error']:
             prompt_id = msg_data_content.get('prompt_id')
             if prompt_id:
                error_details = msg_data_content.get('exception_message', 'No details provided.')
                print(f"WebSocket: Job {prompt_id} failed with status '{msg_type}'. Details: {error_details}")
                self.unregister_prompt(prompt_id)
    
    async def register_prompt(self, prompt_id, message_id, channel_id):
        if not self.is_connected and not self.is_connecting:
            print("WebSocket: Not connected when trying to register prompt. Attempting to connect first.")
            await self.ensure_connected() 
            if not self.is_connected:
                print("WebSocket Warning: Still not connected after ensure_connected. Prompt registered locally but WS communication might fail.")

        print(f"WebSocket: Registering prompt {prompt_id} for message {message_id} in channel {channel_id}")
        self.active_prompts[prompt_id] = {
            "message_id": message_id,
            "channel_id": channel_id,
            "status": "queued", 
            "last_preview_timestamp": 0
        }

    def unregister_prompt(self, prompt_id):
        if prompt_id in self.active_prompts:
            del self.active_prompts[prompt_id]
            print(f"WebSocket: Unregistered prompt {prompt_id}")

    async def close_session(self):
        if self.session and not self.session.closed:
            await self.session.close()
            print("WebSocket: aiohttp session closed.")
        self.session = None

    async def disconnect(self, cancel_tasks=True):
        print("WebSocket: Disconnecting...")
        if cancel_tasks:
            if self.listener_task and not self.listener_task.done():
                self.listener_task.cancel()
                try: await self.listener_task
                except asyncio.CancelledError: print("WebSocket: Listener task successfully cancelled.")
                except Exception as e_cancel_listen: print(f"WebSocket: Error during listener task cancellation: {e_cancel_listen}")
            self.listener_task = None

            if self.connection_task and not self.connection_task.done():
                self.connection_task.cancel()
                try: await self.connection_task
                except asyncio.CancelledError: print("WebSocket: Connection task successfully cancelled.")
                except Exception as e_cancel_conn: print(f"WebSocket: Error during connection task cancellation: {e_cancel_conn}")
            self.connection_task = None

        if self.ws and not self.ws.closed:
            try:
                await self.ws.close()
                print("WebSocket: ws connection gracefully closed.")
            except Exception as e_ws_close:
                print(f"WebSocket: Error closing ws connection: {e_ws_close}")
        
        self.ws = None
        self.is_connected = False
        self.is_connecting = False
        print("WebSocket: Disconnected state set.")
        self.client_id_confirmed = False
        if hasattr(self, "_client_id_ready_event"):
            self._client_id_ready_event.clear()


    async def ensure_connected(self):
        if self.is_connected: return
        if self.is_connecting:
            print("WebSocket: ensure_connected called while already connecting. Waiting for existing attempt.")
            if self.connection_task:
                try: await asyncio.wait_for(self.connection_task, timeout=15)
                except asyncio.TimeoutError: print("WebSocket: Timeout waiting for ongoing connection task in ensure_connected.")
                except Exception as e: print(f"WebSocket: Error waiting for ongoing connection task: {e}")
            return

        bot = self.bot()
        if not bot or bot.is_closed():
            print("WebSocket: Cannot ensure connection, bot reference lost or bot closed.")
            return
        
        print("WebSocket: Not connected. Initiating connection task via ensure_connected.")
        if self.connection_task and not self.connection_task.done():
            self.connection_task.cancel()
            try: await self.connection_task
            except: pass

        self.connection_task = bot.loop.create_task(self.connect())
        try:
            await asyncio.wait_for(self.connection_task, timeout=15) 
        except asyncio.TimeoutError:
            print("WebSocket: Timeout waiting for connection task to complete during ensure_connected.")
        except Exception as e:
            print(f"WebSocket: Error during ensure_connected's connection task: {e}")
        finally:
            self.connection_task = None

    async def reconnect(self):
        print("WebSocket: Reconnect sequence initiated.")
        await self.disconnect(cancel_tasks=True)
        print("WebSocket: Delaying 5s before attempting reconnect...")
        await asyncio.sleep(5)
        await self.ensure_connected()

    async def wait_for_client_id(self, timeout: float = 5.0) -> bool:
        if self.client_id and getattr(self, "client_id_confirmed", False):
            return True

        event = getattr(self, "_client_id_ready_event", None)
        if event is None:
            event = asyncio.Event()
            self._client_id_ready_event = event

        try:
            await asyncio.wait_for(event.wait(), timeout)
        except asyncio.TimeoutError:
            return bool(self.client_id and getattr(self, "client_id_confirmed", False))

        return bool(self.client_id and getattr(self, "client_id_confirmed", False))
