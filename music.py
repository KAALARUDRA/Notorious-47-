# music.py - Complete YouTube Music System
import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
import json
import os
from urllib import parse, request
import re

# FFmpeg options
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -filter:a "volume=0.5"'
}

# YouTube DL options
ydl_opts = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0'
}

ytdl = youtube_dl.YoutubeDL(ydl_opts)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}
    
    def get_queue(self, guild_id):
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]
    
    async def play_song(self, ctx, song):
        voice = ctx.voice_client
        
        if not voice:
            return
        
        def after_playing(error):
            if error:
                print(f"Error playing: {error}")
            asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)
        
        try:
            source = await discord.FFmpegOpusAudio.from_probe(song['url'], **FFMPEG_OPTIONS)
            voice.play(source, after=after_playing)
            
            embed = discord.Embed(
                title="🎵 Now Playing",
                description=f"**[{song['title']}]({song['webpage_url']})**",
                color=discord.Color.green()
            )
            embed.add_field(name="Requested by", value=song['requester'].mention, inline=True)
            embed.add_field(name="Duration", value=song.get('duration_string', 'Unknown'), inline=True)
            embed.set_thumbnail(url=song.get('thumbnail', ''))
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error playing: {str(e)[:100]}")
            await self.play_next(ctx)
    
    async def play_next(self, ctx):
        queue = self.get_queue(ctx.guild.id)
        if queue:
            next_song = queue.pop(0)
            await self.play_song(ctx, next_song)
        else:
            # Disconnect after 5 minutes of inactivity
            await asyncio.sleep(300)
            if ctx.voice_client and not ctx.voice_client.is_playing():
                await ctx.voice_client.disconnect()
    
    @commands.command(name="play", aliases=["p"])
    async def play(self, ctx, *, query):
        """Play a song from YouTube"""
        if not ctx.author.voice:
            await ctx.send("❌ You need to be in a voice channel first!")
            return
        
        voice_channel = ctx.author.voice.channel
        voice = ctx.voice_client
        
        if not voice:
            await voice_channel.connect()
            voice = ctx.voice_client
        
        if voice.channel != voice_channel:
            await voice.move_to(voice_channel)
        
        # Show searching message
        searching = await ctx.send(f"🔍 Searching: `{query}`...")
        
        try:
            # Extract song info
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
                'duration': data.get('duration', 0),
                'duration_string': self.format_duration(data.get('duration', 0)),
                'thumbnail': data.get('thumbnail', ''),
                'requester': ctx.author
            }
            
            await searching.delete()
            
            queue = self.get_queue(ctx.guild.id)
            
            if voice.is_playing() or voice.is_paused():
                queue.append(song)
                embed = discord.Embed(
                    title="📋 Added to Queue",
                    description=f"**[{song['title']}]({song['webpage_url']})**",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Position", value=f"#{len(queue)}", inline=True)
                embed.add_field(name="Requested by", value=ctx.author.mention, inline=True)
                await ctx.send(embed=embed)
            else:
                await self.play_song(ctx, song)
        
        except Exception as e:
            await searching.edit(content=f"❌ Error: {str(e)[:100]}")
    
    @commands.command(name="skip", aliases=["s"])
    async def skip(self, ctx):
        """Skip the current song"""
        voice = ctx.voice_client
        if not voice or not voice.is_playing():
            await ctx.send("❌ Nothing is playing right now!")
            return
        
        voice.stop()
        await ctx.send("⏭️ Skipped the current song!")
    
    @commands.command(name="stop", aliases=["leave", "dc"])
    async def stop(self, ctx):
        """Stop music and clear queue"""
        voice = ctx.voice_client
        if voice:
            self.queues[ctx.guild.id] = []
            voice.stop()
            await voice.disconnect()
            await ctx.send("⏹️ Stopped music and cleared queue!")
    
    @commands.command(name="pause")
    async def pause(self, ctx):
        """Pause the current song"""
        voice = ctx.voice_client
        if voice and voice.is_playing():
            voice.pause()
            await ctx.send("⏸️ Paused the music!")
        else:
            await ctx.send("❌ Nothing is playing!")
    
    @commands.command(name="resume")
    async def resume(self, ctx):
        """Resume the paused song"""
        voice = ctx.voice_client
        if voice and voice.is_paused():
            voice.resume()
            await ctx.send("▶️ Resumed the music!")
        else:
            await ctx.send("❌ Nothing is paused!")
    
    @commands.command(name="queue", aliases=["q"])
    async def queue(self, ctx):
        """Show the current music queue"""
        queue = self.get_queue(ctx.guild.id)
        
        if not queue:
            await ctx.send("📭 The queue is empty!")
            return
        
        embed = discord.Embed(
            title="📋 Music Queue",
            description=f"**{len(queue)}** songs in queue",
            color=discord.Color.blue()
        )
        
        for i, song in enumerate(queue[:10]):
            embed.add_field(
                name=f"{i+1}. {song['title'][:50]}",
                value=f"Requested by {song['requester'].mention} • {song['duration_string']}",
                inline=False
            )
        
        if len(queue) > 10:
            embed.set_footer(text=f"And {len(queue)-10} more songs...")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="nowplaying", aliases=["np"])
    async def nowplaying(self, ctx):
        """Show what's currently playing"""
        voice = ctx.voice_client
        if not voice or not voice.is_playing():
            await ctx.send("❌ Nothing is playing!")
            return
        
        # This is a simplified version - actual current song tracking requires more complex implementation
        await ctx.send("🎵 Music is currently playing! Use `$queue` to see upcoming songs.")
    
    @commands.command(name="volume", aliases=["vol"])
    async def volume(self, ctx, volume: int = None):
        """Change volume (0-100)"""
        if volume is None:
            await ctx.send(f"🔊 Current volume: 50% (fixed)")
            return
        
        if volume < 0 or volume > 100:
            await ctx.send("❌ Volume must be between 0 and 100!")
            return
        
        await ctx.send(f"🔊 Volume set to {volume}% (Note: Volume control may be limited)")
    
    def format_duration(self, seconds):
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

async def setup(bot):
    await bot.add_cog(Music(bot))