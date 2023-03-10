from __future__ import annotations

import sys
import asyncio

from nextcore.http.client import HTTPClient

from nextcore.http import BotAuthentication, UnauthorizedError
from nextcore.gateway import ShardManager

from typing import Dict, Any
from discord_typings import UpdatePresenceData, PartialActivityData, ApplicationData
from devgoldyutils import Colours

from .. import LoggerAdapter, goldy_bot_logger
from ..errors import GoldyBotError
from ..info import VERSION, COPYRIGHT

from .token import Token

# Fixes this https://github.com/nextsnake/nextcore/issues/189.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

cache:Dict[str, Any] = {
    "goldy_core_instance": None,
}

class Goldy():
    """The main Goldy Bot class that controls the whole framework and let's you start an instance of Goldy Bot. Also known as the core."""
    def __init__(self, token:Token = None, raise_on_extension_loader_error = None):
        self.token = token
        self.logger = LoggerAdapter(goldy_bot_logger, Colours.ORANGE.apply_to_string("Goldy"))
        self.async_loop = asyncio.get_event_loop()

        # Boot title and copyright stuff.
        print(
            f" {Colours.YELLOW.apply_to_string('Goldy')} {Colours.ORANGE.apply_to_string('Bot')} ({Colours.BLUE.apply_to_string(VERSION)}) - {Colours.PINK_GREY.apply_to_string(COPYRIGHT)}\n"
        )

        # Initializing stuff
        # -------------------
        if self.token is None:
            self.token = Token()
        
        self.nc_authentication = BotAuthentication(self.token.discord_token)
        self.intents = 1 << 9 | 1 << 15

        self.http_client = HTTPClient()

        self.shard_manager = ShardManager(
            authentication = self.nc_authentication,
            intents = self.intents,
            http_client = self.http_client,

            presence = UpdatePresenceData(
                activities = [PartialActivityData(name=f"Goldy Bot (v{VERSION})", type=ActivityTypes.PLAYING_GAME.value)],
                since = None,
                status = Status.ONLINE.value,
                afk = False
            )
        )

        self.application_data:ApplicationData = None

        # Add to cache.
        cache["goldy_core_instance"] = self

        # Adding shortcuts to sub classes to core class.
        # --------------------------------
        self.database = Database(self)
        """Goldy Bot's class to interface with a Mongo Database asynchronously."""
        self.presence = Presence(self)
        """Class that allows you to control the status, game activity and more of Goldy Bot"""
        self.config = GoldyConfig()
        """
        Class that allows you to retrieve configuration data from the ``goldy.json`` config file. 
        
        All properties return None when not found in the config.
        """
        self.command_loader = CommandLoader(self)
        """Class that handles command loading."""
        self.extension_loader = ExtensionLoader(self, raise_on_extension_loader_error)
        """Class that handles extension loading."""
        self.extension_reloader = ExtensionReloader(self)
        """Class that handles extension reloading."""
        self.live_console = LiveConsole(self)
        """The goldy bot live console."""
        self.guilds = Guilds(self)

    def start(self):
        """???????? Awakens Goldy Bot from her hibernation. ???? Shortcut to ``asyncio.run(goldy.__start_async())`` and also handles various exceptions carefully."""
        try:
            self.async_loop.run_until_complete(
                self.__start_async()
            )
        except KeyboardInterrupt:
            self.stop("Keyboard interrupt detected!")
        except RuntimeError as e:
            # I really do hope this doesn't torture me in the future. ????
            pass

        return None

    async def __start_async(self):
        await self.http_client.setup()

        # This should return once all shards have started to connect.
        # This does not mean they are connected.
        try:
            await self.shard_manager.connect()
            self.logger.debug("Nextcore shard manager connecting...")
        except UnauthorizedError as e:
            raise GoldyBotError(
                f"Nextcord shard manager failed to connect! We got '{e.message}' from nextcord. This might mean your discord token is incorrect!"
            )

        # Log when shards are ready.
        self.shard_manager.event_dispatcher.add_listener(
            lambda x: self.logger.info(f"Nextcore shards are {Colours.GREEN.apply_to_string('connected')} and {Colours.BLUE.apply_to_string('READY!')}"), 
            event_name="READY"
        )

        await self.pre_setup()
        await self.setup()

        self.live_console.start()

        # Raise a error and exit whenever a critical error occurs.
        error = await self.shard_manager.dispatcher.wait_for(lambda reason: True, "critical")

        self.logger.warn(Colours.YELLOW.apply_to_string("Goldy Bot is shutting down..."))
        self.logger.info(Colours.BLUE.apply_to_string(f"Reason: {error[0]}"))

        await self.__stop_async()

    async def pre_setup(self):
        """Method ran before actual setup. This is used to fetch some data from discord needed by goldy when running the actual setup."""
        self.application_data = await self.http_client.get_current_bot_application_information(self.nc_authentication)

    async def setup(self):
        """Method ran to set up goldy bot."""
        await self.guilds.setup()
        
        self.extension_loader.load()
        await self.command_loader.load()

    def stop(self, reason:str = "Unknown Reason"):
        """Shuts down goldy bot right away and safely incase anything sussy wussy is going on. ????"""
        self.live_console.stop()

        self.async_loop.create_task(self.shard_manager.dispatcher.dispatch("critical", reason)) # Raises critical error within nextcore and stops it.

    async def __stop_async(self):
        """This is an internal method and NOT to be used by you. Use the ``Goldy().stop()`` instead. This method is ran when nextcore raises a critical error."""
        await self.presence.change(Status.INVISIBLE) # Set bot to invisible before shutting off.
        
        self.logger.debug("Closing nextcore http client...")
        await self.http_client.close()

        self.logger.debug("Closing nextcore shard manager...")
        await self.shard_manager.close()

        self.logger.debug("Closing AsyncIOMotorClient...")
        self.database.client.close()
    
        self.logger.debug("Closing async_loop...")
        self.async_loop.stop()


# Get goldy instance method.
# ---------------------------
def get_goldy_instance() -> Goldy | None:
    """Returns instance of goldy core class."""
    return cache["goldy_core_instance"]

get_core = get_goldy_instance
"""Returns instance of goldy core class."""
get_goldy = get_goldy_instance
"""Returns instance of goldy core class."""


# Root imports.
# -------------
from .database import Database
from .presence import Presence, Status, ActivityTypes
from .goldy_config import GoldyConfig
from .extensions.extension_loader import ExtensionLoader
from .extensions.extension_reloader import ExtensionReloader
from .commands.command_loader import CommandLoader
from .live_console import LiveConsole
from .guilds import Guilds