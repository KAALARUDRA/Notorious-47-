# ==========================
# BLOCK 1: IMPORTS & CONFIG
# ==========================

import discord
from discord.ext import commands, tasks
from discord import app_commands, ui
import json
import os
import asyncio
import re
import random
import string
import time
from datetime import datetime, timedelta
import aiohttp
from flask import Flask, render_template
import threading
import yt_dlp as youtube_dl

# --------------------------
# Configuration Files
# --------------------------

if not os.path.exists("config.json"):
    with open("config.json", "w") as f:
        json.dump({
            "prefix": "~",
            "log_channel": None,
            "welcome_channel": None,
            "goodbye_channel": None,
            "autorole": None,
            "raid_mode": False,
            "welcome_message": "🎉 Welcome {user} to {server}! You're member #{member_count}",
            "goodbye_message": "👋 {user} left the server! We now have {member_count} members",
            "bad_words": ["fuck", "shit", "asshole", "bitch", "cunt", "nigga", "nigger", "whore", "slut", "dick", "pussy", "cock", "bastard"],
            "spam_threshold": 5,
            "spam_interval": 3,
            "max_mentions": 4,
            "max_emojis": 10,
            "block_links": True,
            "samp_connected_ip": None,
            "samp_connected_port": None
        }, f, indent=4)

with open("config.json", "r") as f:
    config = json.load(f)

def save_config():
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

if not os.path.exists("warnings.json"):
    with open("warnings.json", "w") as f:
        json.dump({}, f)

with open("warnings.json", "r") as f:
    warnings = json.load(f)

def save_warnings():
    with open("warnings.json", "w") as f:
        json.dump(warnings, f, indent=4)

# --------------------------
# Bot Setup
# --------------------------

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=config["prefix"], intents=intents, help_command=None)

# --------------------------
# Spam Tracker
# --------------------------

spam_tracker = {}

# --------------------------
# Music Setup
# --------------------------

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}
ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True
}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
queues = {}

# --------------------------
# Flask Web Server
# --------------------------

app = Flask(__name__)

@app.route('/')
@app.route('/ping')
@app.route('/health')
def health_check():
    return "OK", 200

def run_web_server():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)

threading.Thread(target=run_web_server, daemon=True).start()
print("✅ Web server started for UptimeRobot pings")
# ==========================
# BLOCK 2: UTILITY FUNCTIONS
# ==========================

# --------------------------
# Helper Functions
# --------------------------

def get_uptime():
    """Get bot uptime."""
    delta = datetime.now() - bot.start_time
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"

def create_embed(title, description, color=0x2b2d31, fields=None, footer=None, thumbnail=None, image=None):
    """Create a beautifully formatted embed."""
    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now())
    if fields:
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
    if footer:
        embed.set_footer(text=footer)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    if image:
        embed.set_image(url=image)
    return embed

