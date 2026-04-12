import discord
from discord import app_commands
from discord.ext import commands
import random
import logging
from datetime import datetime, timezone

class Gamification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {} # user_id -> datetime

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        now = datetime.now(timezone.utc)
        user_id = str(message.author.id)

        # Simple 60-second cooldown per user to prevent spam
        last_time = self.cooldowns.get(user_id)
        if last_time and (now - last_time).total_seconds() < 60:
            return
            
        self.cooldowns[user_id] = now
        
        xp_gain = random.randint(15, 25)
        
        try:
            # Async DB execute
            await self.bot.sheets_client._execute(
                '''
                INSERT INTO user_xp (user_id, xp, level, last_message) 
                VALUES (%s, %s, 1, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    xp = user_xp.xp + EXCLUDED.xp,
                    last_message = CURRENT_TIMESTAMP
                ''', 
                user_id, xp_gain
            )

            # Level up check
            user_data = await self.bot.sheets_client._fetchrow("SELECT xp, level FROM user_xp WHERE user_id = %s", user_id)
            if user_data:
                current_xp = user_data['xp']
                current_level = user_data['level']
                # Level up formula: 5 * (level ^ 2) + 50 * level + 100
                xp_needed = 5 * (current_level ** 2) + 50 * current_level + 100
                
                if current_xp >= xp_needed:
                    new_level = current_level + 1
                    await self.bot.sheets_client._execute("UPDATE user_xp SET level = %s WHERE user_id = %s", new_level, user_id)
                    await message.channel.send(f"🎉 Congratulations {message.author.mention}, you've leveled up to **Level {new_level}**!")
        except Exception as e:
            logging.error(f"Error in on_message xp generation: {e}")

    @app_commands.command(name="rank", description="Check your current XP and Level")
    async def rank_command(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id = str(interaction.user.id)
        
        try:
            user_data = await self.bot.sheets_client._fetchrow("SELECT xp, level FROM user_xp WHERE user_id = %s", user_id)
            
            if not user_data:
                await interaction.followup.send(f"{interaction.user.mention}, you haven't earned any XP yet! Start chatting to earn some.")
                return
                
            current_xp = user_data['xp']
            current_level = user_data['level']
            xp_needed = 5 * (current_level ** 2) + 50 * current_level + 100
            
            embed = discord.Embed(title=f"📊 {interaction.user.display_name}'s Rank", color=discord.Color.gold())
            embed.set_thumbnail(url=interaction.user.display_avatar.url if interaction.user.display_avatar else None)
            embed.add_field(name="Level", value=f"**{current_level}**", inline=True)
            embed.add_field(name="XP", value=f"**{current_xp} / {xp_needed}**", inline=True)
            
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logging.error(f"Error fetching rank: {e}")
            await interaction.followup.send("❌ Error fetching rank.", ephemeral=True)

    @app_commands.command(name="leaderboard", description="View the top 10 most active members")
    async def leaderboard_command(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        try:
            top_users = await self.bot.sheets_client._fetch("SELECT user_id, xp, level FROM user_xp ORDER BY xp DESC LIMIT 10")
            
            if not top_users:
                await interaction.followup.send("The leaderboard is currently empty.")
                return

            embed = discord.Embed(title="🏆 Server Leaderboard", color=discord.Color.purple())
            
            description = ""
            for index, user in enumerate(top_users, start=1):
                member = interaction.guild.get_member(int(user['user_id']))
                name = member.display_name if member else f"Unknown User ({user['user_id']})"
                description += f"**#{index}** {name} - Level {user['level']} ({user['xp']} XP)\n"
                
            embed.description = description
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logging.error(f"Error fetching leaderboard: {e}")
            await interaction.followup.send("❌ Error fetching leaderboard.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Gamification(bot))
