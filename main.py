from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is Online!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# main.py - Updated with dynamic bad words, welcome message, prefix
import discord
from discord.ext import commands
import json
import os
import asyncio

# Load config
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

# Bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=config["prefix"], intents=intents, help_command=None)

def save_config():
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

@bot.event
async def on_ready():
    print(f"✅ {bot.user.name} is online!")
    print(f"📊 Serving {len(bot.guilds)} servers")
    
    # Load all cogs
    try:
        await bot.load_extension("automod")
        await bot.load_extension("music")
        await bot.load_extension("admin")
        await bot.load_extension("logs")
        await bot.load_extension("games")
        print("✅ All modules loaded!")
    except Exception as e:
        print(f"Modules error: {e}")
    
    await bot.change_presence(activity=discord.Game(name=f"{config['prefix']}help"))

# ========== BAD WORDS MANAGEMENT ==========
@bot.group(name="badword")
@commands.has_permissions(administrator=True)
async def badword(self, ctx):
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

# ========== WELCOME MESSAGE MANAGEMENT ==========
@bot.command(name="setwelcome")
@commands.has_permissions(administrator=True)
async def set_welcome_message(ctx, *, message: str = None):
    """Set custom welcome message
    Variables: {user} {server} {member_count} {mention}
    Example: $setwelcome Welcome {mention} to {server}!"""
    if message is None:
        embed = discord.Embed(title="📝 Current Welcome Message", description=config.get("welcome_message", "Not set"), color=discord.Color.blue())
        embed.add_field(name="Variables", value="`{user}` - Username\n`{mention}` - Mention user\n`{server}` - Server name\n`{member_count}` - Member count", inline=False)
        await ctx.send(embed=embed)
        return
    
    config["welcome_message"] = message
    save_config()
    await ctx.send(f"✅ Welcome message updated!\nPreview: {await format_welcome_message(ctx.guild, ctx.author, message)}")

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
    """Set custom goodbye message
    Variables: {user} {server} {member_count}"""
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

async def format_welcome_message(guild, member, message):
    return message.replace("{user}", member.name).replace("{mention}", member.mention).replace("{server}", guild.name).replace("{member_count}", str(len(guild.members)))

async def format_goodbye_message(guild, member, message):
    return message.replace("{user}", member.name).replace("{server}", guild.name).replace("{member_count}", str(len(guild.members)))

@bot.event
async def on_member_join(member):
    # Welcome message
    welcome_channel_id = config.get("welcome_channel")
    if welcome_channel_id:
        channel = bot.get_channel(welcome_channel_id)
        if channel:
            msg_template = config.get("welcome_message", "🎉 Welcome {mention} to {server}!")
            msg = await format_welcome_message(member.guild, member, msg_template)
            
            embed = discord.Embed(description=msg, color=discord.Color.green())
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            await channel.send(embed=embed)
    
    # Autorole
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
            msg = await format_goodbye_message(member.guild, member, msg_template)
            await channel.send(msg)

# ========== AUTO-MOD WITH DYNAMIC BAD WORDS ==========
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Check bad words from config
    bad_words = config.get("bad_words", [])
    msg_lower = message.content.lower()
    
    for word in bad_words:
        if word in msg_lower:
            await message.delete()
            await message.channel.send(f"{message.author.mention} ❌ That word is not allowed!", delete_after=3)
            return
    
    await bot.process_commands(message)

# ========== PREFIX CHANGE ==========
@bot.command(name="changeprefix", aliases=["prefix"])
@commands.has_permissions(administrator=True)
async def changeprefix(ctx, new_prefix: str):
    """Change bot prefix (admin only)"""
    if len(new_prefix) > 5:
        await ctx.send("❌ Prefix too long! Max 5 characters.")
        return
    
    config["prefix"] = new_prefix
    bot.command_prefix = new_prefix
    save_config()
    await ctx.send(f"✅ Prefix changed to `{new_prefix}`")