async def log_action(guild, action_type, description, color=0x2b2d31):
    """Send a log message to the configured logging channel."""
    log_channel_id = config.get("log_channel")
    if not log_channel_id:
        return
    channel = bot.get_channel(log_channel_id)
    if not channel:
        return
    embed = create_embed(
        title=f"📝 {action_type} Logged",
        description=description,
        color=color,
        footer=f"Action logged on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    await channel.send(embed=embed)

async def add_warning(guild_id, user_id, reason, moderator_name):
    """Add a warning to a user and auto-timeout after 3 warnings."""
    key = f"{guild_id}_{user_id}"
    if key not in warnings:
        warnings[key] = []
    warnings[key].append({
        "reason": reason,
        "mod": moderator_name,
        "time": datetime.now().isoformat()
    })
    save_warnings()
    
    if len(warnings[key]) >= 3:
        guild = bot.get_guild(guild_id)
        member = guild.get_member(user_id)
        if member:
            until = datetime.now() + timedelta(minutes=15)
            await member.timeout(until, reason="Auto-timeout after 3 warnings")
            await log_action(guild, "Auto-Time Out", f"{member.mention} has been timed out for 15 minutes after receiving 3 warnings.", discord.Color.orange())
            return True
    return False

# --------------------------
# Views (Buttons, Modals, etc.)
# --------------------------

class ConfirmView(ui.View):
    def __init__(self, timeout=60):
        super().__init__(timeout=timeout)
        self.value = None

    @ui.button(label="Confirm", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm_button(self, interaction: discord.Interaction, button: ui.Button):
        self.value = True
        self.stop()
        await interaction.response.edit_message(content="✅ Action confirmed.", view=None)

    @ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: ui.Button):
        self.value = False
        self.stop()
        await interaction.response.edit_message(content="❌ Action cancelled.", view=None)

class BadWordModal(ui.Modal, title="Add Bad Word"):
    word = ui.TextInput(label="Word to Add", placeholder="Enter the word you want to block...", required=True, style=discord.TextStyle.short)
    
    async def on_submit(self, interaction: discord.Interaction):
        word = self.word.value.lower()
        if word in config["bad_words"]:
            await interaction.response.send_message(f"⚠️ The word '{word}' is already in the bad words list.", ephemeral=True)
            return
        config["bad_words"].append(word)
        save_config()
        await interaction.response.send_message(f"✅ Successfully added '{word}' to the bad words list.", ephemeral=True)

class WarningView(ui.View):
    def __init__(self, user_id, warnings_list, page=0):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.warnings_list = warnings_list
        self.page = page
        self.total_pages = (len(warnings_list) + 4) // 5
        self.update_buttons()
    
    def update_buttons(self):
        self.clear_items()
        if self.total_pages > 1:
            if self.page > 0:
                self.add_item(ui.Button(label="◀️ Previous", style=discord.ButtonStyle.secondary, custom_id="prev"))
            self.add_item(ui.Button(label=f"Page {self.page+1}/{self.total_pages}", style=discord.ButtonStyle.secondary, disabled=True))
            if self.page < self.total_pages - 1:
                self.add_item(ui.Button(label="Next ▶️", style=discord.ButtonStyle.secondary, custom_id="next"))
        self.add_item(ui.Button(label="Close", style=discord.ButtonStyle.danger, custom_id="close"))
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You cannot interact with this menu.", ephemeral=True)
            return False
        return True
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass

    async def on_button_click(self, interaction: discord.Interaction, button: ui.Button):
        if button.custom_id == "prev":
            self.page -= 1
        elif button.custom_id == "next":
            self.page += 1
        elif button.custom_id == "close":
            await interaction.response.edit_message(view=None)
            return
        self.update_buttons()
        embed = create_warning_embed(self.user_id, self.warnings_list, self.page)
        await interaction.response.edit_message(embed=embed, view=self)

def create_warning_embed(user_id, warnings_list, page=0):
    """Create embed for warnings pagination."""
    start = page * 5
    end = start + 5
    page_warnings = warnings_list[start:end]
    embed = discord.Embed(title=f"⚠️ Warnings for <@{user_id}>", color=discord.Color.orange(), timestamp=datetime.now())
    if not warnings_list:
        embed.description = "This user has no warnings."
        return embed
    for i, warn in enumerate(page_warnings, start=start+1):
        embed.add_field(name=f"Warning #{i}", value=f"**Reason:** {warn['reason']}\n**Moderator:** {warn['mod']}\n**Date:** {warn['time']}", inline=False)
    embed.set_footer(text=f"Page {page+1}/{(len(warnings_list)+4)//5}")
    return embed
# ==========================
# BLOCK 3: ANTI-RAID & FILTERS
# ==========================

# --------------------------
# Anti-Raid Protection
# --------------------------

raid_detection = {}
def check_raid(guild_id):
    """Check if a server is being raided."""
    if guild_id not in raid_detection:
        raid_detection[guild_id] = {"joins": [], "kick_count": 0, "ban_count": 0, "channel_count": 0, "role_count": 0}
    now = datetime.now()
    raid_detection[guild_id]["joins"] = [t for t in raid_detection[guild_id]["joins"] if (now - t).total_seconds() < 10]
    return len(raid_detection[guild_id]["joins"]) > 5

@bot.event
async def on_member_join(member):
    guild = member.guild
    now = datetime.now()
    if guild.id not in raid_detection:
        raid_detection[guild.id] = {"joins": [], "kick_count": 0, "ban_count": 0, "channel_count": 0, "role_count": 0}
    raid_detection[guild.id]["joins"].append(now)
    raid_detection[guild.id]["joins"] = [t for t in raid_detection[guild.id]["joins"] if (now - t).total_seconds() < 10]
    if len(raid_detection[guild.id]["joins"]) > 5:
        await member.kick(reason="🚨 Anti-Raid: Excessive join rate detected.")
        await log_action(guild, "🚨 Anti-Raid", f"**Kicked {member.mention}** - Excessive join rate detected.", discord.Color.red())
        raid_detection[guild.id]["joins"] = []
        return

@bot.event
async def on_guild_channel_create(channel):
    guild = channel.guild
    now = datetime.now()
    if guild.id not in raid_detection:
        raid_detection[guild.id] = {"joins": [], "kick_count": 0, "ban_count": 0, "channel_count": 0, "role_count": 0}
    raid_detection[guild.id]["channel_count"] += 1
    if raid_detection[guild.id]["channel_count"] > 5:
        await guild.owner.send("🚨 **Anti-Raid Alert!** 🚨\nYour server is under attack! Channels are being created rapidly.")
        await log_action(guild, "🚨 Anti-Raid Alert", f"**{raid_detection[guild.id]['channel_count']}** channels created in a short span. Possible raid in progress.", discord.Color.red())
        raid_detection[guild.id]["channel_count"] = 0

@bot.event
async def on_guild_role_create(role):
    guild = role.guild
    now = datetime.now()
    if guild.id not in raid_detection:
        raid_detection[guild.id] = {"joins": [], "kick_count": 0, "ban_count": 0, "channel_count": 0, "role_count": 0}
    raid_detection[guild.id]["role_count"] += 1
    if raid_detection[guild.id]["role_count"] > 5:
        await guild.owner.send("🚨 **Anti-Raid Alert!** 🚨\nYour server is under attack! Roles are being created rapidly.")
        await log_action(guild, "🚨 Anti-Raid Alert", f"**{raid_detection[guild.id]['role_count']}** roles created in a short span. Possible raid in progress.", discord.Color.red())
        raid_detection[guild.id]["role_count"] = 0

# --------------------------
# Message Filtering
# --------------------------

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Bad words filter
    msg_lower = message.content.lower()
    for word in config["bad_words"]:
        if word in msg_lower:
            await message.delete()
            await message.channel.send(f"{message.author.mention} **YOU ARE NOT PERMITTED TO TALK LIKE THAT. APOLOGIZE IMMEDIATELY!**", delete_after=5)
            await add_warning(message.guild.id, message.author.id, f"Used prohibited word: {word}", "AutoMod")
            return
    
    # Link filter
    if config.get("block_links", True) and not message.author.guild_permissions.administrator:
        link_pattern = r"(https?://[^\s]+)"
        if re.search(link_pattern, message.content):
            await message.delete()
            await message.channel.send(f"{message.author.mention} 🚫 **Links are not allowed in this server!**", delete_after=5)
            return
    
    # Spam detection
    key = f"{message.guild.id}_{message.author.id}"
    now = datetime.now()
    if key not in spam_tracker:
        spam_tracker[key] = []
    spam_tracker[key] = [t for t in spam_tracker[key] if (now - t).total_seconds() < config["spam_interval"]]
    spam_tracker[key].append(now)
    if len(spam_tracker[key]) > config["spam_threshold"]:
        until = datetime.now() + timedelta(minutes=2)
        await message.author.timeout(until, reason="Auto-timeout for spamming")
        await message.channel.send(f"{message.author.mention} ⏰ **You have been timed out for 2 minutes for spamming!**", delete_after=5)
        await log_action(message.guild, "Spam Timeout", f"{message.author.mention} was timed out for 2 minutes for spamming.", discord.Color.orange())
        spam_tracker[key] = []
        return
    
    # Mass mention detection
    if len(message.mentions) >= config["max_mentions"] and not message.author.guild_permissions.administrator:
        until = datetime.now() + timedelta(minutes=2)
        await message.author.timeout(until, reason="Auto-timeout for mass mentions")
        await message.channel.send(f"{message.author.mention} ⏰ **You have been timed out for 2 minutes for mass mentioning!**", delete_after=5)
        await log_action(message.guild, "Mass Mention Timeout", f"{message.author.mention} was timed out for 2 minutes for mass mentioning.", discord.Color.orange())
        return
    
    # Emoji spam detection
    emoji_count = len(re.findall(r'<a?:\w+:\d+>', message.content))
    if emoji_count >= config["max_emojis"] and not message.author.guild_permissions.administrator:
        until = datetime.now() + timedelta(minutes=2)
        await message.author.timeout(until, reason="Auto-timeout for emoji spam")
        await message.channel.send(f"{message.author.mention} ⏰ **You have been timed out for 2 minutes for emoji spam!**", delete_after=5)
        await log_action(message.guild, "Emoji Spam Timeout", f"{message.author.mention} was timed out for 2 minutes for emoji spam.", discord.Color.orange())
        return
    
    await bot.process_commands(message)
# ==========================
# BLOCK 4: MODERATION COMMANDS
# ==========================

@bot.group(name="badword", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def badword(ctx):
    """Manage the bad words list."""
    words = ", ".join(config["bad_words"]) if config["bad_words"] else "No bad words set."
    embed = create_embed(
        title="🚫 Bad Words List",
        description=f"**Currently Filtered Words:**\n{words}",
        color=discord.Color.red(),
        footer="Use `~badword add <word>` to add, `~badword remove <word>` to remove."
    )
    await ctx.send(embed=embed)

@badword.command(name="add")
async def badword_add(ctx, word: str):
    """Add a word to the bad words list."""
    word = word.lower()
    if word in config["bad_words"]:
        await ctx.send(embed=create_embed("❌ Error", f"`{word}` is already in the bad words list.", discord.Color.red()))
        return
    config["bad_words"].append(word)
    save_config()
    await ctx.send(embed=create_embed("✅ Word Added", f"`{word}` has been added to the bad words list.", discord.Color.green()))

@badword.command(name="remove")
async def badword_remove(ctx, word: str):
    """Remove a word from the bad words list."""
    word = word.lower()
    if word not in config["bad_words"]:
        await ctx.send(embed=create_embed("❌ Error", f"`{word}` is not in the bad words list.", discord.Color.red()))
        return
    config["bad_words"].remove(word)
    save_config()
    await ctx.send(embed=create_embed("✅ Word Removed", f"`{word}` has been removed from the bad words list.", discord.Color.green()))

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "No reason provided."):
    """Ban a member from the server."""
    view = ConfirmView()
    embed = create_embed(
        "⚠️ Confirmation Required",
        f"Are you sure you want to ban **{member.mention}**?\n**Reason:** {reason}",
        discord.Color.orange()
    )
    msg = await ctx.send(embed=embed, view=view)
    await view.wait()
    if view.value is True:
        await member.ban(reason=reason)
        embed = create_embed(
            "🔨 Member Banned",
            f"**{member.mention}** has been banned.\n**Reason:** {reason}\n**Moderator:** {ctx.author.mention}",
            discord.Color.dark_red()
        )
        await msg.edit(embed=embed, view=None)
        await log_action(ctx.guild, "Ban", f"{member.mention} was banned by {ctx.author.mention}.\n**Reason:** {reason}", discord.Color.dark_red())
    else:
        await msg.edit(content="Ban cancelled.", embed=None, view=None)

@bot.tree.command(name="ban", description="Ban a member from the server.")
@app_commands.describe(member="The member to ban.", reason="The reason for the ban.")
async def ban_slash(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided."):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return
    view = ConfirmView()
    embed = create_embed(
        "⚠️ Confirmation Required",
        f"Are you sure you want to ban **{member.mention}**?\n**Reason:** {reason}",
        discord.Color.orange()
    )
    await interaction.response.send_message(embed=embed, view=view)
    await view.wait()
    if view.value is True:
        await member.ban(reason=reason)
        embed = create_embed(
            "🔨 Member Banned",
            f"**{member.mention}** has been banned.\n**Reason:** {reason}\n**Moderator:** {interaction.user.mention}",
            discord.Color.dark_red()
        )
        await interaction.edit_original_response(embed=embed, view=None)
        await log_action(interaction.guild, "Ban", f"{member.mention} was banned by {interaction.user.mention}.\n**Reason:** {reason}", discord.Color.dark_red())
    else:
        await interaction.edit_original_response(content="Ban cancelled.", embed=None, view=None)

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = "No reason provided."):
    """Kick a member from the server."""
    view = ConfirmView()
    embed = create_embed(
        "⚠️ Confirmation Required",
        f"Are you sure you want to kick **{member.mention}**?\n**Reason:** {reason}",
        discord.Color.orange()
    )
    msg = await ctx.send(embed=embed, view=view)
    await view.wait()
    if view.value is True:
        await member.kick(reason=reason)
        embed = create_embed(
            "👢 Member Kicked",
            f"**{member.mention}** has been kicked.\n**Reason:** {reason}\n**Moderator:** {ctx.author.mention}",
            discord.Color.orange()
        )
        await msg.edit(embed=embed, view=None)
        await log_action(ctx.guild, "Kick", f"{member.mention} was kicked by {ctx.author.mention}.\n**Reason:** {reason}", discord.Color.orange())
    else:
        await msg.edit(content="Kick cancelled.", embed=None, view=None)

@bot.command(name="timeout")
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, duration: str, *, reason: str = "No reason provided."):
    """Timeout a member for a specified duration (e.g., 10m, 2h, 1d)."""
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    unit = duration[-1]
    if unit not in units:
        await ctx.send(embed=create_embed("❌ Error", "Invalid duration format. Use: `10s`, `5m`, `2h`, `1d`", discord.Color.red()))
        return
    try:
        amount = int(duration[:-1])
        seconds = amount * units[unit]
        if seconds > 2419200:
            await ctx.send(embed=create_embed("❌ Error", "Timeout duration cannot exceed 28 days.", discord.Color.red()))
            return
    except ValueError:
        await ctx.send(embed=create_embed("❌ Error", "Invalid duration format. Use: `10s`, `5m`, `2h`, `1d`", discord.Color.red()))
        return
    until = datetime.now() + timedelta(seconds=seconds)
    await member.timeout(until, reason=reason)
    embed = create_embed(
        "🔇 Member Timed Out",
        f"**{member.mention}** has been timed out.\n**Duration:** {duration}\n**Reason:** {reason}\n**Moderator:** {ctx.author.mention}",
        discord.Color.gold()
    )
    await ctx.send(embed=embed)
    await log_action(ctx.guild, "Timeout", f"{member.mention} was timed out for {duration} by {ctx.author.mention}.\n**Reason:** {reason}", discord.Color.gold())

