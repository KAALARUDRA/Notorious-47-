# games.py - Fun Games
import discord
from discord.ext import commands
import random
import asyncio
from datetime import datetime

class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.trivia_questions = {
            "What is the capital of France?": "Paris",
            "What is 2+2?": "4",
            "Who painted the Mona Lisa?": "Leonardo da Vinci",
            "What is the largest ocean on Earth?": "Pacific Ocean",
            "Who wrote Romeo and Juliet?": "William Shakespeare",
            "What is the fastest land animal?": "Cheetah",
            "What is the chemical symbol for gold?": "Au",
            "Who painted the Sistine Chapel?": "Michelangelo",
            "What is the tallest mountain in the world?": "Mount Everest",
            "What is the currency of Japan?": "Yen"
        }
    
    @commands.command(name="roll", aliases=["dice"])
    async def roll(self, ctx, dice: int = 6):
        """Roll a dice (default 6 sides)"""
        if dice < 1:
            dice = 1
        if dice > 100:
            dice = 100
        
        result = random.randint(1, dice)
        embed = discord.Embed(
            title="🎲 Dice Roll",
            description=f"{ctx.author.mention} rolled a **{result}**",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"1-{dice} dice")
        await ctx.send(embed=embed)
    
    @commands.command(name="8ball", aliases=["eightball"])
    async def eight_ball(self, ctx, *, question):
        """Ask the magic 8-ball a question"""
        responses = [
            "Yes, definitely!", "It is certain.", "Without a doubt.",
            "Most likely.", "Signs point to yes.", "Ask again later.",
            "Better not tell you now.", "Cannot predict now.",
            "Concentrate and ask again.", "Don't count on it.",
            "My reply is no.", "Very doubtful.", "No way!",
            "Absolutely!", "Never in a million years."
        ]
        
        embed = discord.Embed(
            title="🎱 Magic 8-Ball",
            color=discord.Color.purple()
        )
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=random.choice(responses), inline=False)
        embed.set_footer(text=f"Asked by {ctx.author.name}")
        await ctx.send(embed=embed)
    
    @commands.command(name="rps")
    async def rps(self, ctx, choice: str):
        """Play Rock Paper Scissors against the bot"""
        choices = ["rock", "paper", "scissors"]
        bot_choice = random.choice(choices)
        player_choice = choice.lower()
        
        if player_choice not in choices:
            await ctx.send("❌ Invalid choice! Choose: rock, paper, or scissors")
            return
        
        # Determine winner
        if player_choice == bot_choice:
            result = "It's a tie! 🤝"
            color = discord.Color.gold()
        elif (player_choice == "rock" and bot_choice == "scissors") or \
             (player_choice == "paper" and bot_choice == "rock") or \
             (player_choice == "scissors" and bot_choice == "paper"):
            result = "You win! 🎉"
            color = discord.Color.green()
        else:
            result = "I win! 😎"
            color = discord.Color.red()
        
        embed = discord.Embed(
            title="✊ Rock Paper Scissors",
            color=color
        )
        embed.add_field(name="You chose", value=f"🪨 {player_choice}" if player_choice == "rock" else f"📄 {player_choice}" if player_choice == "paper" else f"✂️ {player_choice}", inline=True)
        embed.add_field(name="Bot chose", value=f"🪨 {bot_choice}" if bot_choice == "rock" else f"📄 {bot_choice}" if bot_choice == "paper" else f"✂️ {bot_choice}", inline=True)
        embed.add_field(name="Result", value=result, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="guess", aliases=["number"])
    async def guess_number(self, ctx):
        """Guess a number between 1-100"""
        number = random.randint(1, 100)
        attempts = 0
        
        await ctx.send("🎯 I'm thinking of a number between 1 and 100! You have 10 attempts.")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
        
        while attempts < 10:
            try:
                msg = await self.bot.wait_for('message', timeout=30.0, check=check)
                guess = int(msg.content)
                attempts += 1
                
                if guess < number:
                    await ctx.send(f"📈 Too low! ({10-attempts} attempts left)")
                elif guess > number:
                    await ctx.send(f"📉 Too high! ({10-attempts} attempts left)")
                else:
                    await ctx.send(f"🎉 Correct! You guessed it in {attempts} attempts!")
                    return
            except asyncio.TimeoutError:
                await ctx.send(f"⏰ Time's up! The number was {number}")
                return
        
        await ctx.send(f"😔 Out of attempts! The number was {number}")
    
    @commands.command(name="trivia")
    async def trivia(self, ctx):
        """Answer a trivia question"""
        question, answer = random.choice(list(self.trivia_questions.items()))
        
        await ctx.send(f"📚 **Trivia Time!**\n\n{question}\n\nYou have 20 seconds to answer!")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            msg = await self.bot.wait_for('message', timeout=20.0, check=check)
            if msg.content.lower().strip() == answer.lower():
                await ctx.send(f"✅ Correct! The answer is {answer}")
            else:
                await ctx.send(f"❌ Wrong! The correct answer is {answer}")
        except asyncio.TimeoutError:
            await ctx.send(f"⏰ Time's up! The answer was {answer}")
    
    @commands.command(name="coinflip", aliases=["flip"])
    async def coinflip(self, ctx):
        """Flip a coin"""
        result = random.choice(["Heads", "Tails"])
        
        embed = discord.Embed(
            title="🪙 Coin Flip",
            description=f"The coin landed on **{result}**!",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="slots")
    async def slots(self, ctx):
        """Play slot machine"""
        emojis = ["🍒", "🍊", "🍋", "🍉", "⭐", "💎", "7️⃣"]
        slot1 = random.choice(emojis)
        slot2 = random.choice(emojis)
        slot3 = random.choice(emojis)
        
        if slot1 == slot2 == slot3:
            result = "🎉 JACKPOT! You win! 🎉"
            color = discord.Color.green()
        elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
            result = "✨ You got a pair! ✨"
            color = discord.Color.gold()
        else:
            result = "😔 Better luck next time!"
            color = discord.Color.red()
        
        embed = discord.Embed(
            title="🎰 Slot Machine",
            description=f"| {slot1} | {slot2} | {slot3} |\n\n{result}",
            color=color
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Games(bot))