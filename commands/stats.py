#statistics commands
from discord.ext import commands

class StatsCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command(name="stats")
    async def stats(self, ctx, user=None):
        # Get user stats
        await ctx.send("Stats command - coming soon!")
        
    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx):
        # Get leaderboard
        await ctx.send("Leaderboard - coming soon!")