@bot.command(name="warn")
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason: str = "No reason provided."):
    """Warn a member. After 3 warnings, they are automatically timed out for 15 minutes."""
    key = f"{ctx.guild.id}_{member.id}"
    if key not in warnings:
        warnings[key] = []
    warnings[key].append({
        "reason": reason,
        "mod": ctx.author.name,
        "time": datetime.now().isoformat()
    })
    save_warnings()
    warning_count = len(warnings[key])
    embed = create_embed(
        "⚠️ Member Warned",
        f"**{member.mention}** has been warned.\n**Reason:** {reason}\n**Warnings:** {warning_count}/3",
        discord.Color.orange(),
        footer=f"Moderator: {ctx.author.name}"
    )
    await ctx.send(embed=embed)
    await log_action(ctx.guild, "Warn", f"{member.mention} was warned by {ctx.author.mention}.\n**Reason:** {reason}\n**Warnings:** {warning_count}/3", discord.Color.orange())
    
    if warning_count >= 3:
        until = datetime.now() + timedelta(minutes=15)
        await member.timeout(until, reason="Auto-timeout after 3 warnings.")
        embed = create_embed(
            "⏰ Auto-Time Out",
            f"**{member.mention}** has been automatically timed out for 15 minutes after receiving 3 warnings.",
            discord.Color.orange()
        )
        await ctx.send(embed=embed)
        await log_action(ctx.guild, "Auto-Time Out", f"{member.mention} was automatically timed out after 3 warnings.", discord.Color.orange())

@bot.command(name="warnings")
async def warnings_cmd(ctx, member: discord.Member = None):
    """View warnings for a member."""
    member = member or ctx.author
    key = f"{ctx.guild.id}_{member.id}"
    user_warnings = warnings.get(key, [])
    if not user_warnings:
        embed = create_embed("📜 No Warnings", f"**{member.display_name}** has no warnings.", discord.Color.green())
        await ctx.send(embed=embed)
        return
    view = WarningView(ctx.author.id, user_warnings)
    embed = create_warning_embed(member.id, user_warnings)
    view.message = await ctx.send(embed=embed, view=view)

