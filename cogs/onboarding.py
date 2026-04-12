import discord
from discord import app_commands
from discord.ext import commands
import logging
import config

class RoleSelectionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def toggle_role(self, interaction: discord.Interaction, role_name: str):
        # We'll try to find the role by name. If it doesn't exist, we create it.
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not role:
            try:
                role = await interaction.guild.create_role(name=role_name, reason="Auto-created for onboarding")
            except discord.Forbidden:
                await interaction.response.send_message("I don't have permission to manage roles! Please ask an admin.", ephemeral=True)
                return

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(f"Removed the **{role_name}** role.", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"Added the **{role_name}** role!", ephemeral=True)

    @discord.ui.button(label="Python", style=discord.ButtonStyle.primary, custom_id="role_python", emoji="🐍")
    async def btn_python(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_role(interaction, "Python")

    @discord.ui.button(label="JavaScript", style=discord.ButtonStyle.primary, custom_id="role_js", emoji="⚡")
    async def btn_js(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_role(interaction, "JavaScript")

    @discord.ui.button(label="Cloud / DevOps", style=discord.ButtonStyle.primary, custom_id="role_cloud", emoji="☁️")
    async def btn_cloud(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_role(interaction, "Cloud / DevOps")

    @discord.ui.button(label="AI / ML", style=discord.ButtonStyle.primary, custom_id="role_ai", emoji="🤖")
    async def btn_ai(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_role(interaction, "AI / ML")

class Onboarding(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_roles", description="Spawn the role selection message.")
    @commands.has_permissions(administrator=True)
    async def setup_roles_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🏷️ Select Your Tech Stack",
            description="Click the buttons below to assign yourself roles. This helps others know what you work with, and allows us to ping you for relevant workshops or events!",
            color=discord.Color.blurple()
        )
        view = RoleSelectionView()
        await interaction.response.send_message("Spawning onboarding view...", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Onboarding(bot))
