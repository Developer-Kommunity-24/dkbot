import discord
from discord.ext import commands
import logging
import config
import email_sender

# --- Interactive UI (Buttons) ---
class ApprovalView(discord.ui.View):
    def __init__(self, applicant_email: str, applicant_name: str):
        super().__init__(timeout=None)  # Persistent view
        self.applicant_email = applicant_email
        self.applicant_name = applicant_name

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, custom_id="approve_button")
    async def approve_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Send email (Async)
        email_sent = await email_sender.send_invite_email(self.applicant_email, self.applicant_name)
        
        if email_sent:
            # Update Google Sheet (Async)
            # Access sheets_client via the bot instance (interaction.client)
            await interaction.client.sheets_client.async_update_status_by_email(self.applicant_email, "yes")
            feedback_message = f"✅ **Approved and sent invite to {self.applicant_name} ({self.applicant_email}).**"
            log_message = f"Admin '{interaction.user.name}' approved {self.applicant_name}."
            new_embed_color = discord.Color.green()
        else:
            feedback_message = f"❌ **Failed to send email to {self.applicant_name} ({self.applicant_email}).** Check logs for details."
            log_message = f"Admin '{interaction.user.name}' attempted to approve {self.applicant_name}, but email failed."
            new_embed_color = discord.Color.orange()

        logging.info(log_message)
        await interaction.followup.send(feedback_message, ephemeral=True)

        # Edit original message to show it's been handled
        original_embed = interaction.message.embeds[0]
        new_embed = original_embed.copy()
        new_embed.color = new_embed_color
        new_embed.set_footer(text=f"Action taken by {interaction.user.name}")
        
        # Disable buttons
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(embed=new_embed, view=self)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger, custom_id="reject_button")
    async def reject_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Update Google Sheet (Async)
        await interaction.client.sheets_client.async_update_status_by_email(self.applicant_email, "no")
        
        log_message = f"Admin '{interaction.user.name}' rejected {self.applicant_name}."
        logging.info(log_message)
        
        await interaction.followup.send(f"🗑️ **Rejected {self.applicant_name} ({self.applicant_email}).**", ephemeral=True)

        # Edit original message
        original_embed = interaction.message.embeds[0]
        new_embed = original_embed.copy()
        new_embed.color = discord.Color.red()
        new_embed.set_footer(text=f"Rejected by {interaction.user.name}")

        # Create a new RejectedView
        rejected_view = RejectedView(applicant_email=self.applicant_email, applicant_name=self.applicant_name, original_embed=original_embed)

        await interaction.message.edit(embed=new_embed, view=rejected_view)

class RejectedView(discord.ui.View):
    def __init__(self, applicant_email: str, applicant_name: str, original_embed: discord.Embed):
        super().__init__(timeout=None)
        self.applicant_email = applicant_email
        self.applicant_name = applicant_name
        self.original_embed = original_embed

    @discord.ui.button(label="Changed my mind", style=discord.ButtonStyle.secondary, custom_id="undo_reject_button")
    async def undo_reject_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Revert Google Sheet status (Async)
        await interaction.client.sheets_client.async_update_status_by_email(self.applicant_email, "pending")

        log_message = f"Admin '{interaction.user.name}' reverted rejection for {self.applicant_name}."
        logging.info(log_message)

        await interaction.followup.send(f"↩️ **Reverted rejection for {self.applicant_name}.** You can now approve or reject them again.", ephemeral=True)

        # Create a new ApprovalView
        approval_view = ApprovalView(applicant_email=self.applicant_email, applicant_name=self.applicant_name)

        # Edit the message to show the original embed and the new view
        await interaction.message.edit(embed=self.original_embed, view=approval_view)

class Applications(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def post_approval_card(self, data: dict):
        """Formats and sends the interactive approval message to the admin channel."""
        channel = self.bot.get_channel(config.ADMIN_CHANNEL_ID)
        if not channel:
            logging.error(f"Could not find admin channel with ID {config.ADMIN_CHANNEL_ID}")
            return

        # Extract data with defaults
        first_name = data.get(config.COL_FIRST_NAME, "N/A")
        last_name = data.get(config.COL_LAST_NAME, "")
        email = data.get(config.COL_EMAIL, "N/A")
        phone = data.get(config.COL_PHONE, "N/A")
        college = data.get(config.COL_COLLEGE, "N/A")
        year = data.get(config.COL_YEAR, "N/A")
        interests = data.get(config.COL_INTERESTS, "N/A")
        motivation = data.get(config.COL_MOTIVATION, "N/A")
        full_name = f"{first_name} {last_name}".strip()

        embed = discord.Embed(
            title="New Individual Entry Added",
            description="──────────────────────────────",
            color=discord.Color.blue()
        )
        embed.add_field(name="👤 Name", value=full_name, inline=False)
        embed.add_field(name="📧 Email", value=email, inline=False)
        embed.add_field(name="📱 Phone", value=phone, inline=False)
        embed.add_field(name="🏫 College", value=college, inline=False)
        embed.add_field(name="📅 Year", value=year, inline=False)
        embed.add_field(name="✨ Interests", value=interests, inline=False)
        embed.add_field(name="💡 Motivation", value=motivation, inline=False)

        view = ApprovalView(applicant_email=email, applicant_name=full_name)
        await channel.send(embed=embed, view=view)

    async def post_college_applicant_card(self, data: dict):
        """Formats and sends the college applicant info to the admin channel."""
        channel = self.bot.get_channel(config.ADMIN_CHANNEL_ID)
        if not channel:
            logging.error(f"Could not find admin channel with ID {config.ADMIN_CHANNEL_ID}")
            return

        # Extract data with defaults
        college_name = data.get(config.COL_COLLEGE_NAME, "N/A")
        community_name = data.get(config.COL_COMMUNITY_NAME, "N/A")
        rep_name = data.get(config.COL_REP_NAME, "N/A")
        rep_position = data.get(config.COL_REP_POSITION, "N/A")
        rep_email = data.get(config.COL_REP_EMAIL, "N/A")
        rep_phone = data.get(config.COL_REP_PHONE, "N/A")
        faculty_name = data.get(config.COL_FACULTY_NAME, "N/A")
        faculty_email = data.get(config.COL_FACULTY_EMAIL, "N/A")
        community_size = data.get(config.COL_COMMUNITY_SIZE, "N/A")
        community_activities = data.get(config.COL_COMMUNITY_ACTIVITIES, "N/A")
        expectations = data.get(config.COL_EXPECTATIONS, "N/A")

        embed = discord.Embed(
            title="New Community Entry Added",
            description="──────────────────────────────",
            color=discord.Color.purple()
        )
        embed.add_field(name="College", value=college_name, inline=False)
        embed.add_field(name="Community", value=community_name, inline=False)
        embed.add_field(name="Representative", value=f"{rep_name} ({rep_position})", inline=False)
        embed.add_field(name="Rep Email", value=rep_email, inline=False)
        embed.add_field(name="Rep Phone", value=rep_phone, inline=False)
        embed.add_field(name="‍Faculty", value=faculty_name, inline=False)
        embed.add_field(name="Faculty Email", value=faculty_email, inline=False)
        embed.add_field(name="Community Size", value=community_size, inline=False)
        embed.add_field(name="Activities", value=community_activities, inline=False)
        embed.add_field(name="Expectations", value=expectations, inline=False)
        
        await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Applications(bot))