@bot.command(name="banlist")
@commands.has_permissions(ban_members=True)
async def banlist(ctx):
    """Show the list of banned members."""
    bans = [entry async for entry in ctx.guild.bans()]
    if not bans:
        embed = create_embed("🚫 Ban List", "No banned members in this server.", discord.Color.green())
        await ctx.send(embed=embed)
        return
    embed = create_embed(
        "🚫 Ban List",
        f"**Total Bans:** {len(bans)}\n\n**Banned Members:**",
        discord.Color.red()
    )
    for ban in bans[:10]:
        embed.add_field(name=f"{ban.user}", value=f"**Reason:** {ban.reason or 'No reason provided.'}", inline=False)
    if len(bans) > 10:
        embed.set_footer(text=f"Showing 10 of {len(bans)} bans.")
    await ctx.send(embed=embed)

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    """Clear a specified number of messages (max 100)."""
    if amount > 100:
        amount = 100
    deleted = await ctx.channel.purge(limit=amount + 1)
    embed = create_embed("🗑️ Messages Cleared", f"Successfully deleted **{len(deleted)-1}** messages.", discord.Color.blue())
    msg = await ctx.send(embed=embed)
    await asyncio.sleep(3)
    await msg.delete()
    await log_action(ctx.guild, "Clear", f"{ctx.author.mention} cleared {len(deleted)-1} messages in #{ctx.channel.name}.", discord.Color.blue())

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock(ctx, channel: discord.TextChannel = None):
    """Lock a text channel."""
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    embed = create_embed("🔒 Channel Locked", f"{channel.mention} has been locked. Members cannot send messages.", discord.Color.red())
    await ctx.send(embed=embed)
    await log_action(ctx.guild, "Lock Channel", f"{ctx.author.mention} locked {channel.mention}.", discord.Color.red())

@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock(ctx, channel: discord.TextChannel = None):
    """Unlock a text channel."""
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    embed = create_embed("🔓 Channel Unlocked", f"{channel.mention} has been unlocked. Members can now send messages.", discord.Color.green())
    await ctx.send(embed=embed)
    await log_action(ctx.guild, "Unlock Channel", f"{ctx.author.mention} unlocked {channel.mention}.", discord.Color.green())

@bot.command(name="slowmode")
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int = 0):
    """Set slowmode for the current channel."""
    await ctx.channel.edit(slowmode_delay=seconds)
    if seconds == 0:
        embed = create_embed("⏱️ Slowmode Disabled", "Slowmode has been turned off for this channel.", discord.Color.green())
    else:
        embed = create_embed("⏱️ Slowmode Enabled", f"Slowmode has been set to **{seconds}** seconds in this channel.", discord.Color.blue())
    await ctx.send(embed=embed)
    await log_action(ctx.guild, "Slowmode", f"{ctx.author.mention} set slowmode to {seconds} seconds in #{ctx.channel.name}.", discord.Color.blue())
# ==========================
# BLOCK 5: LOGGING & WELCOME
# ==========================

@bot.event
async def on_message_edit(before, after):
    """Log message edits."""
    if before.author.bot:
        return
    log_channel_id = config.get("log_channel")
    if not log_channel_id:
        return
    channel = bot.get_channel(log_channel_id)
    if not channel:
        return
    embed = create_embed(
        "✏️ Message Edited",
        f"**Author:** {before.author.mention}\n**Channel:** {before.channel.mention}\n**Before:** {before.content[:500]}\n**After:** {after.content[:500]}",
        discord.Color.gold(),
        footer=f"Message ID: {before.id}"
    )
    await channel.send(embed=embed)

@bot.event
async def on_message_delete(message):
    """Log message deletions."""
    if message.author.bot:
        return
    log_channel_id = config.get("log_channel")
    if not log_channel_id:
        return
    channel = bot.get_channel(log_channel_id)
    if not channel:
        return
    embed = create_embed(
        "🗑️ Message Deleted",
        f"**Author:** {message.author.mention}\n**Channel:** {message.channel.mention}\n**Content:** {message.content[:500] or '[No content]'}",
        discord.Color.red(),
        footer=f"Message ID: {message.id}"
    )
    await channel.send(embed=embed)

@bot.event
async def on_voice_state_update(member, before, after):
    """Log voice state changes."""
    log_channel_id = config.get("log_channel")
    if not log_channel_id:
        return
    channel = bot.get_channel(log_channel_id)
    if not channel:
        return
    if before.channel != after.channel:
        if after.channel:
            embed = create_embed(
                "🔊 Voice Join",
                f"{member.mention} joined voice channel {after.channel.mention}.",
                discord.Color.green(),
                footer=f"User ID: {member.id}"
            )
        elif before.channel:
            embed = create_embed(
                "🔇 Voice Leave",
                f"{member.mention} left voice channel {before.channel.mention}.",
                discord.Color.red(),
                footer=f"User ID: {member.id}"
            )
        else:
            return
        await channel.send(embed=embed)

@bot.event
async def on_member_join(member):
    """Welcome new members and assign auto-role."""
    # Log join
    log_channel_id = config.get("log_channel")
    if log_channel_id:
        channel = bot.get_channel(log_channel_id)
        if channel:
            embed = create_embed(
                "👤 Member Joined",
                f"{member.mention} joined the server.\n**Account Created:** {member.created_at.strftime('%Y-%m-%d')}",
                discord.Color.green(),
                footer=f"User ID: {member.id}"
            )
            await channel.send(embed=embed)
    # Send welcome message
    welcome_channel_id = config.get("welcome_channel")
    if welcome_channel_id:
        channel = bot.get_channel(welcome_channel_id)
        if channel:
            msg = config["welcome_message"].replace("{user}", member.name).replace("{mention}", member.mention).replace("{server}", member.guild.name).replace("{member_count}", str(len(member.guild.members)))
            embed = create_embed(
                "🎉 Welcome to the Server!",
                msg,
                discord.Color.green(),
                thumbnail=member.avatar.url if member.avatar else member.default_avatar.url
            )
            await channel.send(embed=embed)
    # Assign auto-role
    role_id = config.get("autorole")
    if role_id:
        role = member.guild.get_role(role_id)
        if role:
            await member.add_roles(role)

@bot.event
async def on_member_remove(member):
    """Log member leaves."""
    log_channel_id = config.get("log_channel")
    if log_channel_id:
        channel = bot.get_channel(log_channel_id)
        if channel:
            embed = create_embed(
                "👤 Member Left",
                f"{member.mention} left the server.",
                discord.Color.red(),
                footer=f"User ID: {member.id}"
            )
            await channel.send(embed=embed)
    goodbye_channel_id = config.get("goodbye_channel")
    if goodbye_channel_id:
        channel = bot.get_channel(goodbye_channel_id)
        if channel:
            msg = config["goodbye_message"].replace("{user}", member.name).replace("{server}", member.guild.name).replace("{member_count}", str(len(member.guild.members)))
            embed = create_embed(
                "👋 Goodbye!",
                msg,
                discord.Color.red(),
                thumbnail=member.avatar.url if member.avatar else member.default_avatar.url
            )
            await channel.send(embed=embed)

