import discord
from discord.ext import commands
from discord import app_commands
from database.models import User, Credit, DrinkCheck, ActiveChain
from database.connection import DatabaseSession
import logging

logger = logging.getLogger(__name__)

class AdminCommands(commands.GroupCog, group_name="admin"):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    @app_commands.checks.has_permissions(administrator=True)
    async def admin_check(self, interaction: discord.Interaction) -> bool:
        """Check if user has admin role or is administrator."""
        if interaction.user.guild_permissions.administrator:
            return True
        admin_role = discord.utils.get(interaction.guild.roles, name="Admin")
        if admin_role in interaction.user.roles:
            return True
        await interaction.response.send_message("You don't have permission to use admin commands.", ephemeral=True)
        return False

    @app_commands.command(name='help', description="Shows help with available admin commands")
    async def admin_help(self, interaction: discord.Interaction):
        """Shows help with available admin commands."""
        if not await self.admin_check(interaction):
            return

        embed = discord.Embed(
            title="DrinkCheck Admin Commands",
            description="Available admin commands:",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="/admin setcredits <user> <initial> <chain>",
            value="Set a user's initial and chain credits",
            inline=False
        )
        embed.add_field(
            name="/admin addcredits <user> <initial> <chain>",
            value="Add initial and chain credits to a user",
            inline=False
        )
        embed.add_field(
            name="/admin resetall",
            value="Reset all users' credits and clear active chains",
            inline=False
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='setcredits', description="Set a user's credits to specific values")
    @app_commands.describe(
        user="The user to set credits for",
        initial="Number of initial credits",
        chain="Number of chain credits"
    )
    async def set_credits(self, interaction: discord.Interaction, user: discord.Member, initial: int, chain: int):
        """Set a user's credits to specific values."""
        if not await self.admin_check(interaction):
            return

        try:
            with DatabaseSession() as db:
                db_user = db.query(User).filter_by(user_id=user.id).first()
                if not db_user:
                    db_user = User(user_id=user.id, username=str(user))
                    db.add(db_user)
                
                # Delete existing credits
                db.query(Credit).filter_by(user_id=user.id).delete()
                
                # Add new credits
                for _ in range(initial):
                    credit = Credit(user_id=user.id, credit_type='initial')
                    db.add(credit)
                
                for _ in range(chain):
                    credit = Credit(user_id=user.id, credit_type='chain')
                    db.add(credit)
                
                db_user.total_credits = initial + chain
                db.commit()
                
                await interaction.response.send_message(f"Set {user.mention}'s credits to {initial} initial and {chain} chain credits.")
                logger.info(f"Admin {interaction.user} set credits for {user} to {initial} initial and {chain} chain")
        
        except Exception as e:
            logger.error(f"Error in set_credits: {e}")
            await interaction.response.send_message("An error occurred while setting credits.", ephemeral=True)
            raise

    @app_commands.command(name='addcredits', description="Add credits to a user's existing total")
    @app_commands.describe(
        user="The user to add credits to",
        initial="Number of initial credits to add",
        chain="Number of chain credits to add"
    )
    async def add_credits(self, interaction: discord.Interaction, user: discord.Member, initial: int, chain: int):
        """Add credits to a user's existing total."""
        if not await self.admin_check(interaction):
            return

        try:
            with DatabaseSession() as db:
                db_user = db.query(User).filter_by(user_id=user.id).first()
                if not db_user:
                    db_user = User(user_id=user.id, username=str(user))
                    db.add(db_user)
                
                # Add new credits
                for _ in range(initial):
                    credit = Credit(user_id=user.id, credit_type='initial')
                    db.add(credit)
                
                for _ in range(chain):
                    credit = Credit(user_id=user.id, credit_type='chain')
                    db.add(credit)
                
                db_user.total_credits += initial + chain
                db.commit()
                
                await interaction.response.send_message(f"Added {initial} initial and {chain} chain credits to {user.mention}.")
                logger.info(f"Admin {interaction.user} added credits for {user}: +{initial} initial, +{chain} chain")
        
        except Exception as e:
            logger.error(f"Error in add_credits: {e}")
            await interaction.response.send_message("An error occurred while adding credits.", ephemeral=True)
            raise

    @app_commands.command(name='resetall', description="Reset all users' credits and clear active chains")
    async def reset_all(self, interaction: discord.Interaction):
        """Reset all users' credits and clear active chains."""
        if not await self.admin_check(interaction):
            return

        try:
            # Ask for confirmation
            await interaction.response.send_message("⚠️ This will reset ALL users' credits and clear ALL active chains. Click the button to confirm.", 
                view=ConfirmView(interaction.user, self._do_reset))
        
        except Exception as e:
            logger.error(f"Error in reset_all: {e}")
            await interaction.response.send_message("An error occurred while resetting credits.", ephemeral=True)
            raise

    async def _do_reset(self, interaction: discord.Interaction):
        """Actually perform the reset after confirmation"""
        try:
            with DatabaseSession() as db:
                # Delete all credits
                db.query(Credit).delete()
                
                # Reset all user totals
                db.query(User).update({User.total_credits: 0})
                
                # Deactivate all chains
                db.query(ActiveChain).update({ActiveChain.is_active: False})
                
                db.commit()
                
                await interaction.response.send_message("✅ All credits have been reset and chains cleared.")
                logger.info(f"Admin {interaction.user} performed full reset of all credits and chains")
        except Exception as e:
            logger.error(f"Error in _do_reset: {e}")
            await interaction.response.send_message("An error occurred while resetting credits.", ephemeral=True)
            raise

class ConfirmView(discord.ui.View):
    def __init__(self, author, callback):
        super().__init__()
        self.author = author
        self.callback = callback

    @discord.ui.button(label='Confirm Reset', style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("Only the command user can confirm this action.", ephemeral=True)
            return
        
        await self.callback(interaction)
        self.stop()

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
    return True 