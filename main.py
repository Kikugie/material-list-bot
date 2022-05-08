import datetime
import logging
import os
import sys

import nextcord
import yaml
from nextcord.ext import commands
from abc import ABC

logging.basicConfig(level=logging.INFO)
INTENTS = nextcord.Intents.default()
CONFIG = None


def main():
    global CONFIG
    with open('config.yml', 'r') as f:
        CONFIG = yaml.load(f, yaml.Loader)
    Bot(CONFIG).run(CONFIG['token'])


class Bot(commands.Bot, ABC):
    def __init__(self, config):
        self.CONFIG = config
        self.LOGGER = logging.getLogger('main')

        super().__init__(
            command_prefix="!",
            intents=INTENTS,
            owner_id=self.CONFIG['owner_id'],
            reconnect=True,
            case_insensitive=False
        )

        if not os.path.exists(self.CONFIG['temp_directory']):
            os.mkdir(self.CONFIG['temp_directory'])

        self.uptime = None

        self.remove_command('help')
        self.loop.create_task(self.ready())

    async def ready(self):
        await self.wait_until_ready()

        # await self.change_presence(activity=discord.Activity(type=type, name=activity))

        if not self.uptime:
            self.uptime = datetime.datetime.utcnow()

        try:
            self.load_extension(f"cogs.schematics")
            self.LOGGER.info(f'Loaded schematics cog')
            await self.rollout_application_commands()
        except Exception as e:
            self.LOGGER.error(f"Could not load cog")
            self.LOGGER.exception(e)

        self.LOGGER.info("\n-------------------MatlBot-------------------"
                         f"\nBot is online and connected to {self.user}"
                         f"\nCreated by enjarai & KikuGie"
                         f"\nConnected to {(len(self.guilds))} Guilds."
                         f"\nDetected Operating System: {sys.platform.title()}"
                         "\n----------------------ඞ---------------------")


if __name__ == '__main__':
    main()
