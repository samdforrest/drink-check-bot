import discord
from discord.ext import commands
from discord import app_commands
from database.models import User, Credit
from database.connection import DatabaseSession
import logging

logger = logging.getLogger(__name__)

class AdminCommands(commands.GroupCog, group_name="admin"):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    async def owner_check(self, interaction: discord.Interaction) -> bool:
        """Check if user has the Owner role."""
        owner_role = discord.utils.get(interaction.guild.roles, name="Owner")
        if not owner_role:
            await interaction.response.send_message("❌ The 'Owner' role doesn't exist in this server.", ephemeral=True)
            return False
        
        if owner_role not in interaction.user.roles:
            await interaction.response.send_message("❌ You need the 'Owner' role to use admin commands.", ephemeral=True)
            return False
        
        return True

    @app_commands.command(name='setcredit', description="Set a user's total credits")
    @app_commands.describe(
        user="The user to set credits for",
        amount="Number of credits to set"
    )
    async def set_credit(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        """Set a user's total credits."""
        # Check for Owner role first
        if not await self.owner_check(interaction):
            return

        try:
            with DatabaseSession() as db:
                # Get or create user
                db_user = db.query(User).filter_by(user_id=user.id).first()
                if not db_user:
                    db_user = User(user_id=user.id, username=str(user))
                    db.add(db_user)
                
                # Update total credits
                db_user.total_credits = amount
                
                # Delete existing credits
                db.query(Credit).filter_by(user_id=user.id).delete()
                
                # Add new credits as 'initial' type
                for _ in range(amount):
                    credit = Credit(
                        user_id=user.id,
                        credit_type='initial'
                    )
                    db.add(credit)
                
                db.commit()
                
                await interaction.response.send_message(
                    f"✅ Set {user.mention}'s credits to {amount}",
                    ephemeral=True
                )
                logger.info(f"Admin {interaction.user} set credits for {user} to {amount}")
        
        except Exception as e:
            logger.error(f"Error in set_credit: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while setting credits.",
                ephemeral=True
            )
            raise

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
    return True 