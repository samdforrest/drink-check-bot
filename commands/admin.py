#admin commands
import discord
from discord.ext import commands

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command(name="admin")
    @commands.has_permissions(administrator=True)
    async def admin(self, ctx):
        # Admin commands
        await ctx.send("Admin panel - coming soon!")