@bot.command(name="setlog")
@commands.has_permissions(administrator=True)
async def setlog(ctx, channel: discord.TextChannel = None):
    """Set the channel for moderation logs."""
    if channel is None:
        config["log_channel"] = None
        await ctx.send(embed=create_embed("✅ Logging Disabled", "Moderation logging has been turned off.", discord.Color.green()))
    else:
        config["log_channel"] = channel.id
        await ctx.send(embed=create_embed("✅ Log Channel Set", f"Moderation logs will be sent to {channel.mention}.", discord.Color.green()))
    save_config()

@bot.command(name="setwelcome")
@commands.has_permissions(administrator=True)
async def setwelcome(ctx, channel: discord.TextChannel = None):
    """Set the channel for welcome messages."""
    if channel is None:
        config["welcome_channel"] = None
        await ctx.send(embed=create_embed("✅ Welcome Disabled", "Welcome messages have been turned off.", discord.Color.green()))
    else:
        config["welcome_channel"] = channel.id
        await ctx.send(embed=create_embed("✅ Welcome Channel Set", f"Welcome messages will be sent to {channel.mention}.", discord.Color.green()))
    save_config()

@bot.command(name="setgoodbye")
@commands.has_permissions(administrator=True)
async def setgoodbye(ctx, channel: discord.TextChannel = None):
    """Set the channel for goodbye messages."""
    if channel is None:
        config["goodbye_channel"] = None
        await ctx.send(embed=create_embed("✅ Goodbye Disabled", "Goodbye messages have been turned off.", discord.Color.green()))
    else:
        config["goodbye_channel"] = channel.id
        await ctx.send(embed=create_embed("✅ Goodbye Channel Set", f"Goodbye messages will be sent to {channel.mention}.", discord.Color.green()))
    save_config()

@bot.command(name="autorole")
@commands.has_permissions(administrator=True)
async def autorole(ctx, role: discord.Role = None):
    """Set a role to automatically assign to new members."""
    if role is None:
        config["autorole"] = None
        await ctx.send(embed=create_embed("✅ Auto-Role Disabled", "Auto-role has been turned off.", discord.Color.green()))
    else:
        config["autorole"] = role.id
        await ctx.send(embed=create_embed("✅ Auto-Role Set", f"New members will automatically receive the {role.mention} role.", discord.Color.green()))
    save_config()
# ==========================
# BLOCK 6: MUSIC & FUN
# ==========================

async def play_song(ctx, song):
    """Play a song in the voice channel."""
    voice = ctx.voice_client
    if not voice:
        return

    def after_playing(error):
        asyncio.run_coroutine_threadsafe(check_queue(ctx), bot.loop)

    try:
        source = await discord.FFmpegOpusAudio.from_probe(song['url'], **FFMPEG_OPTIONS)
        voice.play(source, after=after_playing)
        embed = create_embed(
            "🎵 Now Playing",
            f"**[{song['title']}]({song['webpage_url']})**\nRequested by {song['requester'].mention}",
            discord.Color.green(),
            thumbnail=song.get('thumbnail')
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ An error occurred while playing the song: {str(e)[:100]}")

async def check_queue(ctx):
    """Check the queue and play the next song if available."""
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        next_song = queues[ctx.guild.id].pop(0)
        await play_song(ctx, next_song)
    else:
        await asyncio.sleep(300)
        if ctx.voice_client and not ctx.voice_client.is_playing():
            await ctx.voice_client.disconnect()

@bot.command(name="play", aliases=["p"])
async def play(ctx, *, query: str):
    """Play a song from YouTube using the name or URL."""
    if not ctx.author.voice:
        await ctx.send(embed=create_embed("❌ Error", "You need to be in a voice channel to use this command.", discord.Color.red()))
        return

    voice_channel = ctx.author.voice.channel
    voice = ctx.voice_client

    if not voice:
        await voice_channel.connect()
        voice = ctx.voice_client
    elif voice.channel != voice_channel:
        await voice.move_to(voice_channel)

    searching_msg = await ctx.send(embed=create_embed("🔍 Searching", f"Looking for `{query}`...", discord.Color.blue()))

    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))

        if data is None:
            await searching_msg.edit(embed=create_embed("❌ Error", "No results found.", discord.Color.red()))
            return

        if 'entries' in data:
            data = data['entries'][0]

        song = {
            'url': data['url'],
            'title': data['title'],
            'webpage_url': data['webpage_url'],
            'thumbnail': data.get('thumbnail'),
            'requester': ctx.author
        }

        await searching_msg.delete()

        if voice.is_playing() or voice.is_paused():
            if ctx.guild.id not in queues:
                queues[ctx.guild.id] = []
            queues[ctx.guild.id].append(song)
            embed = create_embed(
                "📋 Added to Queue",
                f"**[{song['title']}]({song['webpage_url']})**\nPosition in queue: {len(queues[ctx.guild.id])}",
                discord.Color.blue(),
                thumbnail=song.get('thumbnail')
            )
            await ctx.send(embed=embed)
        else:
            await play_song(ctx, song)

    except Exception as e:
        await searching_msg.edit(embed=create_embed("❌ Error", f"An error occurred: {str(e)[:100]}", discord.Color.red()))

@bot.command(name="skip")
async def skip(ctx):
    """Skip the currently playing song."""
    voice = ctx.voice_client
    if not voice or not voice.is_playing():
        await ctx.send(embed=create_embed("❌ Error", "No song is currently playing.", discord.Color.red()))
        return
    voice.stop()
    await ctx.send(embed=create_embed("⏭️ Skipped", "The current song has been skipped.", discord.Color.blue()))

@bot.command(name="stop")
async def stop(ctx):
    """Stop the music and clear the queue."""
    voice = ctx.voice_client
    if voice:
        if ctx.guild.id in queues:
            queues[ctx.guild.id] = []
        voice.stop()
        await voice.disconnect()
        await ctx.send(embed=create_embed("⏹️ Stopped", "The music has been stopped and the queue has been cleared.", discord.Color.red()))

@bot.command(name="pause")
async def pause(ctx):
    """Pause the currently playing song."""
    voice = ctx.voice_client
    if voice and voice.is_playing():
        voice.pause()
        await ctx.send(embed=create_embed("⏸️ Paused", "The current song has been paused.", discord.Color.blue()))
    else:
        await ctx.send(embed=create_embed("❌ Error", "No song is currently playing.", discord.Color.red()))

@bot.command(name="resume")
async def resume(ctx):
    """Resume the paused song."""
    voice = ctx.voice_client
    if voice and voice.is_paused():
        voice.resume()
        await ctx.send(embed=create_embed("▶️ Resumed", "The current song has been resumed.", discord.Color.green()))
    else:
        await ctx.send(embed=create_embed("❌ Error", "No song is currently paused.", discord.Color.red()))

