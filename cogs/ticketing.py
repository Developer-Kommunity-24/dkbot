import discord
from discord import app_commands
from discord.ext import commands
import logging
import config

class TicketModal(discord.ui.Modal, title='Create a Query Ticket'):
    query_title = discord.ui.TextInput(
        label='Brief Title',
        placeholder='e.g., Question about Hackathon Timings',
        required=True,
        max_length=100
    )

    query_description = discord.ui.TextInput(
        label='Details',
        style=discord.TextStyle.paragraph,
        placeholder='Please describe your query in detail...',
        required=True,
        max_length=2000
    )

    def __init__(self, event_name: str):
        super().__init__()
        self.event_name = event_name

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        user = interaction.user

        # Create a new channel for the ticket
        # Create under the same category as the current channel if possible
        category = interaction.channel.category
        
        # Define permissions: Admins and the user can see, everyone else cannot
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        # Add admin role overwrites if you have a specific admin role, 
        # or rely on server admin permissions which bypass overwrites.

        ticket_channel_name = f"ticket-{user.name[:10]}-{self.query_title.value[:10]}"
        # Clean channel name
        ticket_channel_name = "".join(c for c in ticket_channel_name if c.isalnum() or c == '-').lower()

        try:
            ticket_channel = await guild.create_text_channel(
                name=ticket_channel_name,
                category=category,
                overwrites=overwrites,
                reason=f"Ticket created by {user.name} for event {self.event_name}"
            )

            # Send the initial message in the ticket channel
            embed = discord.Embed(
                title=f"Ticket: {self.query_title.value}",
                description=self.query_description.value,
                color=discord.Color.gold()
            )
            embed.set_author(name=user.display_name, icon_url=user.display_avatar.url if user.display_avatar else None)
            embed.add_field(name="Event", value=self.event_name, inline=False)
            embed.set_footer(text="An admin will be with you shortly. Use the button below to close this ticket.")

            view = TicketControlView()
            await ticket_channel.send(f"{user.mention} Welcome to your ticket! Please wait for an admin.", embed=embed, view=view)

            await interaction.followup.send(f"✅ Your ticket has been created: {ticket_channel.mention}", ephemeral=True)
            logging.info(f"Ticket channel {ticket_channel.name} created for user {user.name}.")

        except Exception as e:
            logging.error(f"Failed to create ticket channel: {e}")
            await interaction.followup.send("❌ Failed to create a ticket channel. Please contact an administrator directly.", ephemeral=True)


class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket_button")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Only allow the user who opened it or an admin to close it
        # For simplicity, we'll confirm first
        await interaction.response.send_message("Are you sure you want to close this ticket? This action cannot be undone.", view=ConfirmCloseView(), ephemeral=True)


class ConfirmCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Confirm Close", style=discord.ButtonStyle.danger, custom_id="confirm_close_ticket_button")
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user.name}")
            logging.info(f"Ticket channel {interaction.channel.name} deleted by {interaction.user.name}.")
        except Exception as e:
            logging.error(f"Failed to delete ticket channel: {e}")
            await interaction.followup.send("❌ Failed to close the ticket. Please ask an admin to delete the channel manually.", ephemeral=True)


class EventAnnouncementView(discord.ui.View):
    def __init__(self, event_name: str, event_link: str = None):
        super().__init__(timeout=None)
        self.event_name = event_name

        if event_link:
            self.add_item(discord.ui.Button(label="View Details / Register", url=event_link, style=discord.ButtonStyle.link))

    @discord.ui.button(label="Create Ticket 🎫", style=discord.ButtonStyle.primary, custom_id="create_ticket_btn")
    async def create_ticket_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal(event_name=self.event_name))


class Ticketing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="announce", description="Announce an event and set up a ticket system.")
    @app_commands.describe(
        title="The title of the event",
        description="The description or details of the event",
        link="Optional link for registration or details",
        ping_everyone="Whether to ping @everyone (True) or not (False)"
    )
    @commands.has_permissions(administrator=True)
    async def announce_command(self, interaction: discord.Interaction, title: str, description: str, link: str = None, ping_everyone: bool = False):
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title=f"🎉 {title} 🎉",
            description=description,
            color=discord.Color.purple()
        )
        if link:
            embed.add_field(name="Link", value=link, inline=False)
        
        embed.set_footer(text="Have any questions? Click 'Create Ticket' below to reach out to the team!")
        
        view = EventAnnouncementView(event_name=title, event_link=link)
        
        content = "@everyone" if ping_everyone else None

        try:
            await interaction.channel.send(content=content, embed=embed, view=view)
            await interaction.followup.send("✅ Announcement posted successfully!", ephemeral=True)
            logging.info(f"Admin '{interaction.user.name}' posted an announcement for '{title}'.")
        except Exception as e:
            logging.error(f"Failed to post announcement: {e}")
            await interaction.followup.send("❌ Failed to post the announcement. Check my permissions in this channel.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Ticketing(bot), guild=discord.Object(id=config.GUILD_ID))
