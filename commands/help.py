# Help command implementation
import discord
from discord.ext import commands
from discord import app_commands
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HelpCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="View all available drink check bot commands")
    async def help(self, interaction: discord.Interaction):
        """Display help information for all non-admin commands"""
        try:
            embed = discord.Embed(
                title="🍺 Drink Check Bot Commands",
                description="Here are all the available commands you can use!",
                color=discord.Color.blue()
            )

            # Profile Command
            embed.add_field(
                name="/profile [user]",
                value="View your drink check profile or another user's profile. Shows:\n"
                "• 🍺 Total drink check credits\n"
                "• 📝 Initial drink checks started\n"
                "• ⛓️ Chain participations\n"
                "• 📅 Today's and yesterday's drink checks\n"
                "• 🏆 Most active day stats\n"
                "• Longest chain streak",
                inline=False
            )

            # Leaderboard Command
            embed.add_field(
                name="/leaderboard",
                value="View the drink check leaderboard featuring:\n"
                "• Top 10 users by total drink checks\n"
                "• 🏅 Server record chain with initiator",
                inline=False
            )

            # Timer Command
            embed.add_field(
                name="/timer",
                value="Check the status of the current drink check chain:\n"
                "• Time remaining in the current chain\n"
                "• Who started the chain\n"
                "• Last person to participate\n"
                "• Chain starts expire after 30 minutes of inactivity",
                inline=False
            )

            # How to Start a Chain
            embed.add_field(
                name="Starting a Chain",
                value="To start or join a drink check chain:\n"
                "• Type 'drink check' in any tracked channel\n"
                "• Chains last for 30 minutes after the last drink check\n"
                "• Anyone can join an active chain by saying 'drink check'\n"
                "• Replying to your own active chain will not reset the timer",
                inline=False
            )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await interaction.response.send_message("Error displaying help information.", ephemeral=True)
            raise

async def setup(bot):
    await bot.add_cog(HelpCommands(bot)) 