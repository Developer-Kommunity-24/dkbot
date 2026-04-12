import discord
from discord import app_commands
from discord.ext import commands
import logging
import config
import email_sender

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="status", description="Get a summary of applicant statuses.")
    @commands.has_permissions(administrator=True)
    async def status_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        stats = await self.bot.sheets_client.async_get_stats()
        embed = discord.Embed(title="Applicant Status Summary", color=discord.Color.dark_gold())
        embed.add_field(name="Approved", value=stats['approved'], inline=True)
        embed.add_field(name="Rejected", value=stats['rejected'], inline=True)
        embed.add_field(name="Pending", value=stats['pending'], inline=True)
        embed.set_footer(text=f"Total Applicants: {stats['total']}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="invite", description="Send invites to accepted users")
    @commands.has_permissions(administrator=True)
    async def invite_command(self, interaction: discord.Interaction):
        await interaction.response.send_message("📨 Processing invites...")

        try:
            rows = await self.bot.sheets_client.async_get_all_records()
            count = 0
            total = 0

            for i, row in enumerate(rows, start=2):
                responded = str(row.get("responded", "")).strip().lower()
                accepted = str(row.get("accepted", "")).strip().lower()
                email = str(row.get("email", "")).strip()

                if responded == "no" and accepted == "yes" and email:
                    try:
                        total += 1
                        # Use the new async method
                        await email_sender.send_invite_email(email, row.get("firstName", "")+" "+row.get("lastName", ""))
                        await self.bot.sheets_client.async_mark_responded(email)
                        count += 1
                    except Exception as e:
                        print(f"❌ Failed to send to {email}: {e}")

            await interaction.followup.send(f"✅ Sent {count}/{total} invites successfully!")

        except Exception as e:
            await interaction.followup.send(f"❌ Failed to process Google Sheet: {e}")

    @app_commands.command(name="view", description="View applicants by status.")
    @app_commands.describe(status="The status of applicants to view.")
    @app_commands.choices(status=[
        app_commands.Choice(name="Approved", value="approved"),
        app_commands.Choice(name="Rejected", value="rejected"),
        app_commands.Choice(name="Pending", value="pending"),
    ])
    @commands.has_permissions(administrator=True)
    async def view_command(self, interaction: discord.Interaction, status: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)
        
        records = await self.bot.sheets_client.async_get_records_by_status(status.value)
        
        if not records:
            await interaction.followup.send(f"No applicants found with status: {status.name}", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Applicants: {status.name}",
            color=discord.Color.blue()
        )
        
        description = ""
        # TODO: Add pagination if needed
        for record in records[:25]: # Limit to 25 to avoid hitting Discord's embed limits
            name = f"{record.get(config.COL_FIRST_NAME, '')} {record.get(config.COL_LAST_NAME, '')}".strip()
            email = record.get(config.COL_EMAIL, 'N/A')
            description += f"**{name}** - {email}\n"
            
        embed.description = description
        
        if len(records) > 25:
            embed.set_footer(text=f"Showing 25 of {len(records)} records.")
            
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="search", description="Search for an applicant by name or email.")
    @app_commands.describe(query="The name or email to search for.")
    @commands.has_permissions(administrator=True)
    async def search_command(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer(ephemeral=True)
        
        records = await self.bot.sheets_client.async_search_records(query)
        
        if not records:
            await interaction.followup.send(f"No applicants found matching '{query}'.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Search Results for '{query}'",
            color=discord.Color.blue()
        )
        
        description = ""
        for record in records[:25]: # Limit to 25 to avoid hitting Discord's embed limits
            name = f"{record.get(config.COL_FIRST_NAME, '')} {record.get(config.COL_LAST_NAME, '')}".strip()
            email = record.get(config.COL_EMAIL, 'N/A')
            status = str(record.get(config.COL_ACCEPTED, 'N/A')).strip().lower()
            description += f"**{name}** - {email} - Status: `{status}`\n"
            
        embed.description = description
        
        if len(records) > 25:
            embed.set_footer(text=f"Showing 25 of {len(records)} records.")
            
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Admin(bot), guild=discord.Object(id=config.GUILD_ID))
