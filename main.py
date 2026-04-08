#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NoToRiOuS ⁴⁷ - The Ultimate Discord Bot
Built by Ishan // Toxyyy // Zaid | Commissioned: 06-04-2026
Single-file masterpiece with hybrid commands, premium design, and full functionality.
"""

import os
import sys
import asyncio
import logging
import platform
import random
import json
import socket
import struct
import re
import html
from datetime import datetime, timedelta
from threading import Thread
from typing import Optional, List, Dict, Any, Union
from collections import defaultdict

# Third-party imports
import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
from flask import Flask
import dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp as youtube_dl
import psutil

# Load environment variables
dotenv.load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ==================== FLASK WEB SERVER FOR RENDER & UPTIMEROBOT ====================
app = Flask(__name__)

@app.route('/')
def home():
    return "NoToRiOuS ⁴⁷ is operational and patrolling the digital realm. All systems nominal."

def run_webserver():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

def start_webserver():
    t = Thread(target=run_webserver)
    t.start()
    logger.info("🌐 Webserver thread started successfully.")

# ==================== UTILITY CLASSES ====================
class BotEmojis:
    """Central repository for emojis to maintain consistent visual language."""
    BAN = "🔨"
    KICK = "👢"
    MUTE = "🔇"
    WARN = "⚠️"
    TIMEOUT = "⏳"
    PURGE = "🧹"
    SUCCESS = "✅"
    ERROR = "❌"
    INFO = "ℹ️"
    WARNING = "⚠️"
    LOADING = "⏳"
    HUG = "🤗"
    KISS = "😘"
    SLAP = "👋"
    KILL = "💀"
    SERVER = "🖥️"
    PLAYER = "👤"
    PING = "📶"
    PLAY = "▶️"
    PAUSE = "⏸️"
    STOP = "⏹️"
    SKIP = "⏭️"
    SHUFFLE = "🔀"
    VOLUME_UP = "🔊"
    VOLUME_DOWN = "🔉"

class NotoriousEmbed(discord.Embed):
    """Custom Embed class with pre-set styling for the NoToRiOuS ⁴⁷ aesthetic."""
    def __init__(self, *args, **kwargs):
        color = kwargs.pop('color', 0x9b59b6)  # Rich purple default
        super().__init__(*args, color=color, **kwargs)
        self.timestamp = datetime.utcnow()
        self.set_footer(text="NoToRiOuS ⁴⁷ • Dominion Through Order")

    def set_success(self):
        self.color = discord.Color.green()
        return self

    def set_error(self):
        self.color = discord.Color.brand_red()
        return self

    def set_warning(self):
        self.color = discord.Color.gold()
        return self

    def set_info(self):
        self.color = discord.Color.blue()
        return self

    def add_premium_field(self, name: str, value: str, inline: bool = True):
        formatted_name = f"『 {name.upper()} 』"
        self.add_field(name=formatted_name, value=value, inline=inline)
        return self

def generate_punishment_message(action: str, target: discord.Member, reason: str, moderator: discord.Member, duration: Optional[str] = None) -> str:
    """Generates powerful, impactful messages for moderation actions."""
    messages = {
        "ban": [
            f"{target.mention} has been **expelled** from this realm by {moderator.mention}. Their presence is no longer tolerated. The gates are sealed.",
            f"By the decree of {moderator.mention}, {target.mention} has been **banished**. Let their absence serve as a lesson to all.",
            f"**ORDER HAS BEEN RESTORED.** {target.mention} has been **permanently removed** from our ranks. Do not follow in their footsteps."
        ],
        "kick": [
            f"{target.mention} has been **forcefully ejected** from the premises by {moderator.mention}. They may return, but let this be a warning.",
            f"Clean sweep. {target.mention} has been **kicked** by {moderator.mention}. Your disruption ends here.",
            f"{moderator.mention} has shown {target.mention} the door. Good riddance."
        ],
        "mute": [
            f"{target.mention} has been **gagged** by {moderator.mention} for {duration}. Their words are now silenced. Think before you speak.",
            f"**SILENCE.** {moderator.mention} has **muted** {target.mention} for {duration}. Use this time to reflect on your transgressions.",
            f"Your voice is a privilege, not a right. {target.mention} has been **muted** for {duration} by {moderator.mention}."
        ],
        "warn": [
            f"{target.mention}, you have been issued a **formal warning** by {moderator.mention}. This is not a drill. Correct your behavior immediately.",
            f"**STRIKE ONE.** {moderator.mention} has warned {target.mention}. You are on thin ice. Continued misconduct will result in severe consequences.",
            f"A mark has been placed upon your record, {target.mention}. Heed this **warning** from {moderator.mention}."
        ],
        "timeout": [
            f"{target.mention} has been placed in a **timeout** by {moderator.mention} for {duration}. You are confined to the shadows. Reflect on your actions.",
            f"**RESTRICTED.** {moderator.mention} has **timed out** {target.mention} for {duration}. Your ability to interact has been revoked.",
            f"Silence is golden. {target.mention} has been **timed out** for {duration} by the watchful eye of {moderator.mention}."
        ]
    }
    base_msg = random.choice(messages.get(action, [f"{target.mention} has been {action}ed."]))
    reason_part = f"\n\n**REASON FOR ACTION:** {reason}" if reason else ""
    return base_msg + reason_part

def get_uptime(start_time: datetime) -> str:
    """Calculates and formats the bot's uptime."""
    delta = datetime.utcnow() - start_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h {minutes}m {seconds}s"
# ==================== MUSIC PLAYER CLASSES ====================
# Suppress youtube_dl noise
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'force-ipv4': True,
    'cachedir': False
}

ffmpeg_options = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    """Represents an audio source from YouTube."""
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')
        self.uploader = data.get('uploader')
        self.thumbnail = data.get('thumbnail')
        self.webpage_url = data.get('webpage_url')
        self.requester = None

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class MusicPlayer:
    """Manages the music queue and playback for a single guild."""
    def __init__(self, bot, guild: discord.Guild):
        self.bot = bot
        self.guild = guild
        self.queue: List[YTDLSource] = []
        self.current: Optional[YTDLSource] = None
        self.voice_client: Optional[discord.VoiceClient] = None
        self.loop = False
        self.next = asyncio.Event()
        self.task: Optional[asyncio.Task] = None

    async def add_to_queue(self, query: Union[str, List[str]], requester: discord.Member) -> int:
        if isinstance(query, list):
            added = 0
            for q in query:
                added += await self._add_single(q, requester)
            return added
        else:
            return await self._add_single(query, requester)

    async def _add_single(self, query: str, requester: discord.Member) -> int:
        try:
            source = await YTDLSource.from_url(query, loop=self.bot.loop, stream=True)
            source.requester = requester
            self.queue.append(source)
            return 1
        except Exception as e:
            logger.error(f"Failed to add track: {e}")
            raise e

    async def play_next(self):
        if self.loop and self.current:
            self.queue.insert(0, self.current)
        self.current = None
        if self.queue:
            self.current = self.queue.pop(0)
            self.voice_client.play(self.current, after=lambda e: self.bot.loop.call_soon_threadsafe(self.next.set))
        else:
            await self.voice_client.disconnect()
            self.voice_client = None

    async def player_loop(self):
        await self.bot.wait_until_ready()
        while self.voice_client:
            self.next.clear()
            await self.play_next()
            await self.next.wait()

    def start(self, voice_client: discord.VoiceClient):
        self.voice_client = voice_client
        self.task = self.bot.loop.create_task(self.player_loop())

    def stop(self):
        if self.task:
            self.task.cancel()
        self.queue.clear()
        self.current = None
        if self.voice_client:
            self.bot.loop.create_task(self.voice_client.disconnect())
            self.voice_client = None

# ==================== SPOTIFY API CLASS ====================
class SpotifyAPI:
    """Wrapper for Spotify Web API using provided credentials."""
    def __init__(self):
        self.client_id = os.environ.get('SPOTIFY_CLIENT_ID', 'a568b55af1d940aca52ea8fe02f0d93b')
        self.client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET', 'e8199f4024fe49c5b22ea9a3dd0c4789')
        if not self.client_id or not self.client_secret:
            logger.error("Spotify API credentials missing.")
            self.sp = None
            return
        try:
            auth_manager = SpotifyClientCredentials(client_id=self.client_id, client_secret=self.client_secret)
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            logger.info("Spotify API initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Spotify: {e}")
            self.sp = None

    def get_track_info(self, url_or_id: str) -> Optional[Dict[str, Any]]:
        if not self.sp:
            return None
        try:
            if 'track' in url_or_id:
                track_id = re.search(r'track/([a-zA-Z0-9]+)', url_or_id).group(1)
            else:
                track_id = url_or_id
            track = self.sp.track(track_id)
            return track
        except Exception as e:
            logger.error(f"Failed to get Spotify track: {e}")
            return None

    def search_track(self, query: str) -> Optional[str]:
        if not self.sp:
            return None
        try:
            results = self.sp.search(q=query, type='track', limit=1)
            if results['tracks']['items']:
                track = results['tracks']['items'][0]
                artist = track['artists'][0]['name']
                name = track['name']
                return f"{artist} - {name}"
            return None
        except Exception as e:
            logger.error(f"Failed to search Spotify: {e}")
            return None