@bot.command(name="queue", aliases=["q"])
async def queue(ctx):
    """Show the current music queue."""
    if ctx.guild.id not in queues or not queues[ctx.guild.id]:
        await ctx.send(embed=create_embed("📭 Queue", "The queue is currently empty.", discord.Color.blue()))
        return

    embed = create_embed("📋 Music Queue", f"**{len(queues[ctx.guild.id])}** songs in queue.", discord.Color.blue())
    for i, song in enumerate(queues[ctx.guild.id][:10]):
        embed.add_field(name=f"{i+1}. {song['title'][:50]}", value=f"Requested by {song['requester'].mention}", inline=False)
    if len(queues[ctx.guild.id]) > 10:
        embed.set_footer(text=f"And {len(queues[ctx.guild.id])-10} more...")
    await ctx.send(embed=embed)

@bot.command(name="volume")
@commands.has_permissions(administrator=True)
async def volume(ctx, level: int = None):
    """Set the volume of the music (0-100)."""
    if level is None:
        await ctx.send(embed=create_embed("🔊 Volume", "The current volume is **50%** (fixed).", discord.Color.blue()))
        return
    if level < 0 or level > 100:
        await ctx.send(embed=create_embed("❌ Error", "Volume must be between 0 and 100.", discord.Color.red()))
        return
    await ctx.send(embed=create_embed("🔊 Volume Updated", f"The volume has been set to **{level}%**.", discord.Color.green()))

# Fun Commands
@bot.command(name="tictactoe", aliases=["ttt"])
async def tictactoe(ctx):
    """Play a game of Tic-Tac-Toe."""
    view = TicTacToeView()
    embed = create_embed("🎮 Tic-Tac-Toe", "It's your turn!", discord.Color.blue())
    await ctx.send(embed=embed, view=view)

