import os
import discord
from discord.ext import commands
import yt_dlp
import asyncio

# ------------------------
# SETTINGS
# ------------------------
TOKEN = os.environ["DISCORD_TOKEN"]  # replace with your bot token
ALLOWED_TEXT_CHANNEL_ID = 984227820639236157  # replace with your text channel ID

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------------
# YTDL SETTINGS for SoundCloud
# ------------------------
ytdl_opts = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "default_search": "scsearch",  # <- search in SoundCloud instead of YouTube
}
ytdl = yt_dlp.YoutubeDL(ytdl_opts)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get("title")

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=not stream)
        )

        if "entries" in data:
            data = data["entries"][0]  # take first search result

        filename = data["url"] if stream else ytdl.prepare_filename(data)
        return cls(
            discord.FFmpegPCMAudio(filename, executable="ffmpeg", before_options="-nostdin", options="-vn"),
            data=data,
        )


# ------------------------
# EVENTS
# ------------------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")


# ------------------------
# COMMANDS
# ------------------------
@bot.command(name="play")
async def play(ctx, *, query):
    if ctx.channel.id != ALLOWED_TEXT_CHANNEL_ID:
        await ctx.send("❌ You can only use music commands in the dedicated music channel.")
        return

    if not ctx.author.voice:
        await ctx.send("❌ You need to be in a voice channel to play music!")
        return

    voice_client = ctx.voice_client
    if not voice_client:
        voice_channel = ctx.author.voice.channel
        voice_client = await voice_channel.connect()
    elif voice_client.channel != ctx.author.voice.channel:
        await voice_client.move_to(ctx.author.voice.channel)

    async with ctx.typing():
        player = await YTDLSource.from_url(query, loop=bot.loop, stream=True)
        if voice_client.is_playing():
            voice_client.stop()
        voice_client.play(player, after=lambda e: print(f"Player error: {e}") if e else None)

    await ctx.send(f"🎶 Now playing from SoundCloud: **{player.title}**")


@bot.command(name="skip")
async def skip(ctx):
    if ctx.channel.id != ALLOWED_TEXT_CHANNEL_ID:
        return
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Skipped track.")


@bot.command(name="leave")
async def leave(ctx):
    if ctx.channel.id != ALLOWED_TEXT_CHANNEL_ID:
        return
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Left the voice channel.")


# ------------------------
# RUN BOT
# ------------------------
if __name__ == "__main__":
    bot.run(TOKEN)
