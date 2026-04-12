import discord
from discord import app_commands
from discord.ext import commands
import logging
import config

class FindTeamView(discord.ui.View):
    def __init__(self, author: discord.Member, hackathon_name: str):
        super().__init__(timeout=None)
        self.author = author
        self.hackathon_name = hackathon_name

    @discord.ui.button(label="Request to Join", style=discord.ButtonStyle.success, custom_id="join_team_btn")
    async def join_team(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.author.id:
            await interaction.response.send_message("You can't request to join your own team!", ephemeral=True)
            return

        # Send a DM to the author
        try:
            embed = discord.Embed(
                title=f"New Team Request: {self.hackathon_name}",
                description=f"{interaction.user.mention} wants to join your team!",
                color=discord.Color.green()
            )
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None)
            embed.set_footer(text="Send them a message to connect!")
            
            await self.author.send(embed=embed)
            await interaction.response.send_message(f"✅ I have notified {self.author.mention} that you want to join!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(f"❌ {self.author.mention} has their DMs closed. You'll have to ping them directly.", ephemeral=True)
        except Exception as e:
            logging.error(f"Error sending DM in FindTeam: {e}")
            await interaction.response.send_message(f"❌ An error occurred while notifying the author.", ephemeral=True)

class Teams(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="find_team", description="Find a team for a hackathon or project.")
    @app_commands.describe(
        hackathon_name="The name of the hackathon or project",
        skills="Your skills (e.g., React, Python, UI/UX)",
        looking_for="Who you are looking for (e.g., Backend Developer)"
    )
    async def find_team_command(self, interaction: discord.Interaction, hackathon_name: str, skills: str, looking_for: str):
        await interaction.response.defer()

        embed = discord.Embed(
            title=f"🤝 Looking for a Team: {hackathon_name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="💡 My Skills", value=skills, inline=False)
        embed.add_field(name="🔍 Looking For", value=looking_for, inline=False)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None)
        embed.set_footer(text="Click 'Request to Join' to instantly notify the poster!")

        view = FindTeamView(author=interaction.user, hackathon_name=hackathon_name)
        await interaction.followup.send(embed=embed, view=view)
        logging.info(f"Team finding request posted by {interaction.user.name} for {hackathon_name}")

async def setup(bot):
    await bot.add_cog(Teams(bot))
