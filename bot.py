"""Simple Python script using Discord.py and Motor"""

import logging

from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient

from settings import Auth

class Bot(commands.AutoShardedBot):
    """Main Bot class"""

    DESC = "An example bot to interact with Motor"
    EXTENSIONS = ["cogs.util", "cogs.gacha"]

    def __init__(self):
        super().__init__(command_prefix='%', description=self.DESC)

        logging.basicConfig(level=logging.INFO)

        self.client = AsyncIOMotorClient()
        self.db = self.client['coins_db'] # pylint: disable=invalid-name

        for extension in self.EXTENSIONS:
            try:
                self.load_extension(extension)
                print(f"Loaded {extension}")
            except commands.errors.ExtensionNotFound as ex:
                exc = f'{type(ex).__name__}: {ex}'
                print(f'Failed to load extension {extension}\n{exc}')

    async def on_ready(self):
        """Executed when the bot is ready."""
        print("AguiBot is on the sky!")
        print(f"I am running on {self.user.name}")
        print(f"With the ID: {str(self.user.id)}")

    async def on_message(self, message):
        """Executed when the bot detects a messagel in any channel of any server"""
        if message.author.bot:  # Avoids bot triggering itself
            return

        await self.process_commands(message)  # Without this, no @commands.command will be invoked.

if __name__ == "__main__":
    agui = Bot()
    agui.run(Auth.TOKEN)
