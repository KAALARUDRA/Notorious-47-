import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
import re
from datetime import datetime, timedelta
import random
from flask import Flask
import threading

# ========== LOAD CONFIG ==========
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

# ========== BOT SETUP ==========
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=config["prefix"], intents=intents, help_command=None)

def save_config():
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

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

# Start web server in background thread
threading.Thread(target=run_web_server, daemon=True).start()
print("✅ Web server started on port " + os.environ.get('PORT', '10000'))

# ========== BAD WORDS MANAGEMENT ==========
@bot.group(name="badword")
@commands.has_permissions(administrator=True)
async def badword(ctx):
    """Manage bad words filter"""
    if ctx.invoked_subcommand is None:
        words = ", ".join(config.get("bad_words", []))
        embed = discord.Embed(title="🚫 Bad Words List", description=words or "No bad words set", color=discord.Color.red())
        embed.set_footer(text="Use: $badword add <word> | $badword remove <word>")
        await ctx.send(embed=embed)

@badword.command(name="add")
async def badword_add(ctx, word: str):
    """Add a bad word to filter"""
    word = word.lower()
    if "bad_words" not in config:
        config["bad_words"] = []
    if word not in config["bad_words"]:
        config["bad_words"].append(word)
        save_config()
        await ctx.send(f"✅ Added `{word}` to bad words list!")
    else:
        await ctx.send(f"⚠️ `{word}` already in list!")

@badword.command(name="remove")
async def badword_remove(ctx, word: str):
    """Remove a bad word from filter"""
    word = word.lower()
    if "bad_words" in config and word in config["bad_words"]:
        config["bad_words"].remove(word)
        save_config()
        await ctx.send(f"✅ Removed `{word}` from bad words list!")
    else:
        await ctx.send(f"❌ `{word}` not found in list!")

# ========== WELCOME & GOODBYE MANAGEMENT ==========
@bot.command(name="setwelcome")
@commands.has_permissions(administrator=True)
async def set_welcome_message(ctx, *, message: str = None):
    """Set custom welcome message"""
    if message is None:
        embed = discord.Embed(title="📝 Current Welcome Message", description=config.get("welcome_message", "Not set"), color=discord.Color.blue())
        embed.add_field(name="Variables", value="`{user}` - Username\n`{mention}` - Mention user\n`{server}` - Server name\n`{member_count}` - Member count", inline=False)
        await ctx.send(embed=embed)
        return
    config["welcome_message"] = message
    save_config()
    await ctx.send(f"✅ Welcome message updated!")

@bot.command(name="setwelcomechannel")
@commands.has_permissions(administrator=True)
async def set_welcome_channel(ctx, channel: discord.TextChannel = None):
    """Set channel for welcome messages"""
    if channel is None:
        config["welcome_channel"] = None
        await ctx.send("✅ Welcome messages disabled!")
    else:
        config["welcome_channel"] = channel.id
        await ctx.send(f"✅ Welcome channel set to {channel.mention}")
    save_config()

@bot.command(name="setgoodbye")
@commands.has_permissions(administrator=True)
async def set_goodbye_message(ctx, *, message: str = None):
    """Set custom goodbye message"""
    if message is None:
        embed = discord.Embed(title="📝 Current Goodbye Message", description=config.get("goodbye_message", "Not set"), color=discord.Color.blue())
        await ctx.send(embed=embed)
        return
    config["goodbye_message"] = message
    save_config()
    await ctx.send(f"✅ Goodbye message updated!")

@bot.command(name="setgoodbyechannel")
@commands.has_permissions(administrator=True)
async def set_goodbye_channel(ctx, channel: discord.TextChannel = None):
    """Set channel for goodbye messages"""
    if channel is None:
        config["goodbye_channel"] = None
        await ctx.send("✅ Goodbye messages disabled!")
    else:
        config["goodbye_channel"] = channel.id
        await ctx.send(f"✅ Goodbye channel set to {channel.mention}")
    save_config()

@bot.command(name="setlog")
@commands.has_permissions(administrator=True)
async def setlog(ctx, channel: discord.TextChannel = None):
    """Set the logging channel"""
    if channel is None:
        config["log_channel"] = None
        await ctx.send("✅ Logging disabled!")
    else:
        config["log_channel"] = channel.id
        await ctx.send(f"✅ Log channel set to {channel.mention}")
    save_config()

@bot.command(name="autorole")
@commands.has_permissions(administrator=True)
async def autorole(ctx, role: discord.Role = None):
    """Set auto-role for new members"""
    if role is None:
        config["autorole"] = None
        await ctx.send("✅ Auto-role disabled!")
    else:
        config["autorole"] = role.id
        await ctx.send(f"✅ Auto-role set to {role.mention}")
    save_config()

