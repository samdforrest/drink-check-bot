#statistics commands
import discord
from discord.ext import commands
from discord import app_commands
from database.models import User, DrinkCheck, Credit
from database.connection import DatabaseSession
from sqlalchemy import func
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StatsCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="test", description="Test command to verify slash commands work")
    async def test(self, interaction: discord.Interaction):
        """Simple test command"""
        await interaction.response.send_message("Test command works! Slash commands are functioning.", ephemeral=True)
        
    @app_commands.command(name="profile", description="View your drink check profile")
    async def profile(self, interaction: discord.Interaction, user: discord.Member = None):
        """View detailed drink check profile for a user"""
        try:
            target_user = user or interaction.user
            logger.info(f"Getting profile for user: {target_user.name}")
            
            with DatabaseSession() as db:
                # Get user data
                db_user = db.query(User).filter_by(user_id=target_user.id).first()
                if not db_user:
                    logger.info(f"No profile found for user: {target_user.name}")
                    await interaction.response.send_message(f"{target_user.name} hasn't participated in any drink checks yet!", ephemeral=True)
                    return

                logger.info(f"Found user profile with {db_user.total_credits} total credits")

                # Get detailed stats
                initial_dcs = db.query(func.count(Credit.credit_id))\
                    .filter_by(user_id=target_user.id, credit_type='initial')\
                    .scalar() or 0
                    
                chain_dcs = db.query(func.count(Credit.credit_id))\
                    .filter_by(user_id=target_user.id, credit_type='chain')\
                    .scalar() or 0

                logger.info(f"Stats for {target_user.name}: initial={initial_dcs}, chain={chain_dcs}")

                # Create embed
                embed = discord.Embed(
                    title=f"🍺 Drink Check Profile: {target_user.name}",
                    color=discord.Color.gold()
                )
                
                embed.add_field(
                    name="Total Credits",
                    value=f"🍺 {db_user.total_credits}",
                    inline=False
                )
                
                embed.add_field(
                    name="Initial Drink Checks",
                    value=f"📝 {initial_dcs}",
                    inline=True
                )
                
                embed.add_field(
                    name="Chain Participations",
                    value=f"⛓️ {chain_dcs}",
                    inline=True
                )
                
                # Add user avatar
                embed.set_thumbnail(url=target_user.display_avatar.url)
                
                await interaction.response.send_message(embed=embed)
                
        except Exception as e:
            logger.error(f"Error in profile command: {e}")
            await interaction.response.send_message("Error getting profile information.", ephemeral=True)
    
    @app_commands.command(name="leaderboard", description="View the drink check leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        """Display the drink check leaderboard"""
        try:
            logger.info("Fetching leaderboard data")
            with DatabaseSession() as db:
                # Get top 10 users
                top_users = db.query(User)\
                    .order_by(User.total_credits.desc())\
                    .limit(10)\
                    .all()
                
                logger.info(f"Found {len(top_users)} users for leaderboard")
                
                if not top_users:
                    logger.info("No users found in database")
                    await interaction.response.send_message("No drink checks recorded yet!", ephemeral=True)
                    return
                
                # Create embed
                embed = discord.Embed(
                    title="🏆 Drink Check Leaderboard",
                    color=discord.Color.gold()
                )
                
                # Add leaderboard entries
                leaderboard_text = ""
                for i, user in enumerate(top_users, 1):
                    member = interaction.guild.get_member(user.user_id)
                    name = member.name if member else user.username
                    leaderboard_text += f"`{i}.` {name:<20} 🍺 {user.total_credits}\n"
                    logger.info(f"Leaderboard entry {i}: {name} with {user.total_credits} credits")
                
                embed.description = leaderboard_text
                
                await interaction.response.send_message(embed=embed)
                
        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}", exc_info=True)
            await interaction.response.send_message("Error getting leaderboard.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(StatsCommands(bot))
    return True