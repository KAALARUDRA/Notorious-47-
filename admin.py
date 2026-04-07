# admin.py - Admin, Moderation, and Role Commands
import discord
from discord.ext import commands
import json
import asyncio
from datetime import datetime, timedelta

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    # ========== MODERATION COMMANDS ==========
    
    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Ban a member from the server"""
        await member.ban(reason=reason)
        embed = discord.Embed(
            title="🔨 Member Banned",
            description=f"{member.mention} has been banned",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        await ctx.send(embed=embed)
        
        # Log to mod log
        await self.log_action(ctx.guild, f"🔨 **Ban** | {member} | Reason: {reason}", discord.Color.red())
    
    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Kick a member from the server"""
        await member.kick(reason=reason)
        embed = discord.Embed(
            title="👢 Member Kicked",
            description=f"{member.mention} has been kicked",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        await ctx.send(embed=embed)
        await self.log_action(ctx.guild, f"👢 **Kick** | {member} | Reason: {reason}", discord.Color.orange())
    
    @commands.command(name="timeout", aliases=["mute"])
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member, duration: str, *, reason="No reason"):
        """Timeout a member (1m, 1h, 1d)"""
        # Parse duration
        units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        unit = duration[-1]
        if unit not in units:
            await ctx.send("❌ Invalid duration! Use: 30s, 5m, 2h, 1d")
            return
        
        try:
            amount = int(duration[:-1])
            seconds = amount * units[unit]
            if seconds > 2419200:  # 28 days max
                await ctx.send("❌ Timeout cannot exceed 28 days!")
                return
        except:
            await ctx.send("❌ Invalid duration format!")
            return
        
        until = discord.utils.utcnow() + timedelta(seconds=seconds)
        await member.timeout(until, reason=reason)
        
        embed = discord.Embed(
            title="🔇 Member Timed Out",
            description=f"{member.mention} has been timed out",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Duration", value=duration, inline=True)
        embed.add_field(name="Reason", value=reason, inline=True)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        await ctx.send(embed=embed)
        await self.log_action(ctx.guild, f"🔇 **Timeout** | {member} | {duration} | {reason}", discord.Color.gold())
    
    @commands.command(name="warn")
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason="No reason"):
        """Warn a member (auto-ban after 3 warnings)"""
        # Load warnings
        try:
            with open("warnings.json", "r") as f:
                warnings = json.load(f)
        except:
            warnings = {}
        
        key = str(member.id)
        if key not in warnings:
            warnings[key] = []
        
        warnings[key].append({
            "reason": reason,
            "mod": ctx.author.name,
            "time": datetime.now().isoformat(),
            "guild": ctx.guild.id
        })
        
        with open("warnings.json", "w") as f:
            json.dump(warnings, f, indent=4)
        
        warn_count = len(warnings[key])
        
        if warn_count >= 3:
            await member.ban(reason=f"Auto-ban - 3 warnings. Last: {reason}")
            await ctx.send(f"⚠️ {member.mention} has been **auto-banned** for reaching 3 warnings!")
            await self.log_action(ctx.guild, f"⚠️ **Auto-Ban** | {member} | 3 warnings reached", discord.Color.dark_red())
        else:
            embed = discord.Embed(
                title="⚠️ Member Warned",
                description=f"{member.mention} has been warned",
                color=discord.Color.yellow(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Warnings", value=f"{warn_count}/3", inline=True)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            await ctx.send(embed=embed)
            await self.log_action(ctx.guild, f"⚠️ **Warning** | {member} | {reason} ({warn_count}/3)", discord.Color.yellow())
    
    @commands.command(name="clear", aliases=["purge"])
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int = 5, member: discord.Member = None):
        """Clear messages (max 100)"""
        if amount > 100:
            amount = 100
        
        def check_user(m):
            return member is None or m.author == member
        
        deleted = await ctx.channel.purge(limit=amount + 1, check=check_user)
        
        if member:
            msg = await ctx.send(f"🗑️ Deleted {len(deleted)-1} messages from {member.mention}")
        else:
            msg = await ctx.send(f"🗑️ Deleted {len(deleted)-1} messages")
        
        await asyncio.sleep(3)
        await msg.delete()
        await self.log_action(ctx.guild, f"🗑️ **Clear** | {len(deleted)-1} messages deleted by {ctx.author}", discord.Color.blue())
    
    @commands.command(name="slowmode")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int = 0):
        """Set slowmode in seconds (0 to disable)"""
        if seconds > 21600:
            await ctx.send("❌ Slowmode cannot exceed 6 hours (21600 seconds)!")
            return
        
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await ctx.send("✅ Slowmode disabled!")
        else:
            await ctx.send(f"✅ Slowmode set to {seconds} seconds!")
        await self.log_action(ctx.guild, f"⏱️ **Slowmode** | {seconds}s in #{ctx.channel.name}", discord.Color.blue())
    
    @commands.command(name="lock")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx, channel: discord.TextChannel = None):
        """Lock a channel"""
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send(f"🔒 {channel.mention} has been locked!")
        await self.log_action(ctx.guild, f"🔒 **Lock** | #{channel.name} locked by {ctx.author}", discord.Color.blue())
    
    @commands.command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        """Unlock a channel"""
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send(f"🔓 {channel.mention} has been unlocked!")
        await self.log_action(ctx.guild, f"🔓 **Unlock** | #{channel.name} unlocked by {ctx.author}", discord.Color.blue())
    
    # ========== ROLE COMMANDS ==========
    
    @commands.command(name="addrole")
    @commands.has_permissions(manage_roles=True)
    async def addrole(self, ctx, member: discord.Member, role: discord.Role):
        """Add a role to a member"""
        if role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ You cannot add a role higher than or equal to your top role!")
            return
        
        await member.add_roles(role, reason=f"Added by {ctx.author}")
        await ctx.send(f"✅ Added {role.mention} to {member.mention}")
        await self.log_action(ctx.guild, f"➕ **Add Role** | {role.name} added to {member} by {ctx.author}", discord.Color.green())
    
    @commands.command(name="removerole")
    @commands.has_permissions(manage_roles=True)
    async def removerole(self, ctx, member: discord.Member, role: discord.Role):
        """Remove a role from a member"""
        if role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ You cannot remove a role higher than or equal to your top role!")
            return
        
        await member.remove_roles(role, reason=f"Removed by {ctx.author}")
        await ctx.send(f"✅ Removed {role.mention} from {member.mention}")
        await self.log_action(ctx.guild, f"➖ **Remove Role** | {role.name} removed from {member} by {ctx.author}", discord.Color.red())
    
    @commands.command(name="autorole")
    @commands.has_permissions(administrator=True)
    async def autorole(self, ctx, role: discord.Role = None):
        """Set auto-role for new members"""
        if role is None:
            with open("config.json", "r") as f:
                config = json.load(f)
            config["autorole"] = None
            with open("config.json", "w") as f:
                json.dump(config, f, indent=4)
            await ctx.send("✅ Auto-role disabled!")
            return
        
        with open("config.json", "r") as f:
            config = json.load(f)
        config["autorole"] = role.id
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)
        await ctx.send(f"✅ Auto-role set to {role.mention}")
    
    # ========== RAID PROTECTION ==========
    
    @commands.command(name="raidmode")
    @commands.has_permissions(administrator=True)
    async def raidmode(self, ctx, state: str = None):
        """Enable/disable raid mode"""
        if state is None:
            await ctx.send("Usage: `$raidmode on` or `$raidmode off`")
            return
        
        with open("config.json", "r") as f:
            config = json.load(f)
        
        if state.lower() == "on":
            config["raidmode"] = True
            await ctx.send("🛡️ **RAID MODE ENABLED** - Suspicious joins will be auto-kicked!")
        elif state.lower() == "off":
            config["raidmode"] = False
            await ctx.send("✅ Raid mode disabled!")
        else:
            await ctx.send("❌ Invalid state! Use `on` or `off`")
            return
        
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)
    
    # ========== UTILITY ==========
    
    @commands.command(name="ping")
    async def ping(self, ctx):
        """Check bot latency"""
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Latency: **{latency}ms**",
            color=discord.Color.green() if latency < 100 else discord.Color.orange() if latency < 200 else discord.Color.red()
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="serverinfo")
    async def serverinfo(self, ctx):
        """Get server information"""
        guild = ctx.guild
        embed = discord.Embed(
            title=f"📊 {guild.name}",
            description=guild.description or "No description",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.add_field(name="👑 Owner", value=guild.owner.mention, inline=True)
        embed.add_field(name="👥 Members", value=guild.member_count, inline=True)
        embed.add_field(name="💬 Channels", value=len(guild.channels), inline=True)
        embed.add_field(name="🎭 Roles", value=len(guild.roles), inline=True)
        embed.add_field(name="📅 Created", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="🔒 Boost Level", value=guild.premium_tier, inline=True)
        await ctx.send(embed=embed)
    
    @commands.command(name="userinfo", aliases=["whois"])
    async def userinfo(self, ctx, member: discord.Member = None):
        """Get user information"""
        member = member or ctx.author
        embed = discord.Embed(
            title=f"👤 {member.name}",
            color=member.color,
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Joined Discord", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Top Role", value=member.top_role.mention, inline=True)
        embed.add_field(name="Is Bot?", value="✅" if member.bot else "❌", inline=True)
        await ctx.send(embed=embed)
    
    @commands.command(name="avatar")
    async def avatar(self, ctx, member: discord.Member = None):
        """Get user avatar"""
        member = member or ctx.author
        embed = discord.Embed(
            title=f"🖼️ {member.name}'s Avatar",
            color=discord.Color.blue()
        )
        embed.set_image(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await ctx.send(embed=embed)
    
    # ========== LOGGING HELPER ==========
    
    async def log_action(self, guild, action, color):
        with open("config.json", "r") as f:
            config = json.load(f)
        
        log_channel_id = config.get("log_channel")
        if log_channel_id:
            channel = self.bot.get_channel(log_channel_id)
            if channel:
                embed = discord.Embed(
                    description=action,
                    color=color,
                    timestamp=datetime.now()
                )
                await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Admin(bot))