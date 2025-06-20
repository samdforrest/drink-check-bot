#statistics commands
import discord
from discord.ext import commands
from discord import app_commands

class StatsCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="test", description="Test command to verify slash commands work")
    async def test(self, interaction: discord.Interaction):
        """Simple test command"""
        await interaction.response.send_message("Test command works! Slash commands are functioning.", ephemeral=True)
        
    @app_commands.command(name="stats", description="Get your drink check stats")
    async def stats(self, interaction: discord.Interaction, user: discord.Member = None):
        """Get drink check statistics for a user"""
        try:
            user = user or interaction.user
            print(f"Stats command called by {interaction.user.name} for user {user.name}")
            
            # Get stats from database
            stats = await self.bot.database.get_user_stats(str(user.id))
            print(f"Retrieved stats: {stats}")
            
            # Format the stats nicely
            embed = discord.Embed(
                title=f"Drink Check Stats for {stats['username']}",
                color=0x00ff00
            )
            embed.add_field(name="Drink Checks", value=stats['drink_checks'], inline=True)
            embed.add_field(name="Responses", value=stats['responses'], inline=True)
            embed.add_field(name="Rank", value=f"#{stats['user_rank']}" if stats['user_rank'] > 0 else "Unranked", inline=True)
            embed.add_field(name="Total Server Drink Checks", value=stats['total_drink_checks'], inline=True)
            embed.add_field(name="Total Server Responses", value=stats['total_responses'], inline=True)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Error in stats command: {e}")
            await interaction.response.send_message(f"Error getting stats: {str(e)}", ephemeral=True)
        
    @commands.command(name="stats")
    async def stats_prefix(self, ctx, user=None):
        # Get user stats (prefix command version)
        await ctx.send("Stats command - coming soon!")
        
    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx):
        # Get leaderboard
        await ctx.send("Leaderboard - coming soon!")