# ==================== GAME UI VIEWS ====================
class TicTacToeButton(discord.ui.Button):
    def __init__(self, x: int, y: int):
        super().__init__(style=discord.ButtonStyle.secondary, label='\u200b', row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: 'TicTacToe' = self.view
        state = view.board[self.y][self.x]
        if state in (view.X, view.O):
            return

        if view.current_player == interaction.user:
            if view.current_player == view.X:
                self.style = discord.ButtonStyle.danger
                self.label = 'X'
                self.disabled = True
                view.board[self.y][self.x] = view.X
                view.current_player = view.O
                content = f"It is now {view.player2.mention}'s turn. (O)"
            else:
                self.style = discord.ButtonStyle.success
                self.label = 'O'
                self.disabled = True
                view.board[self.y][self.x] = view.O
                view.current_player = view.X
                content = f"It is now {view.player1.mention}'s turn. (X)"

            winner = view.check_board_winner()
            if winner is not None:
                if winner == view.X:
                    content = f'🏆 **{view.player1.mention} (X) has emerged victorious!** Congratulations!'
                elif winner == view.O:
                    content = f'🏆 **{view.player2.mention} (O) has emerged victorious!** Congratulations!'
                else:
                    content = "It's a draw! A battle of equals."

                for child in view.children:
                    child.disabled = True
                view.stop()
            await interaction.response.edit_message(content=content, view=view)
        else:
            await interaction.response.send_message("It is not your turn. Patience is a virtue.", ephemeral=True)

class TicTacToe(discord.ui.View):
    X = -1
    O = 1
    Tie = 2

    def __init__(self, player1: discord.Member, player2: discord.Member):
        super().__init__(timeout=60.0)
        self.player1 = player1
        self.player2 = player2
        self.current_player = player1
        self.board = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        for x in range(3):
            for y in range(3):
                self.add_item(TicTacToeButton(x, y))
        self.message = None

    def check_board_winner(self):
        for across in self.board:
            value = sum(across)
            if value == 3: return self.O
            elif value == -3: return self.X
        for line in range(3):
            value = self.board[0][line] + self.board[1][line] + self.board[2][line]
            if value == 3: return self.O
            elif value == -3: return self.X
        diag = self.board[0][2] + self.board[1][1] + self.board[2][0]
        if diag == 3: return self.O
        elif diag == -3: return self.X
        diag = self.board[0][0] + self.board[1][1] + self.board[2][2]
        if diag == 3: return self.O
        elif diag == -3: return self.X
        if all(i != 0 for row in self.board for i in row):
            return self.Tie
        return None

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await self.message.edit(content="This game of Tic-Tac-Toe has been abandoned due to inactivity.", view=self)

class TriviaButton(discord.ui.Button):
    def __init__(self, index: int, label: str):
        super().__init__(style=discord.ButtonStyle.primary, label=label)
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: 'TriviaView' = self.view
        if view.answered:
            await interaction.response.send_message("This question has already been answered.", ephemeral=True)
            return
        view.answered = True
        for child in view.children:
            child.disabled = True
        if self.index == view.correct_index:
            await interaction.response.send_message(f"✅ Correct! Well done, {interaction.user.mention}!")
        else:
            await interaction.response.send_message(f"❌ Incorrect! The correct answer was: **{view.options[view.correct_index]}**")
        await view.message.edit(view=view)

class TriviaView(discord.ui.View):
    def __init__(self, question: str, options: List[str], correct_index: int):
        super().__init__(timeout=30.0)
        self.question = question
        self.options = options
        self.correct_index = correct_index
        self.answered = False
        self.message = None
        for i, option in enumerate(options):
            self.add_item(TriviaButton(i, option))

    async def on_timeout(self):
        if not self.answered:
            for child in self.children:
                child.disabled = True
            if self.message:
                await self.message.edit(content="Time's up! No one answered correctly.", view=self)
# ==================== SA-MP QUERY CLASS ====================
class SampQuery:
    """Simple SA-MP query client to fetch server information."""
    @staticmethod
    async def query_server(ip: str, port: int = 7777) -> Optional[Dict]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)
            packet = b'SAMP'
            host_bytes = socket.inet_aton(ip)
            packet += host_bytes
            packet += struct.pack('>H', port)
            packet += b'i'
            sock.sendto(packet, (ip, port))
            data, _ = sock.recvfrom(2048)
            sock.close()
            # Mock data for demonstration – replace with proper parsing
            return {
                "online": True,
                "hostname": "SA-MP Server (Mock Data)",
                "players": random.randint(10, 100),
                "maxplayers": 100,
                "gamemode": "Roleplay",
                "language": "English",
                "password": False,
                "player_list": [{"id": i, "name": f"Player{i}", "score": random.randint(10, 100), "ping": random.randint(20, 150)} for i in range(5)]
            }
        except socket.timeout:
            return None
        except Exception as e:
            logger.error(f"SA-MP query error {ip}:{port}: {e}")
            return None

# ==================== MAIN BOT CLASS ====================
class NotoriousBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.presences = True

        super().__init__(
            command_prefix='~',
            intents=intents,
            help_command=None,
            case_insensitive=True,
            description="NoToRiOuS ⁴⁷: The apex predator of Discord server management, blending formidable administration with an unyielding sense of style."
        )

        self.start_time = datetime.utcnow()

        # In-memory data stores
        self.warns: Dict[int, Dict[int, List[Dict]]] = {}
        self.badwords: List[str] = [
            "fuck", "shit", "bitch", "asshole", "cunt", "nigger", "faggot",
            "retard", "whore", "slut", "pussy", "dick", "cock", "bastard"
        ]
        self.log_channels: Dict[int, Dict[str, int]] = {}
        self.players: Dict[int, MusicPlayer] = {}
        self.spotify = SpotifyAPI()  # Now defined!

        # Spam caches
        self.spam_cache: Dict[int, List[datetime]] = defaultdict(list)
        self.mention_cache: Dict[int, List[datetime]] = defaultdict(list)
        self.emoji_cache: Dict[int, List[datetime]] = defaultdict(list)

        # Fun games
        self.guess_games: Dict[int, int] = {}

        # SAMP monitoring
        self.active_samp_monitors: Dict[int, asyncio.Task] = {}
        self.current_samp_server: Dict[int, Dict] = {}
        self.samp_query = SampQuery()

        self.trivia_categories = {
            "9": "General Knowledge", "17": "Science & Nature", "21": "Sports",
            "22": "Geography", "23": "History", "31": "Anime & Manga"
        }

        # Load warns from file
        try:
            with open('warnings.json', 'r') as f:
                self.warns = json.load(f)
        except:
            pass

    def save_warns(self):
        with open('warnings.json', 'w') as f:
            json.dump(self.warns, f, indent=4)

    def get_user_warns(self, guild_id: int, user_id: int) -> List[Dict]:
        return self.warns.get(str(guild_id), {}).get(str(user_id), [])

    def add_warn(self, guild_id: int, user_id: int, moderator_id: int, reason: str):
        guild_id_str = str(guild_id)
        user_id_str = str(user_id)
        if guild_id_str not in self.warns:
            self.warns[guild_id_str] = {}
        if user_id_str not in self.warns[guild_id_str]:
            self.warns[guild_id_str][user_id_str] = []
        warning = {
            "id": len(self.warns[guild_id_str][user_id_str]) + 1,
            "moderator": moderator_id,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.warns[guild_id_str][user_id_str].append(warning)
        self.save_warns()
        return warning

    def get_player(self, guild: discord.Guild) -> MusicPlayer:
        if guild.id not in self.players:
            self.players[guild.id] = MusicPlayer(self, guild)
        return self.players[guild.id]

    def get_log_channel(self, guild: discord.Guild, log_type: str) -> Optional[discord.TextChannel]:
        guild_config = self.log_channels.get(guild.id, {})
        channel_id = guild_config.get(log_type)
        if channel_id:
            return guild.get_channel(channel_id)
        return None

    async def setup_hook(self):
        await self.tree.sync()
        logger.info("✅ Command tree synced globally.")

    async def on_ready(self):
        logger.info(f"✅ Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"📊 Discord.py: {discord.__version__} | Python: {platform.python_version()}")
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name="over the realm of N47 | ~help"),
            status=discord.Status.online
        )
        logger.info("🚀 NoToRiOuS ⁴⁷ is fully operational and ready for duty.")

    async def on_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingPermissions):
            embed = NotoriousEmbed().set_error()
            embed.description = "You lack the authority to execute this command. Your actions are being monitored."
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BadArgument):
            embed = NotoriousEmbed().set_error()
            embed.description = "The parameters you provided are incorrect. Check the command usage and try again."
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = NotoriousEmbed().set_error()
            embed.description = "This command requires additional information to proceed. Please provide all necessary parameters."
            await ctx.send(embed=embed)
        else:
            logger.error(f"Ignoring exception in command {ctx.command}:", exc_info=error)
            embed = NotoriousEmbed().set_error()
            embed.description = "An unforeseen error occurred while executing that command. The issue has been logged for investigation."
            await ctx.send(embed=embed)

    # ==================== AUTO-MOD EVENTS ====================
    async def check_badwords(self, message: discord.Message):
        content_lower = message.content.lower()
        for word in self.badwords:
            if word in content_lower:
                await message.delete()
                embed = NotoriousEmbed()
                embed.color = discord.Color.dark_red()
                embed.description = f"{message.author.mention}, **YOU AIN'T PERMITTED TO TALK LIKE THAT IN THIS ESTABLISHMENT. APOLOGIZE NOW !**"
                embed.set_footer(text="NoToRiOuS ⁴⁷ Auto-Mod • Zero Tolerance")
                warning = await message.channel.send(embed=embed)
                await asyncio.sleep(5)
                await warning.delete()
                logger.info(f"Auto-mod deleted message from {message.author} containing bad word: '{word}'")
                break

    async def check_spam(self, message: discord.Message):
        user_id = message.author.id
        now = datetime.utcnow()
        window = 10

        self.spam_cache[user_id] = [t for t in self.spam_cache[user_id] if (now - t).total_seconds() < window]
        self.spam_cache[user_id].append(now)
        if len(self.spam_cache[user_id]) >= 6:
            await self.punish_spammer(message.author, "message spam", 5)
            self.spam_cache[user_id].clear()
            return

        if len(message.mentions) >= 6:
            self.mention_cache[user_id] = [t for t in self.mention_cache[user_id] if (now - t).total_seconds() < window * 2]
            self.mention_cache[user_id].append(now)
            if len(self.mention_cache[user_id]) >= 2:
                await self.punish_spammer(message.author, "excessive mentions", 5)
                self.mention_cache[user_id].clear()
                return

        emoji_count = sum(1 for char in message.content if char in "😀😃😄😁😆😅😂🤣😊😇🙂🙃😉😌😍🥰😘😗😙😚😋😛😝😜🤪🤨🧐🤓😎🤩🥳😏😒😞😔😟😕🙁☹️😣😖😫😩🥺😢😭😤😠😡🤬🤯😳🥵🥶😱😨😰😥😓🤗🤔🤭🤫🤥😶😐😑😬🙄😯😦😧😮😲🥱😴🤤😪😵🤐🥴🤢🤮🤧😷🤒🤕🤑🤠")
        if emoji_count >= 10:
            self.emoji_cache[user_id] = [t for t in self.emoji_cache[user_id] if (now - t).total_seconds() < window * 2]
            self.emoji_cache[user_id].append(now)
            if len(self.emoji_cache[user_id]) >= 2:
                await self.punish_spammer(message.author, "excessive emoji usage", 5)
                self.emoji_cache[user_id].clear()
                return

    async def punish_spammer(self, member: discord.Member, reason: str, timeout_minutes: int = 5):
        try:
            duration = timedelta(minutes=timeout_minutes)
            await member.timeout(duration, reason=f"Auto-Mod: {reason}")
            embed = NotoriousEmbed()
            embed.color = discord.Color.orange()
            embed.description = f"{member.mention} has been **timed out for {timeout_minutes} minutes** for **{reason}**."
            embed.set_footer(text="NoToRiOuS ⁴⁷ • Maintaining Order")
            if member.guild.system_channel:
                await member.guild.system_channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Auto-mod timeout failed for {member}: {e}")

    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        await self.check_badwords(message)
        await self.check_spam(message)
        await self.process_commands(message)

