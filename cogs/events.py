import aiohttp
import discord
from discord.ext import commands
import logging
import config
import re


def camel_to_title(name):
    return re.sub(r"(?<!^)(?=[A-Z])", " ", name).title()


async def _trigger_calendar_revalidation():
    """Notify the website to revalidate its calendar cache after approval."""
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{config.SITE_URL}/api/revalidate",
                json={"secret": config.REVALIDATION_SECRET},
                timeout=aiohttp.ClientTimeout(total=5),
            )
    except Exception as e:
        logging.warning(f"Calendar revalidation failed (non-fatal): {e}")


class EventApprovalView(discord.ui.View):
    def __init__(self, event_id: str):
        super().__init__(timeout=None)
        self.event_id = event_id

    @discord.ui.button(
        label="Approve",
        style=discord.ButtonStyle.success,
        custom_id="approve_event_button",
    )
    async def approve_callback(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)

        success = await interaction.client.sheets_client.async_accept_event_submission(
            self.event_id
        )

        if success:
            feedback_message = f"✅ **Approved event {self.event_id}.**"
            log_message = (
                f"Admin '{interaction.user.name}' approved event {self.event_id}."
            )
            new_embed_color = discord.Color.green()
            await _trigger_calendar_revalidation()
        else:
            feedback_message = f"❌ **Failed to approve event {self.event_id}.** Check if it was already handled."
            log_message = f"Admin '{interaction.user.name}' failed to approve event {self.event_id}."
            new_embed_color = discord.Color.orange()

        logging.info(log_message)
        await interaction.followup.send(feedback_message, ephemeral=True)

        original_embed = interaction.message.embeds[0]
        new_embed = original_embed.copy()
        new_embed.color = new_embed_color
        new_embed.set_footer(text=f"Approved by {interaction.user.name}")

        for item in self.children:
            item.disabled = True
        await interaction.message.edit(embed=new_embed, view=self)

    @discord.ui.button(
        label="Reject",
        style=discord.ButtonStyle.danger,
        custom_id="reject_event_button",
    )
    async def reject_callback(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)

        success = await interaction.client.sheets_client.async_reject_event_submission(
            self.event_id
        )

        if success:
            feedback_message = f"🗑️ **Rejected event {self.event_id}.**"
            log_message = (
                f"Admin '{interaction.user.name}' rejected event {self.event_id}."
            )
            new_embed_color = discord.Color.red()
        else:
            feedback_message = f"❌ **Failed to reject event {self.event_id}.** Check if it was already handled."
            log_message = f"Admin '{interaction.user.name}' failed to reject event {self.event_id}."
            new_embed_color = discord.Color.orange()

        logging.info(log_message)
        await interaction.followup.send(feedback_message, ephemeral=True)

        original_embed = interaction.message.embeds[0]
        new_embed = original_embed.copy()
        new_embed.color = new_embed_color
        new_embed.set_footer(text=f"Rejected by {interaction.user.name}")

        rejected_view = RejectedEventView(
            event_id=self.event_id, original_embed=original_embed
        )
        await interaction.message.edit(embed=new_embed, view=rejected_view)


class RejectedEventView(discord.ui.View):
    def __init__(self, event_id: str, original_embed: discord.Embed):
        super().__init__(timeout=None)
        self.event_id = event_id
        self.original_embed = original_embed

    @discord.ui.button(
        label="Changed my mind",
        style=discord.ButtonStyle.secondary,
        custom_id="undo_reject_event_button",
    )
    async def undo_reject_callback(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)

        success = await interaction.client.sheets_client.async_revert_rejection(
            self.event_id
        )

        if success:
            feedback_message = f"↩️ **Reverted rejection for event {self.event_id}.**"
            log_message = f"Admin '{interaction.user.name}' reverted rejection for event {self.event_id}."
        else:
            feedback_message = (
                f"❌ **Failed to revert rejection for event {self.event_id}.**"
            )
            log_message = f"Admin '{interaction.user.name}' failed to revert rejection for event {self.event_id}."

        logging.info(log_message)
        await interaction.followup.send(feedback_message, ephemeral=True)

        approval_view = EventApprovalView(event_id=self.event_id)
        await interaction.message.edit(embed=self.original_embed, view=approval_view)


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def post_event_approval_card(self, data: dict, event_id: str):
        """Formats and sends the interactive event approval message to the admin channel."""
        channel = self.bot.get_channel(config.ADMIN_CHANNEL_ID)
        if not channel:
            logging.error(
                f"Could not find admin channel with ID {config.ADMIN_CHANNEL_ID}"
            )
            return

        embed = discord.Embed(
            title=f"New Event Submission ({event_id})",
            description="──────────────────────────────",
            color=discord.Color.blue(),
        )

        for key, value in data.items():
            if key != "ID":  # Don't show the internal ID in the Discord message
                embed.add_field(
                    name=camel_to_title(key), value=str(value), inline=False
                )

        view = EventApprovalView(event_id=event_id)
        await channel.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(Events(bot))