@bot.command(name="changeprefix", aliases=["prefix"])
@commands.has_permissions(administrator=True)
async def changeprefix(ctx, new_prefix: str):
    """Change bot prefix"""
    if len(new_prefix) > 5:
        await ctx.send("❌ Prefix too long! Max 5 characters.")
        return
    config["prefix"] = new_prefix
    bot.command_prefix = new_prefix
    save_config()
    await ctx.send(f"✅ Prefix changed to `{new_prefix}`")

# ========== AUTO-MOD WITH DYNAMIC BAD WORDS ==========
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    bad_words = config.get("bad_words", [])
    msg_lower = message.content.lower()
    for word in bad_words:
        if word in msg_lower:
            await message.delete()
            await message.channel.send(f"{message.author.mention} ❌ That word is not allowed!", delete_after=3)
            return
    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    welcome_channel_id = config.get("welcome_channel")
    if welcome_channel_id:
        channel = bot.get_channel(welcome_channel_id)
        if channel:
            msg_template = config.get("welcome_message", "🎉 Welcome {mention} to {server}!")
            msg = msg_template.replace("{user}", member.name).replace("{mention}", member.mention).replace("{server}", member.guild.name).replace("{member_count}", str(len(member.guild.members)))
            embed = discord.Embed(description=msg, color=discord.Color.green())
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            await channel.send(embed=embed)
    autorole_id = config.get("autorole")
    if autorole_id:
        role = member.guild.get_role(autorole_id)
        if role:
            await member.add_roles(role)

@bot.event
async def on_member_remove(member):
    goodbye_channel_id = config.get("goodbye_channel")
    if goodbye_channel_id:
        channel = bot.get_channel(goodbye_channel_id)
        if channel:
            msg_template = config.get("goodbye_message", "👋 {user} left the server!")
            msg = msg_template.replace("{user}", member.name).replace("{server}", member.guild.name).replace("{member_count}", str(len(member.guild.members)))
            await channel.send(msg)

# ========== UTILITY COMMANDS ==========
@bot.command(name="ping")
async def ping(ctx):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: **{latency}ms**")

@bot.command(name="serverinfo")
async def serverinfo(ctx):
    """Get server information"""
    guild = ctx.guild
    embed = discord.Embed(title=f"📊 {guild.name}", color=discord.Color.blue(), timestamp=datetime.now())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="👑 Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="👥 Members", value=guild.member_count, inline=True)
    embed.add_field(name="💬 Channels", value=len(guild.channels), inline=True)
    await ctx.send(embed=embed)

