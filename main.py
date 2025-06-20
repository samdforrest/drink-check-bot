#entry point for the application

import discord
from discord import app_commands
from discord.ext import commands
from bot.trackers import DrinkCheckTracker
from bot.stats import StatsManager
from bot.database import Database
from commands.stats import StatsCommands
from commands.admin import AdminCommands
from config.settings import DISCORD_TOKEN, TRACKED_CHANNELS

class DrinkCheckBot(commands.Bot):
    def __init__(self):
        # Set up intents (what Discord allows us to see)
        intents = discord.Intents.default()
        intents.message_content = True  # Can read message content
        intents.members = True          # Can see server members
        
        super().__init__(
            command_prefix=None,         # Only use slash commands
            intents=intents
        )
        
        # Initialize our tracking systems
        self.database = Database()
        self.drink_check_tracker = DrinkCheckTracker(database=self.database)
        self.stats_manager = StatsManager()

    async def on_ready(self):
        # Bot just connected to Discord
        print(f"Bot is ready! Logged in as {self.user}")
        print(f"Bot is in {len(self.guilds)} guilds:")
        for guild in self.guilds:
            print(f"  - {guild.name} (id: {guild.id})")
        await self.database.initialize()
        
        # Sync commands after bot is ready
        print("Syncing slash commands...")
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Error syncing commands: {e}")
        
    async def on_message(self, message):
        # Every message in Discord goes through here
        if message.author.bot:  # Ignore other bots
            return
            
        # Check if this is a drink check (with attachment requirement)
        if self.drink_check_tracker.is_drink_check(message.content, message):
            await self.drink_check_tracker.track_new_drink_check(message)
            
        # Check if this is a response to a drink check
        response_to = await self.drink_check_tracker.is_response_to_drink_check(message)
        if response_to:
            await self.drink_check_tracker.track_response(message, response_to)
            
        # Process commands
        await self.process_commands(message)

    async def setup_hook(self):
        # Load all our command modules
        print("Loading command cogs...")
        await self.add_cog(StatsCommands(self))
        await self.add_cog(AdminCommands(self))
        print("Command cogs loaded successfully")

# Create and run the bot
async def main():
    bot = DrinkCheckBot()
    try:
        await bot.start(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("Bot shutting down...")
    finally:
        await bot.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())