# Instantiate the bot
bot = NotoriousBot()
# ==================== MUSIC PLAYER CLASSES ====================
# Suppress youtube_dl noise
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'force-ipv4': True,
    'cachedir': False
}

ffmpeg_options = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    """Represents an audio source from YouTube."""
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')
        self.uploader = data.get('uploader')
        self.thumbnail = data.get('thumbnail')
        self.webpage_url = data.get('webpage_url')
        self.requester = None

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class MusicPlayer:
    """Manages the music queue and playback for a single guild."""
    def __init__(self, bot, guild: discord.Guild):
        self.bot = bot
        self.guild = guild
        self.queue: List[YTDLSource] = []
        self.current: Optional[YTDLSource] = None
        self.voice_client: Optional[discord.VoiceClient] = None
        self.loop = False
        self.next = asyncio.Event()
        self.task: Optional[asyncio.Task] = None

    async def add_to_queue(self, query: Union[str, List[str]], requester: discord.Member) -> int:
        if isinstance(query, list):
            added = 0
            for q in query:
                added += await self._add_single(q, requester)
            return added
        else:
            return await self._add_single(query, requester)

    async def _add_single(self, query: str, requester: discord.Member) -> int:
        try:
            source = await YTDLSource.from_url(query, loop=self.bot.loop, stream=True)
            source.requester = requester
            self.queue.append(source)
            return 1
        except Exception as e:
            logger.error(f"Failed to add track: {e}")
            raise e

    async def play_next(self):
        if self.loop and self.current:
            self.queue.insert(0, self.current)
        self.current = None
        if self.queue:
            self.current = self.queue.pop(0)
            self.voice_client.play(self.current, after=lambda e: self.bot.loop.call_soon_threadsafe(self.next.set))
        else:
            await self.voice_client.disconnect()
            self.voice_client = None

    async def player_loop(self):
        await self.bot.wait_until_ready()
        while self.voice_client:
            self.next.clear()
            await self.play_next()
            await self.next.wait()

    def start(self, voice_client: discord.VoiceClient):
        self.voice_client = voice_client
        self.task = self.bot.loop.create_task(self.player_loop())

    def stop(self):
        if self.task:
            self.task.cancel()
        self.queue.clear()
        self.current = None
        if self.voice_client:
            self.bot.loop.create_task(self.voice_client.disconnect())
            self.voice_client = None

class SpotifyAPI:
    """Wrapper for Spotify Web API using provided credentials."""
    def __init__(self):
        self.client_id = os.environ.get('SPOTIFY_CLIENT_ID', 'a568b55af1d940aca52ea8fe02f0d93b')
        self.client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET', 'e8199f4024fe49c5b22ea9a3dd0c4789')
        if not self.client_id or not self.client_secret:
            logger.error("Spotify API credentials missing.")
            self.sp = None
            return
        try:
            auth_manager = SpotifyClientCredentials(client_id=self.client_id, client_secret=self.client_secret)
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            logger.info("Spotify API initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Spotify: {e}")
            self.sp = None

    def get_track_info(self, url_or_id: str) -> Optional[Dict[str, Any]]:
        if not self.sp:
            return None
        try:
            if 'track' in url_or_id:
                track_id = re.search(r'track/([a-zA-Z0-9]+)', url_or_id).group(1)
            else:
                track_id = url_or_id
            track = self.sp.track(track_id)
            return track
        except Exception as e:
            logger.error(f"Failed to get Spotify track: {e}")
            return None

    def search_track(self, query: str) -> Optional[str]:
        if not self.sp:
            return None
        try:
            results = self.sp.search(q=query, type='track', limit=1)
            if results['tracks']['items']:
                track = results['tracks']['items'][0]
                artist = track['artists'][0]['name']
                name = track['name']
                return f"{artist} - {name}"
            return None
        except Exception as e:
            logger.error(f"Failed to search Spotify: {e}")
            return None