@bot.command(name="userinfo")
async def userinfo(ctx, member: discord.Member = None):
    """Get user information"""
    member = member or ctx.author
    embed = discord.Embed(title=f"👤 {member.name}", color=member.color, timestamp=datetime.now())
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "Unknown", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="avatar")
async def avatar(ctx, member: discord.Member = None):
    """Get user avatar"""
    member = member or ctx.author
    embed = discord.Embed(title=f"🖼️ {member.name}'s Avatar", color=discord.Color.blue())
    embed.set_image(url=member.avatar.url if member.avatar else member.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup_guide(ctx):
    """Show setup guide"""
    embed = discord.Embed(title="🔧 Notorious 47 - Setup Guide", color=discord.Color.green())
    embed.add_field(name="1️⃣ Bad Words", value="`$badword add <word>`\n`$badword remove <word>`", inline=False)
    embed.add_field(name="2️⃣ Welcome Message", value="`$setwelcome Welcome {mention}!`\n`$setwelcomechannel #channel`", inline=False)
    embed.add_field(name="3️⃣ Goodbye Message", value="`$setgoodbye {user} left!`\n`$setgoodbyechannel #channel`", inline=False)
    embed.add_field(name="4️⃣ Prefix", value="`$changeprefix !`", inline=False)
    embed.add_field(name="5️⃣ Log Channel", value="`$setlog #channel`", inline=False)
    embed.add_field(name="6️⃣ Auto Role", value="`$autorole @role`", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_cmd(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Ban a member"""
    await member.ban(reason=reason)
    await ctx.send(f"🔨 Banned {member.mention} | Reason: {reason}")

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick_cmd(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Kick a member"""
    await member.kick(reason=reason)
    await ctx.send(f"👢 Kicked {member.mention} | Reason: {reason}")

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear_cmd(ctx, amount: int = 5):
    """Clear messages (max 100)"""
    if amount > 100:
        amount = 100
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🗑️ Deleted {len(deleted)-1} messages")
    await asyncio.sleep(3)
    await msg.delete()

@bot.command(name="addrole")
@commands.has_permissions(manage_roles=True)
async def addrole_cmd(ctx, member: discord.Member, role: discord.Role):
    """Add a role to a member"""
    await member.add_roles(role)
    await ctx.send(f"✅ Added {role.mention} to {member.mention}")

@bot.command(name="removerole")
@commands.has_permissions(manage_roles=True)
async def removerole_cmd(ctx, member: discord.Member, role: discord.Role):
    """Remove a role from a member"""
    await member.remove_roles(role)
    await ctx.send(f"✅ Removed {role.mention} from {member.mention}")

# ========== GAMES ==========
@bot.command(name="roll")
async def roll(ctx, dice: int = 6):
    """Roll a dice"""
    result = random.randint(1, dice)
    await ctx.send(f"🎲 {ctx.author.name} rolled a **{result}** (1-{dice})")

@bot.command(name="8ball")
async def eightball(ctx, *, question: str):
    """Ask the 8-ball"""
    responses = ["Yes", "No", "Maybe", "Definitely", "Ask later", "No way", "Absolutely!"]
    await ctx.send(f"🎱 {random.choice(responses)}")

@bot.command(name="coinflip")
async def coinflip(ctx):
    """Flip a coin"""
    result = random.choice(["Heads", "Tails"])
    await ctx.send(f"🪙 Coin landed on: **{result}**")

# ========== HELP COMMAND ==========
@bot.command(name="help")
async def help_command(ctx, command_name: str = None):
    if command_name:
        cmd = bot.get_command(command_name)
        if cmd:
            embed = discord.Embed(title=f"📖 {config['prefix']}{cmd.name}", color=discord.Color.blue())
            embed.add_field(name="Description", value=cmd.help or "No description", inline=False)
            await ctx.send(embed=embed)
            return
        else:
            await ctx.send(f"❌ Command `{command_name}` not found!")
            return
    
    embed = discord.Embed(title="🤖 Notorious 47", description=f"Prefix: `{config['prefix']}`", color=discord.Color.gold())
    embed.add_field(name="🛡️ Moderation", value="`ban`, `kick`, `clear`, `addrole`, `removerole`", inline=False)
    embed.add_field(name="⚙️ Admin", value="`badword`, `setwelcome`, `setgoodbye`, `changeprefix`, `setlog`, `autorole`, `setup`", inline=False)
    embed.add_field(name="🎮 Games", value="`roll`, `8ball`, `coinflip`", inline=False)
    embed.add_field(name="📊 Utility", value="`ping`, `serverinfo`, `userinfo`, `avatar`", inline=False)
    embed.set_footer(text="Notorious 47 - Admin Bot")
    await ctx.send(embed=embed)

# ========== SLASH COMMANDS ==========
@bot.tree.command(name="ping", description="Check bot latency")
async def slash_ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! Latency: {round(bot.latency * 1000)}ms")

@bot.tree.command(name="serverinfo", description="Get server information")
async def slash_serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"📊 {guild.name}", color=discord.Color.blue())
    embed.add_field(name="Members", value=guild.member_count)
    embed.add_field(name="Owner", value=guild.owner.mention)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="userinfo", description="Get user information")
async def slash_userinfo(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    embed = discord.Embed(title=f"👤 {member.name}", color=member.color)
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    embed.add_field(name="ID", value=member.id)
    await interaction.response.send_message(embed=embed)

# ========== LOAD COGS AND RUN ==========
@bot.event
async def on_ready():
    print(f"✅ {bot.user.name} is online!")
    print(f"📊 Serving {len(bot.guilds)} servers")
    
    # Load all cogs
    cogs = ["automod", "music", "admin", "logs", "games"]
    for cog in cogs:
        try:
            await bot.load_extension(cog)
            print(f"✅ Loaded: {cog}.py")
        except Exception as e:
            print(f"⚠️ Could not load {cog}.py: {e}")
    
    await bot.change_presence(activity=discord.Game(name=f"{config['prefix']}help | /help"))
    
    # Sync slash commands
    try:
        await bot.tree.sync()
        print(f"✅ Slash commands synced!")
    except Exception as e:
        print(f"❌ Slash sync failed: {e}")

# Error handler
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"❌ You need `{', '.join(error.missing_permissions)}` permission!", delete_after=5)
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        print(f"Error: {error}")

# ========== RUN BOT ==========
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    print("❌ BOT_TOKEN not found in environment variables!")
else:
    bot.run(TOKEN)