# ========== SETUP COMMAND ==========
@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup_guide(ctx):
    """Show setup guide"""
    embed = discord.Embed(title="🔧 Notorious 47 - Setup Guide", color=discord.Color.green())
    embed.add_field(name="1️⃣ Bad Words", value="`$badword add <word>`\n`$badword remove <word>`\n`$badword` (view list)", inline=False)
    embed.add_field(name="2️⃣ Welcome Message", value="`$setwelcome Welcome {mention} to {server}!`\n`$setwelcomechannel #channel`", inline=False)
    embed.add_field(name="3️⃣ Goodbye Message", value="`$setgoodbye {user} left!`\n`$setgoodbyechannel #channel`", inline=False)
    embed.add_field(name="4️⃣ Prefix", value="`$changeprefix !`", inline=False)
    embed.add_field(name="5️⃣ Log Channel", value="`$setlog #channel`", inline=False)
    embed.add_field(name="6️⃣ Auto Role", value="`$autorole @role`", inline=False)
    embed.add_field(name="7️⃣ Auto-Mod", value="`$automod` - View settings", inline=False)
    await ctx.send(embed=embed)

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
    
    embed = discord.Embed(title="🤖 Notorious 47", description=f"Prefix: `{config['prefix']}`", color=discord.Color.gold())
    embed.add_field(name="🛡️ Moderation", value="`ban`, `kick`, `timeout`, `warn`, `clear`, `lock`, `unlock`", inline=False)
    embed.add_field(name="⚙️ Admin", value="`badword`, `setwelcome`, `setgoodbye`, `changeprefix`, `setlog`, `autorole`, `setup`", inline=False)
    embed.add_field(name="🎵 Music", value="`play`, `skip`, `stop`, `queue`, `pause`, `resume`", inline=False)
    embed.add_field(name="👥 Roles", value="`addrole`, `removerole`", inline=False)
    embed.add_field(name="🎮 Games", value="`roll`, `8ball`, `rps`, `guess`, `trivia`, `coinflip`, `slots`", inline=False)
    embed.add_field(name="📊 Utility", value="`ping`, `serverinfo`, `userinfo`, `avatar`", inline=False)
    await ctx.send(embed=embed)

# ========== SET LOG CHANNEL ==========
@bot.command(name="setlog")
@commands.has_permissions(administrator=True)
async def setlog(ctx, channel: discord.TextChannel = None):
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
    if role is None:
        config["autorole"] = None
        await ctx.send("✅ Auto-role disabled!")
    else:
        config["autorole"] = role.id
        await ctx.send(f"✅ Auto-role set to {role.mention}")
    save_config()
# Add this import at the top of main.py (with your other imports)
from discord import app_commands

# Add this after @bot.event async def on_ready()
# Find your existing on_ready function and add the sync line inside it
@bot.event
async def on_ready():
    print(f"✅ {bot.user.name} is online!")
    print(f"📊 Serving {len(bot.guilds)} servers")
    
    # ADD THIS LINE - Syncs slash commands with Discord
    await bot.tree.sync()
    print("✅ Slash commands synced!")
    
    await bot.change_presence(activity=discord.Game(name=f"{config['prefix']}help"))

# Add a test slash command (add this anywhere after bot definition but before bot.run)
@bot.tree.command(name="ping", description="Check bot latency")
async def slash_ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! Latency: {round(bot.latency * 1000)}ms")

@bot.tree.command(name="userinfo", description="Get information about a user")
async def slash_userinfo(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    embed = discord.Embed(title=f"👤 {member.name}", color=discord.Color.blue())
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "Unknown")
    await interaction.response.send_message(embed=embed)
# ========== RUN BOT ==========
keep_alive()
import os
TOKEN = os.environ.get('BOT_TOKEN')
bot.run(TOKEN) # Ee line marannu pokalle! ✅