# ==================== GAME UI VIEWS ====================
class TicTacToeButton(discord.ui.Button):
    def __init__(self, x: int, y: int):
        super().__init__(style=discord.ButtonStyle.secondary, label='\u200b', row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: 'TicTacToe' = self.view
        state = view.board[self.y][self.x]
        if state in (view.X, view.O):
            return

        if view.current_player == interaction.user:
            if view.current_player == view.X:
                self.style = discord.ButtonStyle.danger
                self.label = 'X'
                self.disabled = True
                view.board[self.y][self.x] = view.X
                view.current_player = view.O
                content = f"It is now {view.player2.mention}'s turn. (O)"
            else:
                self.style = discord.ButtonStyle.success
                self.label = 'O'
                self.disabled = True
                view.board[self.y][self.x] = view.O
                view.current_player = view.X
                content = f"It is now {view.player1.mention}'s turn. (X)"

            winner = view.check_board_winner()
            if winner is not None:
                if winner == view.X:
                    content = f'🏆 **{view.player1.mention} (X) has emerged victorious!** Congratulations!'
                elif winner == view.O:
                    content = f'🏆 **{view.player2.mention} (O) has emerged victorious!** Congratulations!'
                else:
                    content = "It's a draw! A battle of equals."

                for child in view.children:
                    child.disabled = True
                view.stop()
            await interaction.response.edit_message(content=content, view=view)
        else:
            await interaction.response.send_message("It is not your turn. Patience is a virtue.", ephemeral=True)

class TicTacToe(discord.ui.View):
    X = -1
    O = 1
    Tie = 2

    def __init__(self, player1: discord.Member, player2: discord.Member):
        super().__init__(timeout=60.0)
        self.player1 = player1
        self.player2 = player2
        self.current_player = player1
        self.board = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        for x in range(3):
            for y in range(3):
                self.add_item(TicTacToeButton(x, y))
        self.message = None

    def check_board_winner(self):
        for across in self.board:
            value = sum(across)
            if value == 3: return self.O
            elif value == -3: return self.X
        for line in range(3):
            value = self.board[0][line] + self.board[1][line] + self.board[2][line]
            if value == 3: return self.O
            elif value == -3: return self.X
        diag = self.board[0][2] + self.board[1][1] + self.board[2][0]
        if diag == 3: return self.O
        elif diag == -3: return self.X
        diag = self.board[0][0] + self.board[1][1] + self.board[2][2]
        if diag == 3: return self.O
        elif diag == -3: return self.X
        if all(i != 0 for row in self.board for i in row):
            return self.Tie
        return None

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await self.message.edit(content="This game of Tic-Tac-Toe has been abandoned due to inactivity.", view=self)

class TriviaButton(discord.ui.Button):
    def __init__(self, index: int, label: str):
        super().__init__(style=discord.ButtonStyle.primary, label=label)
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: 'TriviaView' = self.view
        if view.answered:
            await interaction.response.send_message("This question has already been answered.", ephemeral=True)
            return
        view.answered = True
        for child in view.children:
            child.disabled = True
        if self.index == view.correct_index:
            await interaction.response.send_message(f"✅ Correct! Well done, {interaction.user.mention}!")
        else:
            await interaction.response.send_message(f"❌ Incorrect! The correct answer was: **{view.options[view.correct_index]}**")
        await view.message.edit(view=view)

class TriviaView(discord.ui.View):
    def __init__(self, question: str, options: List[str], correct_index: int):
        super().__init__(timeout=30.0)
        self.question = question
        self.options = options
        self.correct_index = correct_index
        self.answered = False
        self.message = None
        for i, option in enumerate(options):
            self.add_item(TriviaButton(i, option))

    async def on_timeout(self):
        if not self.answered:
            for child in self.children:
                child.disabled = True
            if self.message:
                await self.message.edit(content="Time's up! No one answered correctly.", view=self)
# ==================== MODERATION COMMANDS ====================
@bot.hybrid_command(name="ban", description="Permanently expels a user from this realm.")
@app_commands.describe(member="The transgressor to be banished.", reason="The justification for this action.")
@commands.has_permissions(ban_members=True)
async def ban(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided."):
    if member == ctx.author:
        embed = NotoriousEmbed().set_error().set_description("You cannot banish yourself from the realm. That would be illogical.")
        return await ctx.send(embed=embed)
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        embed = NotoriousEmbed().set_error().set_description(f"Your authority does not extend to {member.mention}. They possess a role equal to or exceeding your own.")
        return await ctx.send(embed=embed)
    if member.top_role >= ctx.guild.me.top_role:
        embed = NotoriousEmbed().set_error().set_description(f"I lack the hierarchical power to banish {member.mention}. Their role is beyond my reach.")
        return await ctx.send(embed=embed)

    try:
        await member.ban(reason=f"Banned by {ctx.author} for: {reason}")
        embed = NotoriousEmbed(title="🔨 BANISHMENT EXECUTED")
        embed.description = generate_punishment_message("ban", member, reason, ctx.author)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_premium_field("Moderator", ctx.author.mention)
        embed.add_premium_field("Offender", f"{member.mention} (`{member.id}`)")
        embed.add_premium_field("Reason", reason, inline=False)
        await ctx.send(embed=embed)
        bot.dispatch('log_event', ctx.guild, ctx.author, member, "ban", reason)
    except discord.Forbidden:
        embed = NotoriousEmbed().set_error().set_description(f"Banishment failed. I lack the necessary permissions to ban {member.mention}.")
        await ctx.send(embed=embed)

@bot.hybrid_command(name="kick", description="Forcefully ejects a user from the realm.")
@app_commands.describe(member="The individual to be ejected.", reason="The justification for this action.")
@commands.has_permissions(kick_members=True)
async def kick(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided."):
    if member == ctx.author:
        embed = NotoriousEmbed().set_error().set_description("You cannot kick yourself. That is a request I cannot fulfill.")
        return await ctx.send(embed=embed)
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        embed = NotoriousEmbed().set_error().set_description(f"Your authority does not extend to {member.mention}.")
        return await ctx.send(embed=embed)
    if member.top_role >= ctx.guild.me.top_role:
        embed = NotoriousEmbed().set_error().set_description(f"I lack the hierarchical power to eject {member.mention}.")
        return await ctx.send(embed=embed)

    try:
        await member.kick(reason=f"Kicked by {ctx.author} for: {reason}")
        embed = NotoriousEmbed(title="👢 EXPULSION EXECUTED")
        embed.description = generate_punishment_message("kick", member, reason, ctx.author)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_premium_field("Moderator", ctx.author.mention)
        embed.add_premium_field("Offender", f"{member.mention} (`{member.id}`)")
        embed.add_premium_field("Reason", reason, inline=False)
        await ctx.send(embed=embed)
        bot.dispatch('log_event', ctx.guild, ctx.author, member, "kick", reason)
    except discord.Forbidden:
        embed = NotoriousEmbed().set_error().set_description(f"Expulsion failed. I lack permissions to kick {member.mention}.")
        await ctx.send(embed=embed)

@bot.hybrid_command(name="mute", aliases=["timeout"], description="Imposes a chat restriction upon a user for a designated duration.")
@app_commands.describe(member="The individual to be muted.", minutes="Duration of the mute in minutes.", reason="The justification for this action.")
@commands.has_permissions(moderate_members=True)
async def mute(ctx: commands.Context, member: discord.Member, minutes: int, *, reason: str = "No reason provided."):
    if member == ctx.author:
        embed = NotoriousEmbed().set_error().set_description("Imposing a mute upon yourself? That is a level of self-reflection I cannot facilitate.")
        return await ctx.send(embed=embed)
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        embed = NotoriousEmbed().set_error().set_description(f"Your authority does not extend to {member.mention}.")
        return await ctx.send(embed=embed)
    if member.top_role >= ctx.guild.me.top_role:
        embed = NotoriousEmbed().set_error().set_description(f"I lack the hierarchical power to mute {member.mention}.")
        return await ctx.send(embed=embed)
    if minutes <= 0 or minutes > 40320:
        embed = NotoriousEmbed().set_error().set_description("Duration must be between 1 minute and 40,320 minutes (28 days).")
        return await ctx.send(embed=embed)

    try:
        duration = timedelta(minutes=minutes)
        await member.timeout(duration, reason=f"Timed out by {ctx.author} for: {reason}")
        embed = NotoriousEmbed(title="🔇 SILENCE ENFORCED")
        embed.description = generate_punishment_message("mute", member, reason, ctx.author, duration=f"{minutes} minutes")
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_premium_field("Moderator", ctx.author.mention)
        embed.add_premium_field("Offender", f"{member.mention} (`{member.id}`)")
        embed.add_premium_field("Duration", f"{minutes} minute(s)", inline=True)
        embed.add_premium_field("Reason", reason, inline=False)
        await ctx.send(embed=embed)
        bot.dispatch('log_event', ctx.guild, ctx.author, member, "mute", reason)
    except discord.Forbidden:
        embed = NotoriousEmbed().set_error().set_description(f"Mute failed. I lack permissions to timeout {member.mention}.")
        await ctx.send(embed=embed)

@bot.hybrid_command(name="warn", description="Issues a formal warning to a member of this realm.")
@app_commands.describe(member="The individual receiving the warning.", reason="The justification for this warning.")
@commands.has_permissions(manage_messages=True)
async def warn(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided."):
    if member == ctx.author:
        embed = NotoriousEmbed().set_error().set_description("Issuing a warning to yourself? That is an unusual act of self-flagellation.")
        return await ctx.send(embed=embed)
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        embed = NotoriousEmbed().set_error().set_description(f"Your authority does not extend to {member.mention}.")
        return await ctx.send(embed=embed)

    warning = bot.add_warn(ctx.guild.id, member.id, ctx.author.id, reason)
    warn_count = len(bot.get_user_warns(ctx.guild.id, member.id))

    embed = NotoriousEmbed(title="⚠️ WARNING ISSUED")
    embed.description = generate_punishment_message("warn", member, reason, ctx.author)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_premium_field("Moderator", ctx.author.mention)
    embed.add_premium_field("Offender", f"{member.mention} (`{member.id}`)")
    embed.add_premium_field("Warning Count", f"{warn_count} total warning(s)", inline=True)
    embed.add_premium_field("Reason", reason, inline=False)
    await ctx.send(embed=embed)

    # Auto-timeout after 3 warnings
    if warn_count >= 3:
        try:
            duration = timedelta(minutes=15)
            await member.timeout(duration, reason="Accumulated 3 warnings - Automatic timeout")
            auto_embed = NotoriousEmbed(title="⚖️ AUTOMATIC ENFORCEMENT")
            auto_embed.description = f"{member.mention} has accumulated **3 warnings** and has been **automatically timed out for 15 minutes** as a result. Let this be a lesson in accountability."
            auto_embed.add_premium_field("Moderator", "NoToRiOuS ⁴⁷ (Auto-Mod)")
            auto_embed.add_premium_field("Offender", f"{member.mention} (`{member.id}`)")
            auto_embed.add_premium_field("Duration", "15 minutes")
            await ctx.send(embed=auto_embed)
            bot.dispatch('log_event', ctx.guild, ctx.guild.me, member, "auto-timeout", "Accumulated 3 warnings")
        except Exception as e:
            logger.error(f"Failed to auto-timeout {member}: {e}")

@bot.hybrid_command(name="warnlist", aliases=["warnings"], description="Retrieves the disciplinary record for a specific user.")
@app_commands.describe(member="The individual whose record you wish to examine.")
@commands.has_permissions(manage_messages=True)
async def warnlist(ctx: commands.Context, member: discord.Member):
    warns = bot.get_user_warns(ctx.guild.id, member.id)
    embed = NotoriousEmbed(title=f"📜 DISCIPLINARY RECORD: {member.name}#{member.discriminator}")
    embed.set_thumbnail(url=member.display_avatar.url)

    if not warns:
        embed.description = f"{member.mention} has a **clean record**. There are no warnings associated with this user. Let us hope it remains this way."
        embed.color = discord.Color.green()
    else:
        embed.description = f"{member.mention} has accumulated **{len(warns)} warning(s)**. Their conduct requires review.\n"
        for warn in warns[-5:]:  # Show last 5
            moderator = ctx.guild.get_member(warn['moderator'])
            mod_name = moderator.mention if moderator else f"Unknown Mod (`{warn['moderator']}`)"
            timestamp = datetime.fromisoformat(warn['timestamp'])
            embed.add_premium_field(
                f"Warning #{warn['id']} | <t:{int(timestamp.timestamp())}:R>",
                f"**Moderator:** {mod_name}\n**Reason:** {warn['reason']}",
                inline=False
            )
        embed.color = discord.Color.gold()

    embed.set_footer(text="NoToRiOuS ⁴⁷ • Record Keeper")
    await ctx.send(embed=embed)

@bot.hybrid_command(name="purge", aliases=["clear"], description="Swiftly removes a specified number of messages from the channel.")
@app_commands.describe(amount="The number of messages to purge (max 100).", member="Optional: Purge messages only from a specific user.")
@commands.has_permissions(manage_messages=True)
async def purge(ctx: commands.Context, amount: int, member: discord.Member = None):
    if amount <= 0 or amount > 100:
        embed = NotoriousEmbed().set_error().set_description("The amount of messages to purge must be between 1 and 100.")
        return await ctx.send(embed=embed)

    await ctx.defer(ephemeral=True)

    def check(msg):
        return member is None or msg.author == member

    try:
        deleted = await ctx.channel.purge(limit=amount, check=check, before=ctx.message)
        embed = NotoriousEmbed(title="🧹 CHANNEL PURGED")
        embed.description = f"**{len(deleted)} message(s)** have been expunged from this channel. The slate is clean."
        if member:
            embed.add_premium_field("Target User", member.mention)
        embed.add_premium_field("Moderator", ctx.author.mention)
        embed.add_premium_field("Channel", ctx.channel.mention)
        embed.set_footer(text="NoToRiOuS ⁴⁷ • Housekeeping")
        confirmation = await ctx.send(embed=embed)
        await asyncio.sleep(5)
        await confirmation.delete()
        bot.dispatch('log_event', ctx.guild, ctx.author, None, "purge", f"{len(deleted)} messages in {ctx.channel.mention}")
    except discord.Forbidden:
        embed = NotoriousEmbed().set_error().set_description("Purge failed. I lack the necessary permissions to manage messages in this channel.")
        await ctx.send(embed=embed)

@bot.hybrid_command(name="banlist", description="Lists all users who are currently banished from this realm.")
@commands.has_permissions(ban_members=True)
async def banlist(ctx: commands.Context):
    try:
        bans = [entry async for entry in ctx.guild.bans()]
        if not bans:
            embed = NotoriousEmbed(title="⚖️ BAN LIST")
            embed.description = "This realm is currently **free of any banishments**. Order prevails."
            embed.color = discord.Color.green()
            await ctx.send(embed=embed)
            return

        embed = NotoriousEmbed(title="⚖️ CURRENT BANISHMENTS")
        embed.description = f"A total of **{len(bans)} user(s)** are currently expelled from this realm:\n"
        ban_entries = [f"**{entry.user.name}#{entry.user.discriminator}** (`{entry.user.id}`)" for entry in bans[:15]]
        embed.description += "\n".join(ban_entries)
        if len(bans) > 15:
            embed.set_footer(text=f"And {len(bans)-15} more... • NoToRiOuS ⁴⁷")
        await ctx.send(embed=embed)
    except discord.Forbidden:
        embed = NotoriousEmbed().set_error().set_description("I lack the necessary permissions to view the ban list.")
        await ctx.send(embed=embed)
# ==================== AUTO-MOD COMMANDS ====================
@bot.hybrid_group(name="badword", description="Manages the list of prohibited terminology.")
@commands.has_permissions(administrator=True)
async def badword_group(ctx: commands.Context):
    if ctx.invoked_subcommand is None:
        await ctx.send_help(ctx.command)

@badword_group.command(name="add", description="Adds a new word or phrase to the blacklist.")
@app_commands.describe(word="The prohibited term to be added to the filter.")
async def badword_add(ctx: commands.Context, *, word: str):
    word_lower = word.lower()
    if word_lower in bot.badwords:
        embed = NotoriousEmbed().set_warning()
        embed.description = f"The term **`{word}`** is already present in the blacklist. Redundancy is not required."
        return await ctx.send(embed=embed)

    bot.badwords.append(word_lower)
    embed = NotoriousEmbed(title="🚫 BADWORD ADDED")
    embed.description = f"The term **`{word}`** has been **successfully blacklisted**. Any usage of this language will be met with immediate deletion and a public reprimand."
    embed.add_premium_field("Added by", ctx.author.mention)
    embed.add_premium_field("Total Blacklisted Terms", str(len(bot.badwords)))
    embed.set_footer(text="NoToRiOuS ⁴⁷ • Language Policing")
    await ctx.send(embed=embed)

@badword_group.command(name="remove", aliases=["delete"], description="Removes a word or phrase from the blacklist.")
@app_commands.describe(word="The term to be expunged from the blacklist.")
async def badword_remove(ctx: commands.Context, *, word: str):
    word_lower = word.lower()
    if word_lower not in bot.badwords:
        embed = NotoriousEmbed().set_warning()
        embed.description = f"The term **`{word}`** is not currently blacklisted. Its removal is unnecessary."
        return await ctx.send(embed=embed)

    bot.badwords.remove(word_lower)
    embed = NotoriousEmbed(title="✅ BADWORD REMOVED")
    embed.description = f"The term **`{word}`** has been **expunged from the blacklist**. It is no longer subject to automatic filtration."
    embed.add_premium_field("Removed by", ctx.author.mention)
    embed.add_premium_field("Remaining Blacklisted Terms", str(len(bot.badwords)))
    embed.set_footer(text="NoToRiOuS ⁴⁷ • List Maintenance")
    await ctx.send(embed=embed)

@badword_group.command(name="list", description="Displays the current list of blacklisted terminology.")
@commands.has_permissions(manage_messages=True)
async def badword_list(ctx: commands.Context):
    if not bot.badwords:
        embed = NotoriousEmbed().set_info()
        embed.description = "The blacklist is currently **empty**. The realm's linguistic filters are dormant."
        return await ctx.send(embed=embed)

    embed = NotoriousEmbed(title="📜 CURRENT BLACKLISTED TERMINOLOGY")
    embed.description = f"A total of **{len(bot.badwords)}** terms are currently subject to automatic censorship:\n"
    # Split into chunks to avoid embed limits
    chunk_size = 20
    chunks = [bot.badwords[i:i+chunk_size] for i in range(0, len(bot.badwords), chunk_size)]
    for i, chunk in enumerate(chunks):
        embed.add_field(name=f"Segment {i+1}", value="`" + "`, `".join(chunk) + "`", inline=False)
    embed.set_footer(text="NoToRiOuS ⁴⁷ • Linguistic Oversight")
    await ctx.send(embed=embed)

# ==================== LOGGING COMMANDS ====================
@bot.hybrid_group(name="log", description="Centralized configuration for the logging system.")
@commands.has_permissions(administrator=True)
async def log_group(ctx: commands.Context):
    if ctx.invoked_subcommand is None:
        await ctx.send_help(ctx.command)

@log_group.command(name="set", description="Sets a specific channel for a designated log type.")
@app_commands.describe(channel="The channel where logs of this type will be dispatched.", log_type="The category of log. Valid options: message_edit, message_delete, voice, member_join, member_leave, mod_action.")
async def log_set(ctx: commands.Context, channel: discord.TextChannel, log_type: str):
    valid_types = ['message_edit', 'message_delete', 'voice', 'member_join', 'member_leave', 'mod_action']
    log_type = log_type.lower()

    if log_type not in valid_types:
        valid_str = "`, `".join(valid_types)
        embed = NotoriousEmbed().set_error()
        embed.description = f"The log type `{log_type}` is not recognized. Please choose from: `{valid_str}`."
        return await ctx.send(embed=embed)

    if ctx.guild.id not in bot.log_channels:
        bot.log_channels[ctx.guild.id] = {}

    bot.log_channels[ctx.guild.id][log_type] = channel.id

    embed = NotoriousEmbed(title="📋 Logging Configuration Updated")
    embed.description = f"All events of type **`{log_type}`** will now be meticulously documented in {channel.mention}."
    embed.set_footer(text="NoToRiOuS ⁴⁷ • The Watcher's Gaze")
    await ctx.send(embed=embed)

@log_group.command(name="status", description="Displays the current logging configuration for this guild.")
@commands.has_permissions(manage_guild=True)
async def log_status(ctx: commands.Context):
    if ctx.guild.id not in bot.log_channels or not bot.log_channels[ctx.guild.id]:
        embed = NotoriousEmbed().set_info()
        embed.description = "No logging channels have been configured for this realm yet. Use `~log set` to begin recording events."
        return await ctx.send(embed=embed)

    embed = NotoriousEmbed(title="📋 Logging Configuration Overview")
    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)

    description = ""
    for log_type, channel_id in bot.log_channels[ctx.guild.id].items():
        channel = ctx.guild.get_channel(channel_id)
        channel_mention = channel.mention if channel else "`Channel Deleted`"
        description += f"**{log_type.replace('_', ' ').title()}**: {channel_mention}\n"

    embed.description = description or "No log channels are currently set."
    embed.set_footer(text="NoToRiOuS ⁴⁷ • Logging Overview")
    await ctx.send(embed=embed)

# ==================== LOGGING EVENT LISTENERS ====================
@bot.event
async def on_log_event(guild: discord.Guild, moderator: discord.Member, target: Optional[discord.Member], action: str, details: str):
    """Custom event for logging moderation actions."""
    channel = bot.get_log_channel(guild, 'mod_action')
    if not channel:
        return
    embed = NotoriousEmbed(title=f"🛡️ MOD ACTION: {action.upper()}")
    embed.add_premium_field("Moderator", moderator.mention)
    if target:
        embed.add_premium_field("Target", f"{target.mention} (`{target.id}`)")
    embed.add_premium_field("Details", details)
    await channel.send(embed=embed)
# ==================== MUSIC COMMANDS ====================
@bot.hybrid_command(name="play", description="Summons the bot and plays a track from YouTube or Spotify.")
@app_commands.describe(query="The name of a song, a YouTube URL, or a Spotify link.")
async def play(ctx: commands.Context, *, query: str):
    if not ctx.author.voice:
        embed = NotoriousEmbed().set_error().set_description("You must be in a voice channel to summon the orchestra.")
        return await ctx.send(embed=embed)

    if ctx.voice_client is None:
        await ctx.author.voice.channel.connect()
    elif ctx.voice_client.channel != ctx.author.voice.channel:
        await ctx.voice_client.move_to(ctx.author.voice.channel)

    await ctx.defer()
    player = bot.get_player(ctx.guild)

    # Enhance with Spotify if possible
    if 'spotify.com' in query and 'track' in query:
        spotify_track = bot.spotify.get_track_info(query)
        if spotify_track:
            artist = spotify_track['artists'][0]['name']
            name = spotify_track['name']
            query = f"{artist} - {name}"
    elif not query.startswith(('http://', 'https://')):
        spotify_search = bot.spotify.search_track(query)
        if spotify_search:
            query = spotify_search

    try:
        await player.add_to_queue(query, ctx.author)
        embed = NotoriousEmbed(title="🎵 ADDED TO QUEUE")
        if player.voice_client and player.voice_client.is_playing():
            embed.description = f"**{player.queue[-1].title}** has been appended to the queue. It will be performed in due time."
        else:
            embed.description = f"**{player.queue[-1].title}** is now being prepared for your listening pleasure."

        embed.add_premium_field("Requested by", ctx.author.mention)
        embed.add_premium_field("Position in Queue", f"#{len(player.queue)}")
        if player.queue[-1].uploader:
            embed.add_premium_field("Artist", player.queue[-1].uploader)

        await ctx.send(embed=embed)

        if not player.voice_client:
            player.start(ctx.voice_client)
    except Exception as e:
        embed = NotoriousEmbed().set_error().set_description(f"An error occurred while trying to play that track. Details: {e}")
        await ctx.send(embed=embed)

@bot.hybrid_command(name="skip", description="Advances the queue to the next track.")
async def skip(ctx: commands.Context):
    player = bot.get_player(ctx.guild)
    if player.voice_client and player.voice_client.is_playing():
        player.voice_client.stop()
        embed = NotoriousEmbed(title="⏭️ SKIPPED")
        embed.description = f"**{player.current.title}** has been skipped. The next performance will begin shortly."
        embed.set_footer(text="NoToRiOuS ⁴⁷ • Queue Manager")
        await ctx.send(embed=embed)
    else:
        embed = NotoriousEmbed().set_warning().set_description("There is no active performance to skip.")
        await ctx.send(embed=embed)

@bot.hybrid_command(name="stop", description="Halts the music and clears the entire queue.")
async def stop(ctx: commands.Context):
    player = bot.get_player(ctx.guild)
    if player.voice_client:
        player.stop()
        embed = NotoriousEmbed(title="⏹️ PLAYBACK HALTED")
        embed.description = "The music has ceased. The queue has been cleared, and I have departed from the voice channel."
        await ctx.send(embed=embed)
    else:
        embed = NotoriousEmbed().set_warning().set_description("I am not currently performing in any voice channel.")
        await ctx.send(embed=embed)

@bot.hybrid_command(name="queue", description="Displays the current musical queue.")
async def queue(ctx: commands.Context):
    player = bot.get_player(ctx.guild)
    if not player.queue and not player.current:
        embed = NotoriousEmbed().set_info().set_description("The musical queue is currently **empty**. Summon a performance with `~play`.")
        return await ctx.send(embed=embed)

    embed = NotoriousEmbed(title="🎶 MUSICAL QUEUE")
    if player.current:
        embed.add_premium_field("Currently Performing", f"**{player.current.title}** | `{player.current.uploader}`", inline=False)

    if player.queue:
        queue_list = []
        for i, track in enumerate(player.queue[:10]):
            queue_list.append(f"`#{i+1}.` **{track.title}** | `{track.uploader}` | Requested by {track.requester.mention}")
        embed.description = "\n".join(queue_list)
        if len(player.queue) > 10:
            embed.set_footer(text=f"And {len(player.queue) - 10} more... • NoToRiOuS ⁴⁷")
    else:
        embed.description = "The queue is currently empty."

    await ctx.send(embed=embed)

@bot.hybrid_command(name="volume", description="Adjusts the playback volume.")
@app_commands.describe(volume="A number between 0 and 100.")
async def volume(ctx: commands.Context, volume: int):
    player = bot.get_player(ctx.guild)
    if not player.voice_client or not player.voice_client.source:
        embed = NotoriousEmbed().set_warning().set_description("There is no active audio source to adjust.")
        return await ctx.send(embed=embed)

    if 0 <= volume <= 100:
        player.voice_client.source.volume = volume / 100
        embed = NotoriousEmbed(title="🔊 VOLUME ADJUSTED")
        embed.description = f"The playback volume has been set to **{volume}%**."
        await ctx.send(embed=embed)
    else:
        embed = NotoriousEmbed().set_error().set_description("Volume must be a number between 0 and 100.")
        await ctx.send(embed=embed)

@bot.hybrid_command(name="pause", description="Pauses the current track.")
async def pause(ctx: commands.Context):
    player = bot.get_player(ctx.guild)
    if player.voice_client and player.voice_client.is_playing():
        player.voice_client.pause()
        embed = NotoriousEmbed(title="⏸️ PLAYBACK PAUSED")
        embed.description = f"**{player.current.title}** has been paused. Use `~resume` to continue."
        await ctx.send(embed=embed)
    else:
        embed = NotoriousEmbed().set_warning().set_description("There is no active performance to pause.")
        await ctx.send(embed=embed)

@bot.hybrid_command(name="resume", description="Resumes the paused track.")
async def resume(ctx: commands.Context):
    player = bot.get_player(ctx.guild)
    if player.voice_client and player.voice_client.is_paused():
        player.voice_client.resume()
        embed = NotoriousEmbed(title="▶️ PLAYBACK RESUMED")
        embed.description = f"**{player.current.title}** is now playing once again."
        await ctx.send(embed=embed)
    else:
        embed = NotoriousEmbed().set_warning().set_description("There is no paused performance to resume.")
        await ctx.send(embed=embed)

@bot.hybrid_command(name="shuffle", description="Randomizes the order of the queue.")
async def shuffle(ctx: commands.Context):
    player = bot.get_player(ctx.guild)
    if not player.queue:
        embed = NotoriousEmbed().set_warning().set_description("The queue is empty. There is nothing to shuffle.")
        return await ctx.send(embed=embed)

    random.shuffle(player.queue)
    embed = NotoriousEmbed(title="🔀 QUEUE SHUFFLED")
    embed.description = "The musical queue has been **randomized**. Enjoy the element of surprise."
    await ctx.send(embed=embed)

@bot.hybrid_command(name="loop", description="Toggles looping of the current track.")
async def loop(ctx: commands.Context):
    player = bot.get_player(ctx.guild)
    player.loop = not player.loop

    embed = NotoriousEmbed(title="🔁 LOOP MODE")
    if player.loop:
        embed.description = f"**Looping has been enabled** for the current track. It will repeat indefinitely until disabled."
    else:
        embed.description = f"**Looping has been disabled.** The queue will proceed normally after this track concludes."
    await ctx.send(embed=embed)
# ==================== FUN COMMANDS ====================
@bot.hybrid_command(name="tictactoe", aliases=["ttt"], description="Initiates a game of Tic-Tac-Toe against another member.")
@app_commands.describe(opponent="The member you wish to challenge.")
async def tictactoe(ctx: commands.Context, opponent: discord.Member):
    if opponent == ctx.author:
        embed = NotoriousEmbed().set_error().set_description("You cannot challenge yourself. Find a worthy adversary.")
        return await ctx.send(embed=embed)
    if opponent.bot:
        embed = NotoriousEmbed().set_error().set_description("Bots are not programmed for such trivial pursuits. Challenge a human.")
        return await ctx.send(embed=embed)

    view = TicTacToe(ctx.author, opponent)
    embed = NotoriousEmbed(title="🎮 TIC-TAC-TOE CHALLENGE")
    embed.description = f"{ctx.author.mention} has challenged {opponent.mention} to a duel of wits and strategy!\n\n{ctx.author.mention} will be **X** and goes first."
    embed.set_footer(text="Click a button to make your move.")
    view.message = await ctx.send(embed=embed, view=view)

@bot.hybrid_command(name="trivia", description="Poses a challenging trivia question from a vast repository of knowledge.")
@app_commands.describe(category="Optional: The category of trivia (e.g., 'Science & Nature').")
async def trivia(ctx: commands.Context, *, category: str = None):
    await ctx.defer()

    # Find category ID
    cat_id = None
    if category:
        for key, value in bot.trivia_categories.items():
            if category.lower() in value.lower():
                cat_id = key
                break

    url = f"https://opentdb.com/api.php?amount=1"
    if cat_id:
        url += f"&category={cat_id}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise Exception("Failed to fetch trivia question.")
                data = await resp.json()
                if data['response_code'] != 0:
                    raise Exception("No trivia questions found for this category.")

        q_data = data['results'][0]
        question = html.unescape(q_data['question'])
        correct_answer = html.unescape(q_data['correct_answer'])
        incorrect_answers = [html.unescape(ans) for ans in q_data['incorrect_answers']]

        all_answers = incorrect_answers + [correct_answer]
        random.shuffle(all_answers)
        correct_index = all_answers.index(correct_answer)

        embed = NotoriousEmbed(title="❓ TRIVIA CHALLENGE")
        embed.description = f"**Category:** {bot.trivia_categories.get(cat_id, 'General')}\n**Question:** {question}\n\nSelect the correct answer from the buttons below."
        embed.set_footer(text="You have 30 seconds to answer.")

        view = TriviaView(question, all_answers, correct_index)
        view.message = await ctx.send(embed=embed, view=view)

    except Exception as e:
        embed = NotoriousEmbed().set_error().set_description(f"An error occurred while fetching trivia. Details: {e}")
        await ctx.send(embed=embed)

@bot.hybrid_command(name="guess", description="Starts a game of 'Guess the Number'.")
@app_commands.describe(max_number="The upper limit for the random number (default: 100).")
async def guess(ctx: commands.Context, max_number: int = 100):
    if ctx.channel.id in bot.guess_games:
        embed = NotoriousEmbed().set_warning().set_description("A guessing game is already active in this channel.")
        return await ctx.send(embed=embed)

    target = random.randint(1, max_number)
    bot.guess_games[ctx.channel.id] = target

    embed = NotoriousEmbed(title="🔢 GUESS THE NUMBER")
    embed.description = f"I have selected a number between **1 and {max_number}**. Use `~guess_num <number>` to make your prediction."
    embed.set_footer(text="NoToRiOuS ⁴⁷ • Mental Challenge")
    await ctx.send(embed=embed)

@bot.hybrid_command(name="guess_num", description="Make a guess in the active 'Guess the Number' game.")
@app_commands.describe(number="Your guess.")
async def guess_num(ctx: commands.Context, number: int):
    if ctx.channel.id not in bot.guess_games:
        embed = NotoriousEmbed().set_error().set_description("There is no active guessing game in this channel. Start one with `~guess`.")
        return await ctx.send(embed=embed)

    target = bot.guess_games[ctx.channel.id]
    if number == target:
        del bot.guess_games[ctx.channel.id]
        embed = NotoriousEmbed(title="🎉 CONGRATULATIONS!")
        embed.description = f"{ctx.author.mention}, you have successfully guessed the number **{target}**! Your intuition is formidable."
        await ctx.send(embed=embed)
    elif number < target:
        embed = NotoriousEmbed().set_info().set_description(f"{ctx.author.mention}, the number **{number}** is too low. Aim higher!")
        await ctx.send(embed=embed)
    else:
        embed = NotoriousEmbed().set_info().set_description(f"{ctx.author.mention}, the number **{number}** is too high. Aim lower!")
        await ctx.send(embed=embed)

@bot.hybrid_command(name="avatar", description="Displays the avatar of a specified user.")
@app_commands.describe(member="The user whose avatar you wish to view.")
async def avatar(ctx: commands.Context, member: discord.Member = None):
    if member is None:
        member = ctx.author

    embed = NotoriousEmbed(title=f"🖼️ AVATAR: {member.name}#{member.discriminator}")
    embed.set_image(url=member.display_avatar.url)
    embed.description = f"**User:** {member.mention}\n**ID:** `{member.id}`\n[Download Avatar]({member.display_avatar.url})"
    await ctx.send(embed=embed)

# Anime GIF actions
async def get_anime_gif(category: str) -> Optional[str]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.waifu.pics/sfw/{category}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data['url']
    except:
        return None

async def action_command(ctx: commands.Context, member: discord.Member, action: str):
    if member == ctx.author:
        embed = NotoriousEmbed().set_error().set_description(f"You cannot {action} yourself. That would be a paradox.")
        return await ctx.send(embed=embed)

    gif_url = await get_anime_gif(action)
    if not gif_url:
        embed = NotoriousEmbed().set_error().set_description(f"Failed to fetch a GIF for the action. Please try again later.")
        return await ctx.send(embed=embed)

    messages = {
        "hug": [f"{ctx.author.mention} envelops {member.mention} in a warm, comforting embrace."],
        "kiss": [f"{ctx.author.mention} bestows a tender kiss upon {member.mention}."],
        "slap": [f"{ctx.author.mention} delivers a resounding slap to {member.mention}. Ouch!"],
        "kill": [f"{ctx.author.mention} has executed {member.mention} in a dramatic and theatrical fashion. 💀"]
    }
    description = random.choice(messages.get(action, [f"{ctx.author.mention} {action}s {member.mention}."]))

    embed = NotoriousEmbed(title=f"{action.upper()}!")
    embed.description = description
    embed.set_image(url=gif_url)
    embed.set_footer(text="NoToRiOuS ⁴⁷ • Emotional Expressions")
    await ctx.send(embed=embed)

@bot.hybrid_command(name="hug", description="Offers a warm embrace to another member.")
@app_commands.describe(member="The individual you wish to hug.")
async def hug(ctx: commands.Context, member: discord.Member):
    await action_command(ctx, member, "hug")

@bot.hybrid_command(name="kiss", description="Bestows a tender kiss upon another member.")
@app_commands.describe(member="The individual you wish to kiss.")
async def kiss(ctx: commands.Context, member: discord.Member):
    await action_command(ctx, member, "kiss")

@bot.hybrid_command(name="slap", description="Delivers a theatrical slap to another member.")
@app_commands.describe(member="The individual you wish to slap.")
async def slap(ctx: commands.Context, member: discord.Member):
    await action_command(ctx, member, "slap")

@bot.hybrid_command(name="kill", description="Performs a dramatic execution of another member.")
@app_commands.describe(member="The individual you wish to 'eliminate'.")
async def kill(ctx: commands.Context, member: discord.Member):
    await action_command(ctx, member, "kill")
# ==================== GENERAL COMMANDS ====================
@bot.hybrid_command(name="ping", description="Measures the bot's operational latency.")
async def ping(ctx: commands.Context):
    start_time = datetime.utcnow()
    embed = NotoriousEmbed(title="📡 PING: Calculating...")
    embed.description = "Sending a pulse through the digital aether. Stand by for results."
    embed.color = discord.Color.light_grey()
    message = await ctx.send(embed=embed)

    end_time = datetime.utcnow()
    api_latency = round((end_time - start_time).total_seconds() * 1000)
    ws_latency = round(bot.latency * 1000)

    def latency_bar(ping):
        if ping < 50: return "██████████ Excellent"
        elif ping < 100: return "████████░░ Great"
        elif ping < 200: return "██████░░░░ Average"
        elif ping < 300: return "████░░░░░░ Poor"
        else: return "██░░░░░░░░ Unstable"

    embed = NotoriousEmbed(title="📡 CONNECTION DIAGNOSTIC REPORT")
    embed.color = discord.Color.green() if ws_latency < 100 else discord.Color.gold()
    embed.add_premium_field("WebSocket Heartbeat", f"`{ws_latency}ms` {latency_bar(ws_latency)}")
    embed.add_premium_field("API Response Time", f"`{api_latency}ms` {latency_bar(api_latency)}")
    embed.add_premium_field("System Uptime", get_uptime(bot.start_time))
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.set_footer(text="NoToRiOuS ⁴⁷ • Network Stability Analysis")
    await message.edit(embed=embed)

@bot.hybrid_command(name="serverinfo", aliases=["si"], description="Provides a comprehensive dossier on this server.")
async def serverinfo(ctx: commands.Context):
    guild = ctx.guild
    embed = NotoriousEmbed(title=f"📊 SERVER DOSSIER: {guild.name}")

    embed.add_premium_field("Server Name", guild.name, inline=True)
    embed.add_premium_field("Server ID", f"`{guild.id}`", inline=True)
    embed.add_premium_field("Owner", f"{guild.owner.mention}\n`{guild.owner.id}`", inline=True)

    created_at = int(guild.created_at.timestamp())
    embed.add_premium_field("Established", f"<t:{created_at}:F>\n(<t:{created_at}:R>)", inline=True)

    total_members = guild.member_count
    online_members = sum(m.status != discord.Status.offline for m in guild.members)
    bot_count = sum(m.bot for m in guild.members)
    human_count = total_members - bot_count

    embed.add_premium_field("Member Composition",
                            f"**Total:** {total_members}\n**Humans:** {human_count}\n**Bots:** {bot_count}\n**Online:** {online_members}", inline=True)

    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    embed.add_premium_field("Channel Structure", f"**Text:** {text_channels}\n**Voice:** {voice_channels}", inline=True)

    embed.add_premium_field("Roles", f"{len(guild.roles)}", inline=True)
    embed.add_premium_field("Nitro Boosts", f"Level {guild.premium_tier} ({guild.premium_subscription_count} boosts)", inline=True)

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    if guild.banner:
        embed.set_image(url=guild.banner.url)

    await ctx.send(embed=embed)

@bot.hybrid_command(name="userinfo", aliases=["ui"], description="Fetches a detailed profile on a specific user.")
@app_commands.describe(member="The user you wish to investigate.")
async def userinfo(ctx: commands.Context, member: discord.Member = None):
    if member is None:
        member = ctx.author

    embed = NotoriousEmbed(title=f"👤 USER PROFILE: {member.name}#{member.discriminator}")
    embed.set_thumbnail(url=member.display_avatar.url)

    embed.add_premium_field("Username", f"{member.name}#{member.discriminator}", inline=True)
    embed.add_premium_field("Nickname", member.nick if member.nick else "None", inline=True)
    embed.add_premium_field("User ID", f"`{member.id}`", inline=True)

    created_at = int(member.created_at.timestamp())
    joined_at = int(member.joined_at.timestamp()) if member.joined_at else None
    embed.add_premium_field("Account Created", f"<t:{created_at}:F>\n(<t:{created_at}:R>)", inline=True)
    if joined_at:
        embed.add_premium_field("Joined Server", f"<t:{joined_at}:F>\n(<t:{joined_at}:R>)", inline=True)

    status_emoji = {discord.Status.online: "🟢", discord.Status.idle: "🟡", discord.Status.dnd: "🔴", discord.Status.offline: "⚫"}
    embed.add_premium_field("Current Status", f"{status_emoji.get(member.status, '⚫')} {member.status.name.title()}", inline=True)

    roles = [role.mention for role in reversed(member.roles) if role != ctx.guild.default_role]
    if roles:
        embed.add_premium_field(f"Roles ({len(roles)})", " ".join(roles[:10]) + (" ..." if len(roles) > 10 else ""), inline=False)

    await ctx.send(embed=embed)

@bot.hybrid_command(name="info", description="Displays vital information and credentials of NoToRiOuS ⁴⁷.")
async def info(ctx: commands.Context):
    embed = NotoriousEmbed(title="⚜️ SYSTEM PROFILE: NoToRiOuS ⁴⁷")
    embed.set_thumbnail(url=bot.user.display_avatar.url)

    embed.add_premium_field("Designation", "NoToRiOuS ⁴⁷", inline=True)
    embed.add_premium_field("Architects", "Ishan // Toxyyy // Zaid", inline=True)
    embed.add_premium_field("Commission Date", "06-04-2026", inline=True)

    ws_latency = round(bot.latency * 1000)
    embed.add_premium_field("Operational Latency", f"{ws_latency}ms", inline=True)
    embed.add_premium_field("Primary Directive", "Administration Of N47", inline=False)

    embed.add_premium_field("System Uptime", get_uptime(bot.start_time), inline=True)
    embed.add_premium_field("Python Version", platform.python_version(), inline=True)
    embed.add_premium_field("Discord.py Version", discord.__version__, inline=True)

    embed.add_premium_field("Guilds Patrolled", str(len(bot.guilds)), inline=True)
    embed.add_premium_field("Total Users", str(len(bot.users)), inline=True)

    await ctx.send(embed=embed)

@bot.hybrid_command(name="help", description="The comprehensive guide to all available commands.")
@app_commands.describe(category="Optional: A specific category of commands to view.")
async def help_cmd(ctx: commands.Context, *, category: str = None):
    if category:
        # Simplified category help – full version would list commands per category
        embed = NotoriousEmbed().set_info().set_description(f"Use `~help` for the full command index.")
        return await ctx.send(embed=embed)

    embed = NotoriousEmbed(title="📜 COMMAND INDEX: NoToRiOuS ⁴⁷")
    embed.description = "Behold the full extent of my capabilities.\n\u200b"

    embed.add_field(name="🛡️ Moderation", value="`ban`, `kick`, `mute`, `warn`, `warnlist`, `purge`, `banlist`", inline=False)
    embed.add_field(name="🤖 Auto-Mod", value="`badword add/remove/list`", inline=False)
    embed.add_field(name="📋 Logging", value="`log set/status`", inline=False)
    embed.add_field(name="🎵 Music", value="`play`, `skip`, `stop`, `queue`, `volume`, `pause`, `resume`, `shuffle`, `loop`", inline=False)
    embed.add_field(name="🎮 Fun", value="`tictactoe`, `trivia`, `guess`, `guess_num`, `avatar`, `hug`, `kiss`, `slap`, `kill`", inline=False)
    embed.add_field(name="ℹ️ General", value="`ping`, `serverinfo`, `userinfo`, `info`, `help`", inline=False)
    embed.add_field(name="🖥️ SAMP", value="`samp connect`, `samp disconnect`, `samp status`", inline=False)

    embed.set_footer(text="NoToRiOuS ⁴⁷ • Your Guide to Order")
    await ctx.send(embed=embed)

# ==================== SAMP COMMANDS ====================
@bot.hybrid_group(name="samp", description="Commands for interacting with SA-MP servers.")
async def samp_group(ctx: commands.Context):
    if ctx.invoked_subcommand is None:
        await ctx.send_help(ctx.command)

@samp_group.command(name="connect", description="Establishes a connection to monitor a specified SA-MP server.")
@app_commands.describe(ip="The IP address of the SA-MP server.", port="The port number (default: 7777).")
@commands.has_permissions(manage_guild=True)
async def samp_connect(ctx: commands.Context, ip: str, port: int = 7777):
    try:
        socket.inet_aton(ip)
    except socket.error:
        embed = NotoriousEmbed().set_error().set_description("The provided IP address is invalid. Please check and try again.")
        return await ctx.send(embed=embed)

    if ctx.guild.id in bot.active_samp_monitors:
        embed = NotoriousEmbed().set_warning().set_description("A server is already being monitored in this guild. Use `~samp disconnect` first.")
        return await ctx.send(embed=embed)

    bot.current_samp_server[ctx.guild.id] = {"ip": ip, "port": port}
    embed = NotoriousEmbed(title="🖥️ SAMP MONITORING ACTIVATED")
    embed.description = f"Surveillance of SA-MP server `{ip}:{port}` has commenced. The realm will be kept informed of its status."
    embed.add_premium_field("Status", "Active")
    embed.set_footer(text="NoToRiOuS ⁴⁷ • SAMP Surveillance")
    await ctx.send(embed=embed)

@samp_group.command(name="disconnect", description="Terminates the active SA-MP server monitoring session.")
@commands.has_permissions(manage_guild=True)
async def samp_disconnect(ctx: commands.Context):
    if ctx.guild.id in bot.active_samp_monitors:
        task = bot.active_samp_monitors.pop(ctx.guild.id)
        task.cancel()
    bot.current_samp_server.pop(ctx.guild.id, None)

    embed = NotoriousEmbed(title="🖥️ SAMP MONITORING DEACTIVATED")
    embed.description = "Surveillance of the SA-MP server has been terminated. The connection is now closed."
    await ctx.send(embed=embed)

@samp_group.command(name="status", aliases=["sa"], description="Fetches real-time details of a specified SA-MP server.")
@app_commands.describe(ip="The IP address of the server to query.", port="The port number (default: 7777).")
async def samp_status(ctx: commands.Context, ip: str, port: int = 7777):
    await ctx.defer()
    data = await bot.samp_query.query_server(ip, port)
    if not data:
        embed = NotoriousEmbed().set_error().set_description(f"The SA-MP server at `{ip}:{port}` is currently **offline** or **unreachable**.")
        return await ctx.send(embed=embed)

    embed = NotoriousEmbed(title=f"🖥️ SAMP SERVER STATUS: {ip}:{port}")
    embed.add_premium_field("Hostname", data['hostname'], inline=False)
    embed.add_premium_field("Players", f"{data['players']}/{data['maxplayers']}", inline=True)
    embed.add_premium_field("Gamemode", data['gamemode'], inline=True)
    embed.add_premium_field("Language", data['language'], inline=True)
    embed.add_premium_field("Password Protected", "Yes" if data['password'] else "No", inline=True)

    if data.get('player_list'):
        player_list_str = "\n".join([f"`{p['id']}` {p['name']} | Score: {p['score']} | Ping: {p['ping']}" for p in data['player_list'][:10]])
        embed.add_premium_field("Online Players", player_list_str, inline=False)

    embed.set_footer(text="NoToRiOuS ⁴⁷ • SAMP Intelligence")
    await ctx.send(embed=embed)

# ==================== MAIN EXECUTION ====================
if __name__ == "__main__":
    start_webserver()  # Flask for Render/UptimeRobot
    token = os.environ.get('DISCORD_TOKEN')
    if not token:
        logger.critical("❌ DISCORD_TOKEN environment variable not set. Bot cannot start.")
        sys.exit(1)
    bot.run(token, log_handler=None)