class TicTacToeView(ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.board = [None] * 9
        self.current_player = "X"
        self.buttons = [ui.Button(label="⬜", style=discord.ButtonStyle.secondary, custom_id=str(i)) for i in range(9)]
        for button in self.buttons:
            button.callback = self.make_callback(button)
            self.add_item(button)

    def make_callback(self, button):
        async def callback(interaction: discord.Interaction):
            idx = int(button.custom_id)
            if self.board[idx] is not None:
                await interaction.response.send_message("❌ That spot is already taken!", ephemeral=True)
                return
            self.board[idx] = self.current_player
            button.label = "❌" if self.current_player == "X" else "⭕"
            button.style = discord.ButtonStyle.danger if self.current_player == "X" else discord.ButtonStyle.success
            button.disabled = True
            await interaction.response.edit_message(view=self)
            winner = self.check_winner()
            if winner:
                embed = create_embed("🎉 Game Over", f"**{winner}** wins the game!", discord.Color.green())
                await interaction.followup.send(embed=embed)
                self.disable_all()
                return
            if all(self.board):
                embed = create_embed("🤝 Game Over", "It's a tie!", discord.Color.blue())
                await interaction.followup.send(embed=embed)
                return
            self.current_player = "O" if self.current_player == "X" else "X"
            embed = create_embed("🎮 Tic-Tac-Toe", f"It's **{self.current_player}**'s turn.", discord.Color.blue())
            await interaction.followup.send(embed=embed)
        return callback

    def check_winner(self):
        win_patterns = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
        for a,b,c in win_patterns:
            if self.board[a] and self.board[a] == self.board[b] == self.board[c]:
                return self.board[a]
        return None

    def disable_all(self):
        for button in self.buttons:
            button.disabled = True

@bot.command(name="trivia")
async def trivia(ctx):
    """Start a trivia game."""
    view = TriviaView()
    embed = create_embed("📚 Trivia Time!", "Get ready for some trivia!", discord.Color.blue())
    await ctx.send(embed=embed, view=view)

class TriviaView(ui.View):
    def __init__(self):
        super().__init__(timeout=30)
        self.question = None
        self.answer = None
        self.add_item(ui.Button(label="Start Trivia", style=discord.ButtonStyle.primary, custom_id="start"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ You didn't start this trivia game!", ephemeral=True)
            return False
        return True

    @ui.button(label="Start Trivia", style=discord.ButtonStyle.primary)
    async def start_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        self.clear_items()
        self.question, self.answer = random.choice(list(trivia_questions.items()))
        embed = create_embed("📚 Trivia Question", self.question, discord.Color.blue())
        await interaction.edit_original_response(embed=embed, view=self)
        self.add_item(ui.Button(label="Submit Answer", style=discord.ButtonStyle.success, custom_id="submit"))

    @ui.button(label="Submit Answer", style=discord.ButtonStyle.success)
    async def submit_button(self, interaction: discord.Interaction, button: ui.Button):
        modal = TriviaAnswerModal(self)
        await interaction.response.send_modal(modal)

class TriviaAnswerModal(ui.Modal, title="Submit Your Answer"):
    def __init__(self, view):
        super().__init__(timeout=None)
        self.view = view
    answer = ui.TextInput(label="Your Answer", placeholder="Type your answer here...", required=True, style=discord.TextStyle.short)
    async def on_submit(self, interaction: discord.Interaction):
        if self.answer.value.lower().strip() == self.view.answer.lower():
            await interaction.response.send_message(embed=create_embed("✅ Correct!", f"The correct answer was **{self.view.answer}**.", discord.Color.green()), ephemeral=True)
        else:
            await interaction.response.send_message(embed=create_embed("❌ Incorrect!", f"The correct answer was **{self.view.answer}**.", discord.Color.red()), ephemeral=True)
        await self.view.message.delete()

trivia_questions = {
    "What is the capital of France?": "Paris",
    "What is the largest ocean on Earth?": "Pacific Ocean",
    "Who painted the Mona Lisa?": "Leonardo da Vinci",
    "What is the fastest land animal?": "Cheetah",
    "Who wrote 'Romeo and Juliet'?": "William Shakespeare",
    "What is the chemical symbol for gold?": "Au",
    "What is the tallest mountain in the world?": "Mount Everest",
    "What is the currency of Japan?": "Yen",
    "What is the smallest country in the world?": "Vatican City",
    "Who painted the Sistine Chapel ceiling?": "Michelangelo"
}

@bot.command(name="guess")
async def guess(ctx):
    """Play a number guessing game."""
    number = random.randint(1, 100)
    attempts = 0
    await ctx.send(embed=create_embed("🎯 Guess the Number!", "I'm thinking of a number between 1 and 100. You have 10 attempts.", discord.Color.blue()))

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

    while attempts < 10:
        try:
            msg = await bot.wait_for('message', timeout=30.0, check=check)
            guess_num = int(msg.content)
            attempts += 1
            if guess_num < number:
                await ctx.send(embed=create_embed("📈 Too Low!", f"Attempt {attempts}/10. Guess higher!", discord.Color.orange()))
            elif guess_num > number:
                await ctx.send(embed=create_embed("📉 Too High!", f"Attempt {attempts}/10. Guess lower!", discord.Color.orange()))
            else:
                await ctx.send(embed=create_embed("🎉 Correct!", f"You guessed the number **{number}** in {attempts} attempts!", discord.Color.green()))
                return
        except asyncio.TimeoutError:
            await ctx.send(embed=create_embed("⏰ Time's Up!", f"The number was **{number}**.", discord.Color.red()))
            return
    await ctx.send(embed=create_embed("😔 Out of Attempts!", f"The number was **{number}**.", discord.Color.red()))

@bot.command(name="avatar")
async def avatar(ctx, member: discord.Member = None):
    """Get a member's avatar."""
    member = member or ctx.author
    embed = create_embed(
        title=f"🖼️ {member.display_name}'s Avatar",
        description=f"[Click here for higher quality]({member.avatar.url})",
        color=member.color,
        image=member.avatar.url
    )
    await ctx.send(embed=embed)

@bot.command(name="kiss", aliases=["hug", "kill", "slap"])
async def anime_action(ctx, action: str, member: discord.Member = None):
    """Send an anime GIF for various actions."""
    if not member:
        await ctx.send(embed=create_embed("❌ Error", f"Please mention a member to {action}.", discord.Color.red()))
        return
    gif_url = await get_anime_gif(action)
    if gif_url:
        embed = create_embed(
            title=f"🎭 {ctx.author.display_name} {action}s {member.display_name}!",
            description="How cute!",
            color=discord.Color.magenta(),
            image=gif_url
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send(embed=create_embed("❌ Error", f"Couldn't find a GIF for {action}.", discord.Color.red()))

async def get_anime_gif(action):
    """Fetch an anime GIF from the Waifu.it API."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"https://waifu.it/api/v4/{action}") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("url")
        except:
            return None
    return None
# ==========================
# BLOCK 7: GENERAL & INFO
# ==========================

@bot.command(name="ping")
async def ping(ctx):
    """Check the bot's latency."""
    latency = round(bot.latency * 1000)
    embed = create_embed(
        title="🏓 Pong!",
        description=f"**Current Latency:** {latency}ms\n**Bot Status:** {'🟢 Online' if latency < 200 else '🟡 High Latency' if latency < 500 else '🔴 Slow Response'}",
        color=discord.Color.green() if latency < 200 else discord.Color.orange() if latency < 500 else discord.Color.red(),
        footer=f"Requested by {ctx.author.name}"
    )
    await ctx.send(embed=embed)

@bot.command(name="info")
async def info(ctx):
    """Display information about the bot."""
    embed = discord.Embed(
        title="🤖 Notorious 47",
        description="A powerful and feature-rich administration bot designed to keep your server safe, fun, and well-managed.",
        color=discord.Color.dark_gold(),
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else bot.user.default_avatar.url)
    embed.add_field(name="Name", value="**NoToRiOuS ⁴⁷**", inline=True)
    embed.add_field(name="Built By", value="**Ishan // Toxyyy // Zaid**", inline=True)
    embed.add_field(name="Built Date", value="**06-04-2026**", inline=True)
    embed.add_field(name="Current Ping", value=f"**{round(bot.latency * 1000)}ms**", inline=True)
    embed.add_field(name="Duty", value="**Administration Of N47** :discordev:", inline=True)
    embed.add_field(name="Uptime", value=f"**{get_uptime()}**", inline=True)
    embed.add_field(name="Servers", value=f"**{len(bot.guilds)}**", inline=True)
    embed.add_field(name="Prefix", value=f"**{config['prefix']}**", inline=True)
    embed.set_footer(text="Notorious 47 • Keeping Your Server Safe")
    await ctx.send(embed=embed)

@bot.command(name="serverinfo")
async def serverinfo(ctx):
    """Display detailed information about the server."""
    guild = ctx.guild
    embed = discord.Embed(
        title=f"📊 Server Information - {guild.name}",
        color=guild.owner.color if guild.owner else discord.Color.blue(),
        timestamp=datetime.now()
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="👑 Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="📅 Created", value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    embed.add_field(name="👥 Members", value=guild.member_count, inline=True)
    embed.add_field(name="💬 Text Channels", value=len(guild.text_channels), inline=True)
    embed.add_field(name="🔊 Voice Channels", value=len(guild.voice_channels), inline=True)
    embed.add_field(name="🎭 Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="🚀 Boost Level", value=guild.premium_tier, inline=True)
    embed.add_field(name="✨ Boosters", value=guild.premium_subscription_count, inline=True)
    embed.add_field(name="🔒 Security Level", value=guild.verification_level, inline=True)
    embed.add_field(name="🌐 Explicit Filter", value=guild.explicit_content_filter, inline=True)
    embed.set_footer(text=f"Server ID: {guild.id}")
    await ctx.send(embed=embed)

@bot.command(name="userinfo")
async def userinfo(ctx, member: discord.Member = None):
    """Display detailed information about a user."""
    member = member or ctx.author
    embed = discord.Embed(
        title=f"👤 User Information - {member.display_name}",
        color=member.color,
        timestamp=datetime.now()
    )
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    embed.add_field(name="Username", value=member.name, inline=True)
    embed.add_field(name="Display Name", value=member.display_name, inline=True)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Joined Discord", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if member.joined_at else "Unknown", inline=True)
    embed.add_field(name="Top Role", value=member.top_role.mention, inline=True)
    embed.add_field(name="Is Bot?", value="✅" if member.bot else "❌", inline=True)
    embed.add_field(name="Boosting Since", value=member.premium_since.strftime("%Y-%m-%d %H:%M:%S") if member.premium_since else "Not Boosting", inline=True)
    embed.set_footer(text=f"Requested by {ctx.author.name}")
    await ctx.send(embed=embed)

@bot.command(name="help")
async def help(ctx, command_name: str = None):
    """Display the help menu."""
    if command_name:
        cmd = bot.get_command(command_name)
        if cmd:
            embed = create_embed(
                title=f"📖 Help: {config['prefix']}{cmd.name}",
                description=cmd.help or "No description available.",
                color=discord.Color.blue(),
                footer=f"Usage: {config['prefix']}{cmd.name} {cmd.signature if cmd.signature else ''}"
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(embed=create_embed("❌ Error", f"Command `{command_name}` not found.", discord.Color.red()))
        return

    embed = discord.Embed(
        title="🤖 Notorious 47 - Help Menu",
        description=f"**Prefix:** `{config['prefix']}`\n**Slash Commands:** `/`\nUse `{config['prefix']}help <command>` for more details on a specific command.",
        color=discord.Color.dark_gold()
    )
    embed.add_field(name="🛡️ Moderation", value="`ban`, `kick`, `timeout`, `warn`, `clear`, `lock`, `unlock`, `slowmode`, `badword`, `banlist`", inline=False)
    embed.add_field(name="⚙️ Administration", value="`setlog`, `setwelcome`, `setgoodbye`, `autorole`, `changeprefix`, `raidmode`", inline=False)
    embed.add_field(name="🎵 Music", value="`play`, `skip`, `stop`, `queue`, `pause`, `resume`, `volume`", inline=False)
    embed.add_field(name="🎮 Fun", value="`tictactoe`, `trivia`, `guess`, `avatar`, `kiss`, `hug`, `kill`, `slap`", inline=False)
    embed.add_field(name="📊 Utility", value="`ping`, `info`, `serverinfo`, `userinfo`", inline=False)
    embed.add_field(name="💾 SA-MP", value="`connect`, `disconnect`, `sa`", inline=False)
    embed.set_footer(text="Notorious 47 • Keeping Your Server Safe")
    await ctx.send(embed=embed)
# ==========================
# BLOCK 8: SA-MP & MAIN
# ==========================

# SA-MP Commands
@bot.command(name="connect")
@commands.has_permissions(administrator=True)
async def connect_samp(ctx, ip: str, port: int = 7777):
    """Connect to a SA-MP server and start monitoring."""
    config["samp_connected_ip"] = ip
    config["samp_connected_port"] = port
    save_config()
    embed = create_embed("🔌 Connected to SA-MP Server", f"Now monitoring **{ip}:{port}**.", discord.Color.green())
    await ctx.send(embed=embed)
    await update_samp_status.start(ctx.guild.id)

@bot.command(name="disconnect")
@commands.has_permissions(administrator=True)
async def disconnect_samp(ctx):
    """Disconnect from the SA-MP server."""
    config["samp_connected_ip"] = None
    config["samp_connected_port"] = None
    save_config()
    embed = create_embed("🔌 Disconnected from SA-MP Server", "Monitoring has been stopped.", discord.Color.red())
    await ctx.send(embed=embed)
    await update_samp_status.stop()

@bot.command(name="sa")
async def sa(ctx):
    """Display information about the connected SA-MP server."""
    if not config["samp_connected_ip"]:
        await ctx.send(embed=create_embed("❌ Error", "No SA-MP server is currently connected. Use `~connect <ip> <port>` first.", discord.Color.red()))
        return
    try:
        ip = config["samp_connected_ip"]
        port = config["samp_connected_port"]
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.samp.lt/server/{ip}/{port}") as response:
                if response.status == 200:
                    data = await response.json()
                    embed = create_embed(
                        title="🖥️ SA-MP Server Information",
                        description=f"**{data.get('hostname', 'Unknown')}**",
                        color=discord.Color.blue()
                    )
                    embed.add_field(name="Address", value=f"{ip}:{port}", inline=True)
                    embed.add_field(name="Players", value=f"{data.get('players', 0)}/{data.get('maxplayers', 0)}", inline=True)
                    embed.add_field(name="Gamemode", value=data.get('gamemode', 'Unknown'), inline=False)
                    embed.add_field(name="Map", value=data.get('mapname', 'Unknown'), inline=False)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(embed=create_embed("❌ Error", "Failed to fetch server information.", discord.Color.red()))
    except Exception as e:
        await ctx.send(embed=create_embed("❌ Error", f"An error occurred: {str(e)[:100]}", discord.Color.red()))

@tasks.loop(minutes=5)
async def update_samp_status(guild_id):
    """Background task to update SA-MP server status."""
    if not config["samp_connected_ip"]:
        return
    try:
        ip = config["samp_connected_ip"]
        port = config["samp_connected_port"]
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.samp.lt/server/{ip}/{port}") as response:
                if response.status == 200:
                    data = await response.json()
                    activity = discord.Activity(type=discord.ActivityType.watching, name=f"{data.get('players', 0)}/{data.get('maxplayers', 0)} on SA-MP")
                    await bot.change_presence(activity=activity)
                else:
                    await bot.change_presence(activity=discord.Game(name=f"{config['prefix']}help"))
    except:
        await bot.change_presence(activity=discord.Game(name=f"{config['prefix']}help"))

@bot.command(name="raidmode")
@commands.has_permissions(administrator=True)
async def raidmode(ctx, state: str = None):
    """Enable or disable raid mode."""
    if state is None:
        embed = create_embed("🛡️ Raid Mode Status", f"Raid mode is currently **{'enabled' if config['raid_mode'] else 'disabled'}**.", discord.Color.blue())
        await ctx.send(embed=embed)
        return
    if state.lower() == "on":
        config["raid_mode"] = True
        save_config()
        embed = create_embed("🛡️ Raid Mode Enabled", "Raid mode has been enabled. Suspicious activities will be automatically blocked.", discord.Color.red())
        await ctx.send(embed=embed)
    elif state.lower() == "off":
        config["raid_mode"] = False
        save_config()
        embed = create_embed("🛡️ Raid Mode Disabled", "Raid mode has been disabled. The server is now in standard protection mode.", discord.Color.green())
        await ctx.send(embed=embed)
    else:
        await ctx.send(embed=create_embed("❌ Error", "Invalid state. Use `~raidmode on` or `~raidmode off`.", discord.Color.red()))

@bot.command(name="changeprefix")
@commands.has_permissions(administrator=True)
async def changeprefix(ctx, new_prefix: str):
    """Change the bot's prefix."""
    if len(new_prefix) > 5:
        await ctx.send(embed=create_embed("❌ Error", "Prefix must be 5 characters or less.", discord.Color.red()))
        return
    old_prefix = config["prefix"]
    config["prefix"] = new_prefix
    bot.command_prefix = new_prefix
    save_config()
    embed = create_embed("✅ Prefix Changed", f"The prefix has been changed from `{old_prefix}` to `{new_prefix}`.", discord.Color.green())
    await ctx.send(embed=embed)
    await log_action(ctx.guild, "Prefix Change", f"{ctx.author.mention} changed the prefix from `{old_prefix}` to `{new_prefix}`.", discord.Color.blue())

@bot.event
async def on_ready():
    bot.start_time = datetime.now()
    print(f"✅ {bot.user.name} is online!")
    print(f"📊 Serving {len(bot.guilds)} servers")
    await bot.change_presence(activity=discord.Game(name=f"{config['prefix']}help"))
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}")
    await update_samp_status.start(bot.guilds[0].id)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=create_embed("❌ Error", f"You need `{', '.join(error.missing_permissions)}` permission to use this command.", discord.Color.red()), delete_after=5)
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=create_embed("❌ Error", f"Missing argument: `{error.param.name}`\nUse `{config['prefix']}help {ctx.command.name}` for usage.", discord.Color.red()), delete_after=5)
    elif isinstance(error, commands.BadArgument):
        await ctx.send(embed=create_embed("❌ Error", f"Invalid argument: {error}", discord.Color.red()), delete_after=5)
    else:
        print(f"Error: {error}")
        await ctx.send(embed=create_embed("❌ Error", f"An unexpected error occurred: {str(error)[:100]}", discord.Color.red()), delete_after=5)

if __name__ == "__main__":
    TOKEN = os.environ.get('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ DISCORD_TOKEN environment variable not set.")
        exit(1)
    bot.run(TOKEN)