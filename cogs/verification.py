import discord
from discord import app_commands
from discord.ext import commands
import logging
import config

class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="verify", description="Verify your email to claim your cluster role")
    @app_commands.describe(email="Your registered email address")
    async def verify_command(self, interaction: discord.Interaction, email: str):
        await interaction.response.send_message("🔍 Verifying your email...", ephemeral=True)
        
        # Async method usage
        record = await self.bot.sheets_client.async_get_record_by_email(email)
        
        if not record:
            await interaction.followup.send("❌ Email not found or not eligible.", ephemeral=True)
            return

        if str(record.get(config.COL_ROLE_CLAIMED, "")).strip().lower() == "yes":
            await interaction.followup.send("⚠️ You have already claimed your role.", ephemeral=True)
            return
        
        if str(record.get(config.COL_ACCEPTED, "")).strip().lower() != "yes":
            await interaction.followup.send("❌ Your application has not been approved yet.", ephemeral=True)
            return

        role = interaction.guild.get_role(config.VERIFY_ROLE_ID)
        if role:
            await interaction.user.add_roles(role)
            await self.bot.sheets_client.async_claim_role_by_email(email)
            logging.info(f"Role '{role.name}' assigned to {interaction.user.name} and sheet updated for {email}.")
            await interaction.followup.send("✅ Role successfully claimed!", ephemeral=True)
        else:
            await interaction.followup.send("❌ Internal error: Could not find the role to assign.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Verification(bot), guild=discord.Object(id=config.GUILD_ID))
