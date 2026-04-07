# logs.py - Complete Logging System
import discord
from discord.ext import commands
import json
from datetime import datetime

class Logs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return
        
        log_channel = await self.get_log_channel(message.guild)
        if not log_channel:
            return
        
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Author", value=message.author.mention, inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Content", value=message.content[:1000] or "[Empty/Media]", inline=False)
        
        await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or before.content == after.content:
            return
        
        log_channel = await self.get_log_channel(before.guild)
        if not log_channel:
            return
        
        embed = discord.Embed(
            title="✏️ Message Edited",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Author", value=before.author.mention, inline=True)
        embed.add_field(name="Channel", value=before.channel.mention, inline=True)
        embed.add_field(name="Before", value=before.content[:500] or "[Empty]", inline=False)
        embed.add_field(name="After", value=after.content[:500] or "[Empty]", inline=False)
        
        await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        log_channel = await self.get_log_channel(member.guild)
        if not log_channel:
            return
        
        embed = discord.Embed(
            title="👤 Member Joined",
            description=f"{member.mention} ({member.name}#{member.discriminator})",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Member ID", value=member.id, inline=True)
        
        await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        log_channel = await self.get_log_channel(member.guild)
        if not log_channel:
            return
        
        embed = discord.Embed(
            title="👤 Member Left",
            description=f"{member.mention} ({member.name}#{member.discriminator})",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name="Member ID", value=member.id, inline=True)
        
        await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return
        
        embed = discord.Embed(
            title="🔨 Member Banned",
            description=f"{user.mention} ({user.name}#{user.discriminator})",
            color=discord.Color.dark_red(),
            timestamp=datetime.now()
        )
        embed.add_field(name="User ID", value=user.id, inline=True)
        
        await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return
        
        embed = discord.Embed(
            title="✅ Member Unbanned",
            description=f"{user.mention} ({user.name}#{user.discriminator})",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="User ID", value=user.id, inline=True)
        
        await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        log_channel = await self.get_log_channel(member.guild)
        if not log_channel:
            return
        
        if before.channel != after.channel:
            if after.channel:
                embed = discord.Embed(
                    title="🔊 Joined Voice",
                    description=f"{member.mention} joined {after.channel.mention}",
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
            elif before.channel:
                embed = discord.Embed(
                    title="🔇 Left Voice",
                    description=f"{member.mention} left {before.channel.mention}",
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
            else:
                return
            
            await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        log_channel = await self.get_log_channel(role.guild)
        if not log_channel:
            return
        
        embed = discord.Embed(
            title="➕ Role Created",
            description=f"Role: {role.mention}",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Role ID", value=role.id, inline=True)
        
        await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        log_channel = await self.get_log_channel(role.guild)
        if not log_channel:
            return
        
        embed = discord.Embed(
            title="➖ Role Deleted",
            description=f"Role: {role.name}",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Role ID", value=role.id, inline=True)
        
        await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        log_channel = await self.get_log_channel(channel.guild)
        if not log_channel:
            return
        
        embed = discord.Embed(
            title="➕ Channel Created",
            description=f"{channel.mention} ({channel.type})",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        log_channel = await self.get_log_channel(channel.guild)
        if not log_channel:
            return
        
        embed = discord.Embed(
            title="➖ Channel Deleted",
            description=f"Name: {channel.name} ({channel.type})",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        await log_channel.send(embed=embed)
    
    @commands.command(name="setlog")
    @commands.has_permissions(administrator=True)
    async def setlog(self, ctx, channel: discord.TextChannel = None):
        """Set the logging channel"""
        with open("config.json", "r") as f:
            config = json.load(f)
        
        if channel is None:
            config["log_channel"] = None
            await ctx.send("✅ Logging disabled!")
        else:
            config["log_channel"] = channel.id
            await ctx.send(f"✅ Log channel set to {channel.mention}")
        
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)
    
    @commands.command(name="setwelcome")
    @commands.has_permissions(administrator=True)
    async def setwelcome(self, ctx, channel: discord.TextChannel = None):
        """Set the welcome message channel"""
        with open("config.json", "r") as f:
            config = json.load(f)
        
        if channel is None:
            config["welcome_channel"] = None
            await ctx.send("✅ Welcome messages disabled!")
        else:
            config["welcome_channel"] = channel.id
            await ctx.send(f"✅ Welcome channel set to {channel.mention}")
        
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)
    
    @commands.command(name="setgoodbye")
    @commands.has_permissions(administrator=True)
    async def setgoodbye(self, ctx, channel: discord.TextChannel = None):
        """Set the goodbye message channel"""
        with open("config.json", "r") as f:
            config = json.load(f)
        
        if channel is None:
            config["goodbye_channel"] = None
            await ctx.send("✅ Goodbye messages disabled!")
        else:
            config["goodbye_channel"] = channel.id
            await ctx.send(f"✅ Goodbye channel set to {channel.mention}")
        
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)
    
    @commands.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx):
        """Quick setup guide for logs and welcome"""
        embed = discord.Embed(
            title="🔧 Notorious 47 - Setup Guide",
            description="Run these commands to set up your bot:",
            color=discord.Color.green()
        )
        embed.add_field(name="1. Log Channel", value=f"`{ctx.prefix}setlog #channel`", inline=False)
        embed.add_field(name="2. Welcome Channel", value=f"`{ctx.prefix}setwelcome #channel`", inline=False)
        embed.add_field(name="3. Goodbye Channel", value=f"`{ctx.prefix}setgoodbye #channel`", inline=False)
        embed.add_field(name="4. Auto-Role", value=f"`{ctx.prefix}autorole @role`", inline=False)
        embed.add_field(name="5. Change Prefix", value=f"`{ctx.prefix}changeprefix newprefix`", inline=False)
        embed.add_field(name="6. Auto-Mod", value=f"`{ctx.prefix}automod` to view settings", inline=False)
        await ctx.send(embed=embed)
    
    async def get_log_channel(self, guild):
        with open("config.json", "r") as f:
            config = json.load(f)
        
        channel_id = config.get("log_channel")
        if channel_id:
            return self.bot.get_channel(channel_id)
        return None

async def setup(bot):
    await bot.add_cog(Logs(bot))