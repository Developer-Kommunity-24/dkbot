import discord
from discord import app_commands
from discord.ext import commands
import logging
import config

class Showcase(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="showcase", description="Show off your project to the community!")
    @app_commands.describe(
        project_name="The name of your project",
        github_link="Link to the repository or live demo",
        description="A short description of what it does"
    )
    async def showcase_command(self, interaction: discord.Interaction, project_name: str, github_link: str, description: str):
        await interaction.response.defer()

        embed = discord.Embed(
            title=f"🚀 Project Showcase: {project_name}",
            description=description,
            color=discord.Color.teal()
        )
        embed.add_field(name="🔗 Link", value=github_link, inline=False)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None)
        embed.set_footer(text="React with 👍 to upvote or 👎 to downvote this project!")

        try:
            # We use interaction.followup.send which posts the message
            msg = await interaction.followup.send(embed=embed)
            
            # To add reactions, we need to grab the original response
            message = await interaction.original_response()
            await message.add_reaction("👍")
            await message.add_reaction("👎")
            
            # Create a discussion thread linked to the message
            await message.create_thread(name=f"Discussion: {project_name[:20]}")
            logging.info(f"Project showcase posted by {interaction.user.name}")
            
        except Exception as e:
            logging.error(f"Failed to post showcase: {e}")
            await interaction.followup.send("❌ Failed to post showcase.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Showcase(bot))
