#main bot class and setup
import discord
from discord.ext import commands
import os
import logging
from database.connection import init_db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DrinkCheckBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # Need this for reading message content
        intents.members = True  # Need this for member info in leaderboard
        
        super().__init__(
            command_prefix='!',  # Prefix for traditional commands
            intents=intents,
            help_command=None  # We'll implement our own help command
        )
    
    async def setup_hook(self):
        """This is called when the bot starts up"""
        logger.info("Starting bot setup...")
        
        # Initialize database
        init_db()
        logger.info("Database initialized")
        
        # Load all cogs
        await self.load_extension('bot.events.message_events')
        await self.load_extension('commands.stats')
        await self.load_extension('commands.help')
        logger.info("Extensions loaded")
    
    async def on_ready(self):
        """Called when the bot is ready to start working"""
        logger.info(f'Logged in as {self.user.name} ({self.user.id})')
        
        # Sync slash commands
        logger.info("Syncing slash commands...")
        await self.tree.sync()
        logger.info("Slash commands synced")

def run_bot():
    """Run the bot with the token from environment"""
    bot = DrinkCheckBot()
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        raise ValueError("No Discord token found in environment variables!")
    bot.run(token)

if __name__ == "__main__":
    run_bot()