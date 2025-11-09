import asyncio
import sys
import types


def _ensure_discord_stub() -> None:
    if "discord" in sys.modules:
        return

    discord_stub = types.ModuleType("discord")

    class Message:
        def __init__(self, content: str | None = None):
            self.content = content
            self.id = 0
            self.channel = types.SimpleNamespace(id=0)

    class File:
        def __init__(self, fp=None, filename: str | None = None):
            self.fp = fp
            self.filename = filename

    class Attachment:
        def __init__(self, *, url: str = "", filename: str = ""):
            self.url = url
            self.filename = filename

    class Reaction:
        def __init__(self, emoji=None, message=None):
            self.emoji = emoji
            self.message = message

    class _BaseDMRecipient:
        def __init__(self, name: str = "user", user_id: int = 0):
            self.name = name
            self.id = user_id

        async def send(self, content: str, **kwargs):  # pragma: no cover - stub only
            return Message(content=content)

    class User(_BaseDMRecipient):
        pass

    Member = User

    class _InteractionResponse:
        def __init__(self):
            self._done = False

        def is_done(self) -> bool:
            return self._done

        async def send_message(self, *args, **kwargs):  # pragma: no cover - stub only
            self._done = True

        async def defer(self, *args, **kwargs):  # pragma: no cover - stub only
            self._done = True

        async def edit_message(self, *args, **kwargs):  # pragma: no cover - stub only
            self._done = True

    class _Followup:
        async def send(self, *args, **kwargs):  # pragma: no cover - stub only
            return Message()

    class Interaction:
        def __init__(self):
            self.response = _InteractionResponse()
            self.followup = _Followup()
            self.channel = types.SimpleNamespace(send=self._channel_send)
            self.command = types.SimpleNamespace(name="command")

        async def _channel_send(self, *args, **kwargs):  # pragma: no cover - stub only
            return Message()

        async def original_response(self):  # pragma: no cover - stub only
            return Message()

    class ButtonStyle:
        primary = "primary"
        secondary = "secondary"
        success = "success"
        danger = "danger"
        grey = "grey"
        green = "green"
        red = "red"

    class TextStyle:
        short = "short"
        paragraph = "paragraph"

    class _DummySelectOption:
        def __init__(self, label=None, value=None, default=None, *args, **kwargs):
            self.label = label
            self.value = value
            self.default = default

    class Messageable:
        async def send(self, *args, **kwargs):  # pragma: no cover - stub only
            return Message()

    discord_stub.Message = Message
    discord_stub.File = File
    discord_stub.Attachment = Attachment
    discord_stub.Reaction = Reaction
    discord_stub.User = User
    discord_stub.Member = Member
    discord_stub.Interaction = Interaction
    discord_stub.ButtonStyle = ButtonStyle
    discord_stub.TextStyle = TextStyle
    discord_stub.SelectOption = _DummySelectOption

    ui_module = types.ModuleType("discord.ui")

    class Modal:
        title: str | None = None

        def __init_subclass__(cls, **kwargs):
            cls.title = kwargs.get("title")
            return super().__init_subclass__()

        def __init__(self, *, timeout: float | None = None):
            self.timeout = timeout
            self.children: list = []

        def add_item(self, item):
            self.children.append(item)

    class TextInput:
        def __init__(self, *, label=None, style=None, default=None, required=True, placeholder=None, max_length=None):
            self.label = label
            self.style = style
            self.default = default
            self.required = required
            self.placeholder = placeholder
            self.max_length = max_length
            self.value = default

    class View:
        def __init__(self, *, timeout: float | None = None):
            self.timeout = timeout
            self.children: list = []

        def add_item(self, item):
            self.children.append(item)

    class Button:
        def __init__(self, *, label=None, style=None, custom_id=None, row=None, disabled=False, emoji=None, url=None):
            self.label = label
            self.style = style
            self.custom_id = custom_id
            self.row = row
            self.disabled = disabled
            self.emoji = emoji
            self.url = url

        async def callback(self, interaction):  # pragma: no cover - stub only
            return None

    def button(*decorator_args, **decorator_kwargs):  # pragma: no cover - stub only
        def _decorator(func):
            return func

        return _decorator

    ui_module.Modal = Modal
    ui_module.TextInput = TextInput
    ui_module.View = View
    ui_module.Button = Button
    ui_module.button = button

    errors_module = types.ModuleType("discord.errors")

    class DiscordException(Exception):
        pass

    class Forbidden(DiscordException):
        pass

    class HTTPException(DiscordException):
        def __init__(self, status: int = 0, text: str = ""):
            super().__init__(text)
            self.status = status
            self.text = text

    class InteractionResponded(DiscordException):
        pass

    class NotFound(DiscordException):
        def __init__(self, code: int = 0, text: str = ""):
            super().__init__(text)
            self.code = code
            self.text = text

    errors_module.DiscordException = DiscordException
    errors_module.Forbidden = Forbidden
    errors_module.HTTPException = HTTPException
    errors_module.InteractionResponded = InteractionResponded
    errors_module.NotFound = NotFound

    abc_module = types.ModuleType("discord.abc")
    abc_module.Messageable = Messageable

    app_commands_module = types.ModuleType("discord.app_commands")

    class CommandTree:
        def __init__(self, bot=None):
            self.bot = bot

        def command(self, *args, **kwargs):  # pragma: no cover - stub only
            def _decorator(func):
                return func

            return _decorator

        async def sync(self, *args, **kwargs):  # pragma: no cover - stub only
            return []

    app_commands_module.CommandTree = CommandTree

    discord_stub.ui = ui_module
    discord_stub.abc = abc_module
    discord_stub.errors = errors_module
    discord_stub.app_commands = app_commands_module
    discord_stub.HTTPException = HTTPException

    sys.modules["discord"] = discord_stub
    sys.modules["discord.ui"] = ui_module
    sys.modules["discord.errors"] = errors_module
    sys.modules["discord.app_commands"] = app_commands_module
    sys.modules["discord.abc"] = abc_module


