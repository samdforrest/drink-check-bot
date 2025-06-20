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
        self.drink_check_tracker = DrinkCheckTracker()
        self.stats_manager = StatsManager()
        self.database = Database()

    async def on_ready(self):
        # Bot just connected to Discord
        print(f"Bot is ready! Logged in as {self.user}")
        print(f"Bot is in {len(self.guilds)} guilds:")
        for guild in self.guilds:
            print(f"  - {guild.name} (id: {guild.id})")
        await self.database.initialize()
        
    async def on_message(self, message):
        # Every message in Discord goes through here
        if message.author.bot:  # Ignore other bots
            return
            
        # Check if this is a drink check
        if self.drink_check_tracker.is_drink_check(message.content):
            await self.drink_check_tracker.track_new_drink_check(message)
            
        # Check if this is a response to a drink check
        response_to = self.drink_check_tracker.is_response_to_drink_check(message)
        if response_to:
            await self.drink_check_tracker.track_response(message, response_to)
            
        # Process commands
        await self.process_commands(message)

    async def setup_hook(self):
        # Load all our command modules
        await self.add_cog(StatsCommands(self))
        await self.add_cog(AdminCommands(self))

        # Sync the slash commands
        await self.tree.sync()
        
    # Commands like /stats, /leaderboard get routed here
    @app_commands.command(name="stats", description="Get your drink check stats")
    async def stats(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        stats = await self.stats_manager.get_user_stats(user.id)
        await interaction.response.send_message(f"Stats for {user.name}: {stats}")

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