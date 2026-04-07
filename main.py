import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
import re
import random
from datetime import datetime, timedelta
from flask import Flask
import threading
import yt_dlp as youtube_dl

# ========== CONFIG FILE MANAGEMENT ==========
if not os.path.exists("config.json"):
    with open("config.json", "w") as f:
        json.dump({
            "prefix": "$",
            "log_channel": None,
            "welcome_channel": None,
            "goodbye_channel": None,
            "autorole": None,
            "raidmode": False,
            "welcome_message": "🎉 Welcome {user} to {server}! You're member #{member_count}",
            "goodbye_message": "👋 {user} left the server! We now have {member_count} members",
            "bad_words": ["fuck", "shit", "asshole", "bitch", "cunt", "nigga", "nigger", "whore", "slut", "dick", "pussy", "cock", "bastard"]
        }, f, indent=4)

with open("config.json", "r") as f:
    config = json.load(f)

def save_config():
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

# ========== WARNINGS SYSTEM ==========
if not os.path.exists("warnings.json"):
    with open("warnings.json", "w") as f:
        json.dump({}, f)

with open("warnings.json", "r") as f:
    warnings = json.load(f)

def save_warnings():
    with open("warnings.json", "w") as f:
        json.dump(warnings, f, indent=4)

# ========== BOT SETUP ==========
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=config["prefix"], intents=intents, help_command=None)

# ========== WEB SERVER FOR UPTIMEROBOT ==========
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
print("✅ Web server started")

# ========== SPAM TRACKER ==========
spam_tracker = {}