def _ensure_numpy_stub() -> None:
    if "numpy" in sys.modules:
        return

    numpy_stub = types.ModuleType("numpy")

    def _arange(start, stop=None, step=1.0):
        if stop is None:
            stop = float(start)
            start = 0.0
        values = []
        current = float(start)
        step = float(step)
        comparator = (lambda a, b: a < b) if step > 0 else (lambda a, b: a > b)
        while comparator(current, float(stop)) or abs(current - float(stop)) < 1e-9:
            values.append(current)
            current += step
        return values

    numpy_stub.arange = _arange
    sys.modules["numpy"] = numpy_stub


def _ensure_aiohttp_stub() -> None:
    if "aiohttp" in sys.modules:
        return

    aiohttp_stub = types.ModuleType("aiohttp")

    class _DummyTCPConnector:
        def __init__(self, *args, **kwargs):
            pass

    class _DummyClientSession:
        def __init__(self, *args, **kwargs):
            self.closed = True

        async def ws_connect(self, *args, **kwargs):  # pragma: no cover - stub only
            raise RuntimeError("aiohttp stub does not provide websocket connections")

        async def close(self):  # pragma: no cover - stub only
            self.closed = True

    aiohttp_stub.TCPConnector = _DummyTCPConnector
    aiohttp_stub.ClientSession = _DummyClientSession
    aiohttp_stub.ClientConnectorError = Exception
    sys.modules["aiohttp"] = aiohttp_stub


def _ensure_pillow_stub() -> None:
    if "PIL" in sys.modules:
        return

    pil_module = types.ModuleType("PIL")
    image_module = types.ModuleType("PIL.Image")

    class _DummyImage:
        def __init__(self, size=(0, 0)):
            self.size = size

        def resize(self, size, resample=None):  # pragma: no cover - stub only
            return _DummyImage(size)

        def save(self, fp, format=None):  # pragma: no cover - stub only
            return None

    def open(path):  # pragma: no cover - stub only
        return _DummyImage()

    image_module.Image = _DummyImage
    image_module.open = open
    pil_module.Image = image_module

    sys.modules["PIL"] = pil_module
    sys.modules["PIL.Image"] = image_module


_ensure_discord_stub()
_ensure_numpy_stub()
_ensure_aiohttp_stub()
_ensure_pillow_stub()
