import discord
from discord import app_commands
from discord.ext import commands
import logging
import config

class QuizView(discord.ui.View):
    def __init__(self, correct_option: str):
        super().__init__(timeout=None)
        self.correct_option = correct_option
        self.answered_users = set()

    async def handle_answer(self, interaction: discord.Interaction, chosen_option: str):
        if interaction.user.id in self.answered_users:
            await interaction.response.send_message("You have already answered this quiz!", ephemeral=True)
            return
            
        self.answered_users.add(interaction.user.id)
        
        if chosen_option == self.correct_option:
            # Reward XP!
            try:
                await interaction.client.sheets_client._execute(
                    '''
                    INSERT INTO user_xp (user_id, xp, level, last_message) 
                    VALUES (%s, 50, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        xp = user_xp.xp + 50
                    ''', 
                    str(interaction.user.id)
                )
                await interaction.response.send_message("✅ Correct! You've been awarded **50 XP**!", ephemeral=True)
            except Exception as e:
                logging.error(f"Error awarding XP for quiz: {e}")
                await interaction.response.send_message("✅ Correct! (But there was an error awarding your XP, sorry!)", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Incorrect! Better luck next time.", ephemeral=True)

    @discord.ui.button(label="A", style=discord.ButtonStyle.secondary, custom_id="quiz_a")
    async def btn_a(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, "A")

    @discord.ui.button(label="B", style=discord.ButtonStyle.secondary, custom_id="quiz_b")
    async def btn_b(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, "B")

    @discord.ui.button(label="C", style=discord.ButtonStyle.secondary, custom_id="quiz_c")
    async def btn_c(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, "C")

    @discord.ui.button(label="D", style=discord.ButtonStyle.secondary, custom_id="quiz_d")
    async def btn_d(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, "D")


class Quizzes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="post_quiz", description="Post a tech quiz for the community.")
    @app_commands.describe(
        question="The quiz question",
        opt_a="Option A",
        opt_b="Option B",
        opt_c="Option C",
        opt_d="Option D",
        answer="The correct option (A, B, C, or D)"
    )
    @commands.has_permissions(administrator=True)
    async def post_quiz_command(self, interaction: discord.Interaction, question: str, opt_a: str, opt_b: str, opt_c: str, opt_d: str, answer: str):
        answer = answer.upper()
        if answer not in ["A", "B", "C", "D"]:
            await interaction.response.send_message("The answer must be exactly A, B, C, or D.", ephemeral=True)
            return

        embed = discord.Embed(title="🧠 Daily Tech Quiz", description=question, color=discord.Color.orange())
        embed.add_field(name="A", value=opt_a, inline=False)
        embed.add_field(name="B", value=opt_b, inline=False)
        embed.add_field(name="C", value=opt_c, inline=False)
        embed.add_field(name="D", value=opt_d, inline=False)
        embed.set_footer(text="Click a button below to answer. Answer correctly to earn 50 XP!")

        view = QuizView(correct_option=answer)
        
        await interaction.response.send_message("Posting quiz...", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)
        logging.info(f"Quiz posted by admin {interaction.user.name}")

async def setup(bot):
    await bot.add_cog(Quizzes(bot))
