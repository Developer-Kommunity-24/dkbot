import discord
from discord.ext import commands
import logging
import asyncio
import os

import config
from db_client import DatabaseClient
import web_server

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Bot Setup ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

class DKBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="^", intents=intents)
        self.sheets_client = None
        self.web_server_started = False

    async def setup_hook(self):
        # Initialize Database Client
        try:
            self.sheets_client = DatabaseClient()
            await self.sheets_client.async_init()
            logging.info("✅ Database Client initialized.")
        except Exception as e:
            logging.critical(f"FATAL: Could not initialize DatabaseClient. Error: {e}")
            exit(1)

        # Load Cogs
        await self.load_extension("cogs.verification")
        await self.load_extension("cogs.admin")
        await self.load_extension("cogs.applications")
        await self.load_extension("cogs.events")
        await self.load_extension("cogs.ticketing")
        await self.load_extension("cogs.gamification")
        await self.load_extension("cogs.showcase")
        await self.load_extension("cogs.teams")
        await self.load_extension("cogs.quizzes")
        await self.load_extension("cogs.onboarding")
        logging.info("✅ Cogs loaded.")

        # Sync Slash Commands
        try:
            synced = await self.tree.sync(guild=discord.Object(id=config.GUILD_ID))
            logging.info(f"✅ Synced {len(synced)} slash commands.")
        except Exception as e:
            logging.error(f"❌ Failed to sync slash commands: {e}")

    async def on_ready(self):
        logging.info(f"✅ Logged in as {self.user}")
        
        if not self.web_server_started:
            # Start the web server
            await web_server.start_web_server(self, self.sheets_client)
            self.web_server_started = True

if __name__ == "__main__":
    if not config.TOKEN:
        logging.critical("FATAL: Discord TOKEN not found in environment.")
        exit(1)
    
    bot = DKBot()
    bot.run(config.TOKEN)
  
    bot = DKBot()
    bot.run(config.TOKEN)