# ========== MUSIC SETUP ==========
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
# ========== ADMIN COMMANDS ==========
@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_cmd(ctx, member: discord.Member, *, reason: str = "No reason"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 Banned {member.mention} | Reason: {reason}")

@bot.tree.command(name="ban", description="Ban a member")
@app_commands.describe(member="The member to ban", reason="Reason for ban")
async def ban_slash(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
        return
    await member.ban(reason=reason)
    await interaction.response.send_message(f"🔨 Banned {member.mention} | Reason: {reason}")

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick_cmd(ctx, member: discord.Member, *, reason: str = "No reason"):
    await member.kick(reason=reason)
    await ctx.send(f"👢 Kicked {member.mention} | Reason: {reason}")

@bot.tree.command(name="kick", description="Kick a member")
@app_commands.describe(member="The member to kick", reason="Reason for kick")
async def kick_slash(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
        return
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👢 Kicked {member.mention} | Reason: {reason}")

@bot.command(name="timeout")
@commands.has_permissions(moderate_members=True)
async def timeout_cmd(ctx, member: discord.Member, duration: str, *, reason: str = "No reason"):
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    unit = duration[-1]
    if unit not in units:
        await ctx.send("❌ Use: 30s, 5m, 2h, 1d")
        return
    try:
        amount = int(duration[:-1])
        seconds = amount * units[unit]
        if seconds > 2419200:
            await ctx.send("❌ Max 28 days!")
            return
    except:
        await ctx.send("❌ Invalid duration!")
        return
    until = datetime.now() + timedelta(seconds=seconds)
    await member.timeout(until, reason=reason)
    await ctx.send(f"🔇 {member.mention} timed out for {duration} | Reason: {reason}")

@bot.tree.command(name="timeout", description="Timeout a member")
@app_commands.describe(member="The member to timeout", duration="30s, 5m, 2h, 1d", reason="Reason for timeout")
async def timeout_slash(interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = "No reason"):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
        return
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    unit = duration[-1]
    if unit not in units:
        await interaction.response.send_message("❌ Use: 30s, 5m, 2h, 1d")
        return
    try:
        amount = int(duration[:-1])
        seconds = amount * units[unit]
        if seconds > 2419200:
            await interaction.response.send_message("❌ Max 28 days!")
            return
    except:
        await interaction.response.send_message("❌ Invalid duration!")
        return
    until = datetime.now() + timedelta(seconds=seconds)
    await member.timeout(until, reason=reason)
    await interaction.response.send_message(f"🔇 {member.mention} timed out for {duration} | Reason: {reason}")

@bot.command(name="warn")
@commands.has_permissions(kick_members=True)
async def warn_cmd(ctx, member: discord.Member, *, reason: str = "No reason"):
    key = str(member.id)
    if key not in warnings:
        warnings[key] = []
    warnings[key].append({"reason": reason, "mod": ctx.author.name, "time": datetime.now().isoformat()})
    save_warnings()
    if len(warnings[key]) >= 3:
        await member.ban(reason=f"Auto-ban - 3 warnings. Last: {reason}")
        await ctx.send(f"⚠️ {member.mention} auto-banned for 3 warnings!")
    else:
        await ctx.send(f"⚠️ {member.mention} warned ({len(warnings[key])}/3) | Reason: {reason}")

@bot.tree.command(name="warn", description="Warn a member (auto-ban at 3 warnings)")
@app_commands.describe(member="The member to warn", reason="Reason for warning")
async def warn_slash(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
        return
    key = str(member.id)
    if key not in warnings:
        warnings[key] = []
    warnings[key].append({"reason": reason, "mod": interaction.user.name, "time": datetime.now().isoformat()})
    save_warnings()
    if len(warnings[key]) >= 3:
        await member.ban(reason=f"Auto-ban - 3 warnings. Last: {reason}")
        await interaction.response.send_message(f"⚠️ {member.mention} auto-banned for 3 warnings!")
    else:
        await interaction.response.send_message(f"⚠️ {member.mention} warned ({len(warnings[key])}/3) | Reason: {reason}")

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear_cmd(ctx, amount: int = 5):
    if amount > 100:
        amount = 100
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🗑️ Deleted {len(deleted)-1} messages")
    await asyncio.sleep(3)
    await msg.delete()

@bot.tree.command(name="clear", description="Clear messages")
@app_commands.describe(amount="Number of messages to clear (max 100)")
async def clear_slash(interaction: discord.Interaction, amount: int = 5):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
        return
    if amount > 100:
        amount = 100
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"🗑️ Deleted {len(deleted)} messages", ephemeral=True)

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock_cmd(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(f"🔒 {channel.mention} locked")

@bot.tree.command(name="lock", description="Lock a channel")
@app_commands.describe(channel="Channel to lock (default: current)")
async def lock_slash(interaction: discord.Interaction, channel: discord.TextChannel = None):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
        return
    channel = channel or interaction.channel
    await channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message(f"🔒 {channel.mention} locked")

@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock_cmd(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(f"🔓 {channel.mention} unlocked")

@bot.tree.command(name="unlock", description="Unlock a channel")
@app_commands.describe(channel="Channel to unlock (default: current)")
async def unlock_slash(interaction: discord.Interaction, channel: discord.TextChannel = None):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
        return
    channel = channel or interaction.channel
    await channel.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message(f"🔓 {channel.mention} unlocked")

@bot.command(name="slowmode")
@commands.has_permissions(manage_channels=True)
async def slowmode_cmd(ctx, seconds: int = 0):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"⏱️ Slowmode set to {seconds} seconds")

@bot.tree.command(name="slowmode", description="Set slowmode in channel")
@app_commands.describe(seconds="Seconds between messages (0 to disable)")
async def slowmode_slash(interaction: discord.Interaction, seconds: int = 0):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
        return
    await interaction.channel.edit(slowmode_delay=seconds)
    await interaction.response.send_message(f"⏱️ Slowmode set to {seconds} seconds")
# ========== ROLE COMMANDS ==========
@bot.command(name="addrole")
@commands.has_permissions(manage_roles=True)
async def addrole_cmd(ctx, member: discord.Member, role: discord.Role):
    if role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        await ctx.send("❌ Cannot add role higher than your top role!")
        return
    await member.add_roles(role)
    await ctx.send(f"✅ Added {role.mention} to {member.mention}")

@bot.tree.command(name="addrole", description="Add a role to a member")
@app_commands.describe(member="The member", role="The role to add")
async def addrole_slash(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
        return
    if role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
        await interaction.response.send_message("❌ Cannot add role higher than your top role!")
        return
    await member.add_roles(role)
    await interaction.response.send_message(f"✅ Added {role.mention} to {member.mention}")

@bot.command(name="removerole")
@commands.has_permissions(manage_roles=True)
async def removerole_cmd(ctx, member: discord.Member, role: discord.Role):
    if role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        await ctx.send("❌ Cannot remove role higher than your top role!")
        return
    await member.remove_roles(role)
    await ctx.send(f"✅ Removed {role.mention} from {member.mention}")

@bot.tree.command(name="removerole", description="Remove a role from a member")
@app_commands.describe(member="The member", role="The role to remove")
async def removerole_slash(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
        return
    if role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
        await interaction.response.send_message("❌ Cannot remove role higher than your top role!")
        return
    await member.remove_roles(role)
    await interaction.response.send_message(f"✅ Removed {role.mention} from {member.mention}")

@bot.command(name="autorole")
@commands.has_permissions(administrator=True)
async def autorole_cmd(ctx, role: discord.Role = None):
    if role is None:
        config["autorole"] = None
        await ctx.send("✅ Auto-role disabled!")
    else:
        config["autorole"] = role.id
        await ctx.send(f"✅ Auto-role set to {role.mention}")
    save_config()

@bot.tree.command(name="autorole", description="Set auto-role for new members")
@app_commands.describe(role="Role to give new members (omit to disable)")
async def autorole_slash(interaction: discord.Interaction, role: discord.Role = None):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
        return
    if role is None:
        config["autorole"] = None
        await interaction.response.send_message("✅ Auto-role disabled!")
    else:
        config["autorole"] = role.id
        await interaction.response.send_message(f"✅ Auto-role set to {role.mention}")
    save_config()

# ========== AUTO-MODERATION ==========
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    bad_words = config.get("bad_words", [])
    msg_lower = message.content.lower()
    
    # Bad words filter
    for word in bad_words:
        if word in msg_lower:
            await message.delete()
            await message.channel.send(f"{message.author.mention} ❌ That word is not allowed!", delete_after=3)
            return
    
    # Discord invite filter
    invite_pattern = r"(discord\.gg/|discord\.com/invite/|dsc\.gg/|discordapp\.com/invite/)"
    if re.search(invite_pattern, message.content) and not message.author.guild_permissions.administrator:
        await message.delete()
        await message.channel.send(f"{message.author.mention} 🚫 No invite links!", delete_after=3)
        return
    
    # Mass mention filter
    if len(message.mentions) >= 4 and not message.author.guild_permissions.administrator:
        await message.delete()
        await message.channel.send(f"{message.author.mention} 🚫 Mass mentions not allowed!", delete_after=3)
        return
    
    # Spam filter
    key = f"{message.guild.id}_{message.author.id}"
    now = datetime.now()
    if key not in spam_tracker:
        spam_tracker[key] = []
    spam_tracker[key] = [t for t in spam_tracker[key] if (now - t).total_seconds() < 3]
    spam_tracker[key].append(now)
    if len(spam_tracker[key]) >= 5:
        await message.delete()
        await message.channel.send(f"{message.author.mention} 🚫 Stop spamming!", delete_after=3)
        spam_tracker[key] = []
        return
    
    # Caps filter
    if len(message.content) >= 10:
        caps = sum(1 for c in message.content if c.isupper())
        if (caps / len(message.content)) * 100 >= 70 and not message.author.guild_permissions.administrator:
            await message.delete()
            await message.channel.send(f"{message.author.mention} 🔠 Too many capitals!", delete_after=3)
            return
    
    await bot.process_commands(message)

# ========== BAD WORDS MANAGEMENT ==========
@bot.group(name="badword")
@commands.has_permissions(administrator=True)
async def badword(ctx):
    if ctx.invoked_subcommand is None:
        words = ", ".join(config.get("bad_words", []))
        embed = discord.Embed(title="🚫 Bad Words List", description=words or "No bad words set", color=discord.Color.red())
        await ctx.send(embed=embed)

@badword.command(name="add")
async def badword_add(ctx, word: str):
    word = word.lower()
    if word not in config["bad_words"]:
        config["bad_words"].append(word)
        save_config()
        await ctx.send(f"✅ Added `{word}`")
    else:
        await ctx.send(f"⚠️ `{word}` already in list")

@badword.command(name="remove")
async def badword_remove(ctx, word: str):
    word = word.lower()
    if word in config["bad_words"]:
        config["bad_words"].remove(word)
        save_config()
        await ctx.send(f"✅ Removed `{word}`")
    else:
        await ctx.send(f"❌ `{word}` not found")

# ========== WELCOME & GOODBYE ==========
@bot.command(name="setwelcome")
@commands.has_permissions(administrator=True)
async def setwelcome_msg(ctx, *, message: str = None):
    if message is None:
        await ctx.send(f"Current: {config['welcome_message']}")
        return
    config["welcome_message"] = message
    save_config()
    await ctx.send("✅ Welcome message updated!")

@bot.command(name="setwelcomechannel")
@commands.has_permissions(administrator=True)
async def setwelcome_channel(ctx, channel: discord.TextChannel = None):
    config["welcome_channel"] = channel.id if channel else None
    save_config()
    await ctx.send(f"✅ Welcome channel set to {channel.mention}" if channel else "✅ Welcome messages disabled")

@bot.command(name="setgoodbye")
@commands.has_permissions(administrator=True)
async def setgoodbye_msg(ctx, *, message: str = None):
    if message is None:
        await ctx.send(f"Current: {config['goodbye_message']}")
        return
    config["goodbye_message"] = message
    save_config()
    await ctx.send("✅ Goodbye message updated!")

@bot.command(name="setgoodbyechannel")
@commands.has_permissions(administrator=True)
async def setgoodbye_channel(ctx, channel: discord.TextChannel = None):
    config["goodbye_channel"] = channel.id if channel else None
    save_config()
    await ctx.send(f"✅ Goodbye channel set to {channel.mention}" if channel else "✅ Goodbye messages disabled")

@bot.event
async def on_member_join(member):
    channel_id = config.get("welcome_channel")
    if channel_id:
        channel = bot.get_channel(channel_id)
        if channel:
            msg = config["welcome_message"].replace("{user}", member.name).replace("{mention}", member.mention).replace("{server}", member.guild.name).replace("{member_count}", str(len(member.guild.members)))
            embed = discord.Embed(description=msg, color=discord.Color.green())
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            await channel.send(embed=embed)
    
    role_id = config.get("autorole")
    if role_id:
        role = member.guild.get_role(role_id)
        if role:
            await member.add_roles(role)

@bot.event
async def on_member_remove(member):
    channel_id = config.get("goodbye_channel")
    if channel_id:
        channel = bot.get_channel(channel_id)
        if channel:
            msg = config["goodbye_message"].replace("{user}", member.name).replace("{server}", member.guild.name).replace("{member_count}", str(len(member.guild.members)))
            await channel.send(msg)

@bot.command(name="setlog")
@commands.has_permissions(administrator=True)
async def setlog_cmd(ctx, channel: discord.TextChannel = None):
    config["log_channel"] = channel.id if channel else None
    save_config()
    await ctx.send(f"✅ Log channel set to {channel.mention}" if channel else "✅ Logging disabled")

@bot.command(name="changeprefix", aliases=["prefix"])
@commands.has_permissions(administrator=True)
async def changeprefix_cmd(ctx, new_prefix: str):
    if len(new_prefix) > 5:
        await ctx.send("❌ Prefix too long!")
        return
    config["prefix"] = new_prefix
    bot.command_prefix = new_prefix
    save_config()
    await ctx.send(f"✅ Prefix changed to `{new_prefix}`")
# ========== MUSIC SYSTEM ==========
async def play_song(ctx, song):
    voice = ctx.voice_client
    if not voice:
        return
    
    def after_playing(error):
        asyncio.run_coroutine_threadsafe(check_queue(ctx), bot.loop)
    
    try:
        source = await discord.FFmpegOpusAudio.from_probe(song['url'], **FFMPEG_OPTIONS)
        voice.play(source, after=after_playing)
        embed = discord.Embed(title="🎵 Now Playing", description=f"[{song['title']}]({song['webpage_url']})", color=discord.Color.green())
        embed.add_field(name="Requested by", value=song['requester'].mention)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Error playing: {str(e)[:100]}")

async def check_queue(ctx):
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        next_song = queues[ctx.guild.id].pop(0)
        await play_song(ctx, next_song)
    else:
        await asyncio.sleep(300)
        if ctx.voice_client and not ctx.voice_client.is_playing():
            await ctx.voice_client.disconnect()

@bot.command(name="play", aliases=["p"])
async def play_cmd(ctx, *, query: str):
    if not ctx.author.voice:
        await ctx.send("❌ Join a voice channel first!")
        return
    
    voice_channel = ctx.author.voice.channel
    voice = ctx.voice_client
    
    if not voice:
        await voice_channel.connect()
        voice = ctx.voice_client
    elif voice.channel != voice_channel:
        await voice.move_to(voice_channel)
    
    searching = await ctx.send(f"🔍 Searching: `{query}`...")
    
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        
        if data is None:
            await searching.edit(content="❌ No results found!")
            return
        
        if 'entries' in data:
            data = data['entries'][0]
        
        song = {
            'url': data['url'],
            'title': data['title'],
            'webpage_url': data['webpage_url'],
            'requester': ctx.author
        }
        
        await searching.delete()
        
        if voice.is_playing() or voice.is_paused():
            if ctx.guild.id not in queues:
                queues[ctx.guild.id] = []
            queues[ctx.guild.id].append(song)
            embed = discord.Embed(title="📋 Added to Queue", description=f"[{song['title']}]({song['webpage_url']})", color=discord.Color.blue())
            embed.add_field(name="Position", value=f"#{len(queues[ctx.guild.id])}")
            await ctx.send(embed=embed)
        else:
            await play_song(ctx, song)
    except Exception as e:
        await searching.edit(content=f"❌ Error: {str(e)[:100]}")

@bot.tree.command(name="play", description="Play a song from YouTube")
@app_commands.describe(query="Song name or YouTube URL")
async def play_slash(interaction: discord.Interaction, query: str):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ Join a voice channel first!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    voice_channel = interaction.user.voice.channel
    voice = interaction.guild.voice_client
    
    if not voice:
        await voice_channel.connect()
        voice = interaction.guild.voice_client
    elif voice.channel != voice_channel:
        await voice.move_to(voice_channel)
    
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        
        if data is None:
            await interaction.followup.send("❌ No results found!")
            return
        
        if 'entries' in data:
            data = data['entries'][0]
        
        song = {
            'url': data['url'],
            'title': data['title'],
            'webpage_url': data['webpage_url'],
            'requester': interaction.user
        }
        
        if voice.is_playing() or voice.is_paused():
            if interaction.guild.id not in queues:
                queues[interaction.guild.id] = []
            queues[interaction.guild.id].append(song)
            embed = discord.Embed(title="📋 Added to Queue", description=f"[{song['title']}]({song['webpage_url']})", color=discord.Color.blue())
            embed.add_field(name="Position", value=f"#{len(queues[interaction.guild.id])}")
            await interaction.followup.send(embed=embed)
        else:
            await play_song(interaction, song)
            await interaction.followup.send("🎵 Playing...")
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)[:100]}")

async def play_song(ctx_or_interaction, song):
    if isinstance(ctx_or_interaction, discord.Interaction):
        ctx = await bot.get_context(ctx_or_interaction)
        voice = ctx.guild.voice_client
    else:
        ctx = ctx_or_interaction
        voice = ctx.voice_client
    
    if not voice:
        return
    
    def after_playing(error):
        asyncio.run_coroutine_threadsafe(check_queue(ctx), bot.loop)
    
    try:
        source = await discord.FFmpegOpusAudio.from_probe(song['url'], **FFMPEG_OPTIONS)
        voice.play(source, after=after_playing)
        embed = discord.Embed(title="🎵 Now Playing", description=f"[{song['title']}]({song['webpage_url']})", color=discord.Color.green())
        embed.add_field(name="Requested by", value=song['requester'].mention)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)[:100]}")

@bot.command(name="skip", aliases=["s"])
async def skip_cmd(ctx):
    voice = ctx.voice_client
    if not voice or not voice.is_playing():
        await ctx.send("❌ Nothing playing!")
        return
    voice.stop()
    await ctx.send("⏭️ Skipped")

@bot.tree.command(name="skip", description="Skip the current song")
async def skip_slash(interaction: discord.Interaction):
    voice = interaction.guild.voice_client
    if not voice or not voice.is_playing():
        await interaction.response.send_message("❌ Nothing playing!", ephemeral=True)
        return
    voice.stop()
    await interaction.response.send_message("⏭️ Skipped")

@bot.command(name="stop", aliases=["leave", "dc"])
async def stop_cmd(ctx):
    voice = ctx.voice_client
    if voice:
        if ctx.guild.id in queues:
            queues[ctx.guild.id] = []
        voice.stop()
        await voice.disconnect()
        await ctx.send("⏹️ Stopped and left")

@bot.tree.command(name="stop", description="Stop music and clear queue")
async def stop_slash(interaction: discord.Interaction):
    voice = interaction.guild.voice_client
    if voice:
        if interaction.guild.id in queues:
            queues[interaction.guild.id] = []
        voice.stop()
        await voice.disconnect()
        await interaction.response.send_message("⏹️ Stopped and left")

@bot.command(name="pause")
async def pause_cmd(ctx):
    voice = ctx.voice_client
    if voice and voice.is_playing():
        voice.pause()
        await ctx.send("⏸️ Paused")
    else:
        await ctx.send("❌ Nothing playing!")

@bot.tree.command(name="pause", description="Pause the current song")
async def pause_slash(interaction: discord.Interaction):
    voice = interaction.guild.voice_client
    if voice and voice.is_playing():
        voice.pause()
        await interaction.response.send_message("⏸️ Paused")
    else:
        await interaction.response.send_message("❌ Nothing playing!", ephemeral=True)

@bot.command(name="resume")
async def resume_cmd(ctx):
    voice = ctx.voice_client
    if voice and voice.is_paused():
        voice.resume()
        await ctx.send("▶️ Resumed")
    else:
        await ctx.send("❌ Nothing paused!")

@bot.tree.command(name="resume", description="Resume the paused song")
async def resume_slash(interaction: discord.Interaction):
    voice = interaction.guild.voice_client
    if voice and voice.is_paused():
        voice.resume()
        await interaction.response.send_message("▶️ Resumed")
    else:
        await interaction.response.send_message("❌ Nothing paused!", ephemeral=True)

@bot.command(name="queue", aliases=["q"])
async def queue_cmd(ctx):
    if ctx.guild.id not in queues or not queues[ctx.guild.id]:
        await ctx.send("📭 Queue is empty!")
        return
    
    embed = discord.Embed(title="📋 Music Queue", color=discord.Color.blue())
    for i, song in enumerate(queues[ctx.guild.id][:10]):
        embed.add_field(name=f"{i+1}. {song['title'][:50]}", value=f"Requested by {song['requester'].mention}", inline=False)
    if len(queues[ctx.guild.id]) > 10:
        embed.set_footer(text=f"And {len(queues[ctx.guild.id])-10} more...")
    await ctx.send(embed=embed)

@bot.tree.command(name="queue", description="Show the music queue")
async def queue_slash(interaction: discord.Interaction):
    if interaction.guild.id not in queues or not queues[interaction.guild.id]:
        await interaction.response.send_message("📭 Queue is empty!")
        return
    
    embed = discord.Embed(title="📋 Music Queue", color=discord.Color.blue())
    for i, song in enumerate(queues[interaction.guild.id][:10]):
        embed.add_field(name=f"{i+1}. {song['title'][:50]}", value=f"Requested by {song['requester'].mention}", inline=False)
    if len(queues[interaction.guild.id]) > 10:
        embed.set_footer(text=f"And {len(queues[interaction.guild.id])-10} more...")
    await interaction.response.send_message(embed=embed)

@bot.command(name="nowplaying", aliases=["np"])
async def nowplaying_cmd(ctx):
    voice = ctx.voice_client
    if not voice or not voice.is_playing():
        await ctx.send("❌ Nothing playing!")
        return
    await ctx.send("🎵 Music is playing! Use `$queue` to see upcoming songs.")

@bot.tree.command(name="nowplaying", description="Show current playing song")
async def nowplaying_slash(interaction: discord.Interaction):
    voice = interaction.guild.voice_client
    if not voice or not voice.is_playing():
        await interaction.response.send_message("❌ Nothing playing!", ephemeral=True)
        return
    await interaction.response.send_message("🎵 Music is playing!")
# ========== GAMES ==========
@bot.command(name="roll")
async def roll_cmd(ctx, sides: int = 6):
    if sides < 1:
        sides = 1
    if sides > 100:
        sides = 100
    result = random.randint(1, sides)
    await ctx.send(f"🎲 {ctx.author.mention} rolled **{result}** (1-{sides})")

@bot.tree.command(name="roll", description="Roll a dice")
@app_commands.describe(sides="Number of sides (default: 6)")
async def roll_slash(interaction: discord.Interaction, sides: int = 6):
    if sides < 1:
        sides = 1
    if sides > 100:
        sides = 100
    result = random.randint(1, sides)
    await interaction.response.send_message(f"🎲 {interaction.user.mention} rolled **{result}** (1-{sides})")

@bot.command(name="8ball")
async def eightball_cmd(ctx, *, question: str):
    responses = ["Yes", "No", "Maybe", "Definitely", "Ask later", "No way", "Absolutely!", "Never", "Probably", "I doubt it"]
    await ctx.send(f"🎱 {random.choice(responses)}")

@bot.tree.command(name="8ball", description="Ask the magic 8-ball")
@app_commands.describe(question="Your question")
async def eightball_slash(interaction: discord.Interaction, question: str):
    responses = ["Yes", "No", "Maybe", "Definitely", "Ask later", "No way", "Absolutely!", "Never", "Probably", "I doubt it"]
    await interaction.response.send_message(f"🎱 {random.choice(responses)}")

@bot.command(name="rps")
async def rps_cmd(ctx, choice: str):
    choices = ["rock", "paper", "scissors"]
    bot_choice = random.choice(choices)
    player_choice = choice.lower()
    
    if player_choice not in choices:
        await ctx.send("❌ Choose: rock, paper, or scissors")
        return
    
    if player_choice == bot_choice:
        result = "Tie! 🤝"
    elif (player_choice == "rock" and bot_choice == "scissors") or \
         (player_choice == "paper" and bot_choice == "rock") or \
         (player_choice == "scissors" and bot_choice == "paper"):
        result = "You win! 🎉"
    else:
        result = "I win! 😎"
    
    await ctx.send(f"✊ You: {player_choice} | Bot: {bot_choice}\n{result}")

@bot.tree.command(name="rps", description="Play Rock Paper Scissors")
@app_commands.describe(choice="Your choice")
async def rps_slash(interaction: discord.Interaction, choice: str):
    choices = ["rock", "paper", "scissors"]
    bot_choice = random.choice(choices)
    player_choice = choice.lower()
    
    if player_choice not in choices:
        await interaction.response.send_message("❌ Choose: rock, paper, or scissors", ephemeral=True)
        return
    
    if player_choice == bot_choice:
        result = "Tie! 🤝"
    elif (player_choice == "rock" and bot_choice == "scissors") or \
         (player_choice == "paper" and bot_choice == "rock") or \
         (player_choice == "scissors" and bot_choice == "paper"):
        result = "You win! 🎉"
    else:
        result = "I win! 😎"
    
    await interaction.response.send_message(f"✊ You: {player_choice} | Bot: {bot_choice}\n{result}")

@bot.command(name="guess")
async def guess_cmd(ctx):
    number = random.randint(1, 100)
    attempts = 0
    
    await ctx.send("🎯 Guess a number between 1-100! You have 10 attempts.")
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
    
    while attempts < 10:
        try:
            msg = await bot.wait_for('message', timeout=30.0, check=check)
            guess = int(msg.content)
            attempts += 1
            
            if guess < number:
                await ctx.send(f"📈 Too low! ({10-attempts} left)")
            elif guess > number:
                await ctx.send(f"📉 Too high! ({10-attempts} left)")
            else:
                await ctx.send(f"🎉 Correct! Guessed in {attempts} attempts!")
                return
        except asyncio.TimeoutError:
            await ctx.send(f"⏰ Time's up! Number was {number}")
            return
    
    await ctx.send(f"😔 Out of attempts! Number was {number}")

@bot.tree.command(name="guess", description="Guess a number between 1-100")
async def guess_slash(interaction: discord.Interaction):
    await interaction.response.send_message("🎯 Use `$guess` to play - slash version coming soon!", ephemeral=True)

@bot.command(name="trivia")
async def trivia_cmd(ctx):
    questions = {
        "What is the capital of France?": "Paris",
        "What is 2+2?": "4",
        "Who painted the Mona Lisa?": "Leonardo da Vinci",
        "What is the largest ocean?": "Pacific Ocean",
        "Who wrote Romeo and Juliet?": "William Shakespeare",
        "What is the fastest land animal?": "Cheetah",
        "What is the chemical symbol for gold?": "Au",
        "What is the tallest mountain?": "Mount Everest"
    }
    question, answer = random.choice(list(questions.items()))
    
    await ctx.send(f"📚 **Trivia!**\n{question}\n\nYou have 20 seconds!")
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    
    try:
        msg = await bot.wait_for('message', timeout=20.0, check=check)
        if msg.content.lower().strip() == answer.lower():
            await ctx.send(f"✅ Correct! Answer: {answer}")
        else:
            await ctx.send(f"❌ Wrong! Answer: {answer}")
    except asyncio.TimeoutError:
        await ctx.send(f"⏰ Time's up! Answer: {answer}")

@bot.command(name="coinflip", aliases=["flip"])
async def coinflip_cmd(ctx):
    result = random.choice(["Heads", "Tails"])
    await ctx.send(f"🪙 Coin landed on: **{result}**")

@bot.tree.command(name="coinflip", description="Flip a coin")
async def coinflip_slash(interaction: discord.Interaction):
    result = random.choice(["Heads", "Tails"])
    await interaction.response.send_message(f"🪙 Coin landed on: **{result}**")

@bot.command(name="slots")
async def slots_cmd(ctx):
    emojis = ["🍒", "🍊", "🍋", "🍉", "⭐", "💎", "7️⃣"]
    slot1 = random.choice(emojis)
    slot2 = random.choice(emojis)
    slot3 = random.choice(emojis)
    
    if slot1 == slot2 == slot3:
        result = "🎉 JACKPOT! You win! 🎉"
    elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
        result = "✨ You got a pair! ✨"
    else:
        result = "😔 Better luck next time!"
    
    await ctx.send(f"🎰 | {slot1} | {slot2} | {slot3} |\n{result}")

@bot.tree.command(name="slots", description="Play slot machine")
async def slots_slash(interaction: discord.Interaction):
    emojis = ["🍒", "🍊", "🍋", "🍉", "⭐", "💎", "7️⃣"]
    slot1 = random.choice(emojis)
    slot2 = random.choice(emojis)
    slot3 = random.choice(emojis)
    
    if slot1 == slot2 == slot3:
        result = "🎉 JACKPOT! You win! 🎉"
    elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
        result = "✨ You got a pair! ✨"
    else:
        result = "😔 Better luck next time!"
    
    await interaction.response.send_message(f"🎰 | {slot1} | {slot2} | {slot3} |\n{result}")
# ========== UTILITY COMMANDS ==========
@bot.command(name="ping")
async def ping_cmd(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: **{latency}ms**")

@bot.tree.command(name="ping", description="Check bot latency")
async def ping_slash(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latency: **{latency}ms**")

@bot.command(name="serverinfo")
async def serverinfo_cmd(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"📊 {guild.name}", color=discord.Color.blue(), timestamp=datetime.now())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="👑 Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="👥 Members", value=guild.member_count, inline=True)
    embed.add_field(name="💬 Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="🎭 Roles", value=len(guild.roles), inline=True)
    await ctx.send(embed=embed)

@bot.tree.command(name="serverinfo", description="Get server information")
async def serverinfo_slash(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"📊 {guild.name}", color=discord.Color.blue(), timestamp=datetime.now())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="👑 Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="👥 Members", value=guild.member_count, inline=True)
    embed.add_field(name="💬 Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="🎭 Roles", value=len(guild.roles), inline=True)
    await interaction.response.send_message(embed=embed)

@bot.command(name="userinfo")
async def userinfo_cmd(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"👤 {member.name}", color=member.color, timestamp=datetime.now())
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "Unknown", inline=True)
    embed.add_field(name="Joined Discord", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Bot?", value="✅" if member.bot else "❌", inline=True)
    await ctx.send(embed=embed)

@bot.tree.command(name="userinfo", description="Get user information")
@app_commands.describe(member="The user to get info about")
async def userinfo_slash(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    embed = discord.Embed(title=f"👤 {member.name}", color=member.color, timestamp=datetime.now())
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "Unknown", inline=True)
    embed.add_field(name="Joined Discord", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Bot?", value="✅" if member.bot else "❌", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.command(name="avatar")
async def avatar_cmd(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"🖼️ {member.name}'s Avatar", color=discord.Color.blue())
    embed.set_image(url=member.avatar.url if member.avatar else member.default_avatar.url)
    await ctx.send(embed=embed)

@bot.tree.command(name="avatar", description="Get user avatar")
@app_commands.describe(member="The user to get avatar of")
async def avatar_slash(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    embed = discord.Embed(title=f"🖼️ {member.name}'s Avatar", color=discord.Color.blue())
    embed.set_image(url=member.avatar.url if member.avatar else member.default_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup_cmd(ctx):
    embed = discord.Embed(title="🔧 Notorious 47 - Setup Guide", color=discord.Color.green())
    embed.add_field(name="1️⃣ Bad Words", value="`$badword add <word>`\n`$badword remove <word>`", inline=False)
    embed.add_field(name="2️⃣ Welcome Message", value="`$setwelcome Welcome {mention}!`\n`$setwelcomechannel #channel`", inline=False)
    embed.add_field(name="3️⃣ Goodbye Message", value="`$setgoodbye {user} left!`\n`$setgoodbyechannel #channel`", inline=False)
    embed.add_field(name="4️⃣ Prefix", value="`$changeprefix !`", inline=False)
    embed.add_field(name="5️⃣ Log Channel", value="`$setlog #channel`", inline=False)
    embed.add_field(name="6️⃣ Auto Role", value="`$autorole @role`", inline=False)
    await ctx.send(embed=embed)

@bot.tree.command(name="setup", description="Show setup guide")
async def setup_slash(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    embed = discord.Embed(title="🔧 Notorious 47 - Setup Guide", color=discord.Color.green())
    embed.add_field(name="1️⃣ Bad Words", value="`/badword add <word>`\n`/badword remove <word>`", inline=False)
    embed.add_field(name="2️⃣ Welcome Message", value="`/setwelcome message`\n`/setwelcomechannel #channel`", inline=False)
    embed.add_field(name="3️⃣ Goodbye Message", value="`/setgoodbye message`\n`/setgoodbyechannel #channel`", inline=False)
    embed.add_field(name="4️⃣ Prefix", value="`/changeprefix !`", inline=False)
    embed.add_field(name="5️⃣ Log Channel", value="`/setlog #channel`", inline=False)
    embed.add_field(name="6️⃣ Auto Role", value="`/autorole @role`", inline=False)
    await interaction.response.send_message(embed=embed)

# ========== HELP COMMAND ==========
@bot.command(name="help")
async def help_cmd(ctx, command_name: str = None):
    if command_name:
        cmd = bot.get_command(command_name)
        if cmd:
            embed = discord.Embed(title=f"📖 {config['prefix']}{cmd.name}", color=discord.Color.blue())
            embed.add_field(name="Description", value=cmd.help or "No description", inline=False)
            await ctx.send(embed=embed)
            return
    
    embed = discord.Embed(title="🤖 Notorious 47", description=f"Prefix: `{config['prefix']}` | Slash: `/`", color=discord.Color.gold())
    embed.add_field(name="🛡️ Moderation", value="`ban`, `kick`, `timeout`, `warn`, `clear`, `lock`, `unlock`, `slowmode`", inline=False)
    embed.add_field(name="⚙️ Admin", value="`badword`, `setwelcome`, `setgoodbye`, `changeprefix`, `setlog`, `autorole`, `setup`", inline=False)
    embed.add_field(name="🎵 Music", value="`play`, `skip`, `stop`, `queue`, `pause`, `resume`, `nowplaying`", inline=False)
    embed.add_field(name="👥 Roles", value="`addrole`, `removerole`", inline=False)
    embed.add_field(name="🎮 Games", value="`roll`, `8ball`, `rps`, `guess`, `trivia`, `coinflip`, `slots`", inline=False)
    embed.add_field(name="📊 Utility", value="`ping`, `serverinfo`, `userinfo`, `avatar`", inline=False)
    embed.set_footer(text="Notorious 47 - Full Admin Bot")
    await ctx.send(embed=embed)

@bot.tree.command(name="help", description="Show help menu")
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 Notorious 47", description="Use `/` for slash commands or `$` for prefix commands", color=discord.Color.gold())
    embed.add_field(name="🛡️ Moderation", value="`ban`, `kick`, `timeout`, `warn`, `clear`, `lock`, `unlock`, `slowmode`", inline=False)
    embed.add_field(name="⚙️ Admin", value="`badword`, `setwelcome`, `setgoodbye`, `changeprefix`, `setlog`, `autorole`", inline=False)
    embed.add_field(name="🎵 Music", value="`play`, `skip`, `stop`, `queue`, `pause`, `resume`", inline=False)
    embed.add_field(name="🎮 Games", value="`roll`, `8ball`, `rps`, `coinflip`, `slots`", inline=False)
    await interaction.response.send_message(embed=embed)

# ========== ON READY ==========
@bot.event
async def on_ready():
    print(f"✅ {bot.user.name} is online!")
    print(f"📊 Serving {len(bot.guilds)} servers")
    
    await bot.change_presence(activity=discord.Game(name=f"{config['prefix']}help | /help"))
    
    # Sync slash commands
    try:
        await bot.tree.sync()
        print(f"✅ Slash commands synced!")
    except Exception as e:
        print(f"❌ Slash sync failed: {e}")

# ========== ERROR HANDLER ==========
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"❌ You need `{', '.join(error.missing_permissions)}` permission!", delete_after=5)
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument: `{error.param.name}`\nUse `{config['prefix']}help {ctx.command.name}`", delete_after=5)
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument: {error}", delete_after=5)
    else:
        print(f"Error: {error}")

# ========== RUN BOT ==========
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    print("❌ BOT_TOKEN not found in environment variables!")
    print("Add it in Render: Environment Variables → BOT_TOKEN")
else:
    bot.run(TOKEN)
