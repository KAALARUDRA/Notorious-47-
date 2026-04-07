# automod.py - Advanced Auto-moderation System
import discord
from discord.ext import commands
import json
import re
from datetime import datetime, timedelta

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.filtered_words = ["fuck", "shit", "asshole", "bitch", "cunt", "nigga", "nigger", "whore", "slut", "dick", "pussy", "cock", "bastard", "damn", "hell", "porn", "xxx", "sex"]
        self.invite_pattern = re.compile(r"(discord\.gg/|discord\.com/invite/|dsc\.gg/|discordapp\.com/invite/)")
        self.raid_detection = {}
        
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        guild = message.guild
        if not guild:
            return
        
        # Load settings for this guild
        settings = self.load_settings(guild.id)
        
        # Check each filter
        if settings.get("profanity", True):
            await self.check_profanity(message)
        
        if settings.get("invites", True):
            await self.check_invites(message)
        
        if settings.get("spam", True):
            await self.check_spam(message)
        
        if settings.get("zalgo", True):
            await self.check_zalgo(message)
        
        if settings.get("max_lines", True):
            await self.check_max_lines(message)
    
    async def check_profanity(self, message):
        content_lower = message.content.lower()
        for word in self.filtered_words:
            if word in content_lower:
                await message.delete()
                await message.channel.send(f"{message.author.mention} ⚠️ Profanity is not allowed!", delete_after=3)
                await self.add_warning(message.guild.id, message.author.id, "Profanity")
                break
    
    async def check_invites(self, message):
        if self.invite_pattern.search(message.content) and not message.author.guild_permissions.administrator:
            await message.delete()
            await message.channel.send(f"{message.author.mention} 🚫 Discord invites are not allowed!", delete_after=3)
            await self.add_warning(message.guild.id, message.author.id, "Discord invite")
    
    async def check_spam(self, message):
        key = f"{message.guild.id}_{message.author.id}"
        now = datetime.now()
        
        if key not in self.raid_detection:
            self.raid_detection[key] = []
        
        self.raid_detection[key] = [t for t in self.raid_detection[key] if (now - t).total_seconds() < 5]
        self.raid_detection[key].append(now)
        
        if len(self.raid_detection[key]) > 5:
            await message.delete()
            await message.channel.send(f"{message.author.mention} ⚠️ Stop spamming!", delete_after=3)
            await self.add_warning(message.guild.id, message.author.id, "Spamming")
            self.raid_detection[key] = []
    
    async def check_zalgo(self, message):
        # Check for zalgo text (excessive combining characters)
        import unicodedata
        zalgo_count = sum(1 for c in message.content if unicodedata.combining(c))
        if zalgo_count > 10:
            await message.delete()
            await message.channel.send(f"{message.author.mention} ⚠️ Zalgo text is not allowed!", delete_after=3)
    
    async def check_max_lines(self, message):
        lines = message.content.count('\n') + 1
        if lines > 15:
            await message.delete()
            await message.channel.send(f"{message.author.mention} ⚠️ Too many lines! Max 15 lines.", delete_after=3)
    
    async def add_warning(self, guild_id, user_id, reason):
        # Load warnings
        try:
            with open("warnings.json", "r") as f:
                warnings = json.load(f)
        except:
            warnings = {}
        
        key = f"{guild_id}_{user_id}"
        if key not in warnings:
            warnings[key] = []
        
        warnings[key].append({"reason": reason, "time": datetime.now().isoformat()})
        
        # Save warnings
        with open("warnings.json", "w") as f:
            json.dump(warnings, f, indent=4)
        
        # Auto-action after 3 warnings
        if len(warnings[key]) >= 3:
            guild = self.bot.get_guild(guild_id)
            member = guild.get_member(user_id)
            if member:
                await member.ban(reason=f"Auto-ban - 3 warnings. Last: {reason}")
                
                # Log the ban
                with open("config.json", "r") as f:
                    config = json.load(f)
                log_channel = self.bot.get_channel(config.get("log_channel"))
                if log_channel:
                    await log_channel.send(f"🔨 **Auto-Ban** | {member.name} was auto-banned for 3 warnings")
    
    def load_settings(self, guild_id):
        try:
            with open(f"settings_{guild_id}.json", "r") as f:
                return json.load(f)
        except:
            default = {
                "profanity": True,
                "invites": True,
                "spam": True,
                "zalgo": True,
                "max_lines": True,
                "mass_mention": 4,
                "caps_percent": 70
            }
            return default
    
    @commands.group(name="automod")
    @commands.has_permissions(administrator=True)
    async def automod(self, ctx):
        """Auto-moderation settings"""
        if ctx.invoked_subcommand is None:
            settings = self.load_settings(ctx.guild.id)
            embed = discord.Embed(title="🛡️ Auto-mod Settings", color=discord.Color.blue())
            for key, value in settings.items():
                embed.add_field(name=key, value="✅ ON" if value else "❌ OFF", inline=True)
            await ctx.send(embed=embed)
    
    @automod.command(name="profanity")
    async def toggle_profanity(self, ctx, state: bool):
        """Toggle profanity filter"""
        settings = self.load_settings(ctx.guild.id)
        settings["profanity"] = state
        with open(f"settings_{ctx.guild.id}.json", "w") as f:
            json.dump(settings, f, indent=4)
        await ctx.send(f"✅ Profanity filter {'enabled' if state else 'disabled'}")
    
    @automod.command(name="invites")
    async def toggle_invites(self, ctx, state: bool):
        """Toggle invite filter"""
        settings = self.load_settings(ctx.guild.id)
        settings["invites"] = state
        with open(f"settings_{ctx.guild.id}.json", "w") as f:
            json.dump(settings, f, indent=4)
        await ctx.send(f"✅ Invite filter {'enabled' if state else 'disabled'}")
    
    @automod.command(name="spam")
    async def toggle_spam(self, ctx, state: bool):
        """Toggle spam filter"""
        settings = self.load_settings(ctx.guild.id)
        settings["spam"] = state
        with open(f"settings_{ctx.guild.id}.json", "w") as f:
            json.dump(settings, f, indent=4)
        await ctx.send(f"✅ Spam filter {'enabled' if state else 'disabled'}")
    
    @automod.command(name="massmention")
    async def set_mass_mention(self, ctx, limit: int):
        """Set mass mention limit (default 4)"""
        settings = self.load_settings(ctx.guild.id)
        settings["mass_mention"] = limit
        with open(f"settings_{ctx.guild.id}.json", "w") as f:
            json.dump(settings, f, indent=4)
        await ctx.send(f"✅ Mass mention limit set to {limit}")

async def setup(bot):
    await bot.add_cog(AutoMod(bot))