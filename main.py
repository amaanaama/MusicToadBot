import discord
import spotipy
import random
import config
import re
from spotipy.oauth2 import SpotifyClientCredentials
from datetime import date, time, timedelta, datetime
import asyncio

DISCORD_TOKEN = config.DISCORD_TOKEN
SPOTIFY_CLIENT_ID = config.SPOTIFY_CLIENT_ID
SPOTIFY_CLIENT_SECRET = config.SPOTIFY_CLIENT_SECRET
DEFAULT_PLAYLIST_URI = 'spotify:playlist:6s8pr9gAJ4Ja2oNK90ddhL'
COMMAND_PREFIX = '!'

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))

playlist_storage = {}
target_time = time(10, 35)  # Replace with the desired time in 24-hour format (e.g., time(10, 25) for 10:25 AM)


@client.event
async def on_ready():
    print('Logged in as {0.user}'.format(client))
    await send_song_of_the_day()  # Send the song of the day when the bot starts
    client.loop.create_task(schedule_send_song_of_the_day())  # Schedule the task for the next day


@client.event
async def on_message(message):
    if message.content.startswith(COMMAND_PREFIX):
        command = message.content[len(COMMAND_PREFIX):].lower()

        if command.startswith('sp'):
            if message.author.guild_permissions.manage_channels:
                playlist_url = message.content.split(' ')[1]
                try:
                    playlist_id = get_playlist_id(playlist_url)
                    playlist_uri = f'spotify:playlist:{playlist_id}'
                    sp.playlist(playlist_uri)  # This will validate the playlist
                    playlist_storage[message.guild.id] = {"playlist": playlist_uri, "song": None, "channel": None}
                    await message.channel.send(f"Playlist successfully set!")
                except Exception as e:
                    await message.channel.send("Error: Invalid playlist URL. Please provide a valid Spotify playlist URL.")
            else:
                await message.channel.send("You don't have the required permissions to set the playlist.")

        elif command.startswith('set_channel'):
            if message.author.guild_permissions.manage_channels:
                channel_id = message.content.split(' ')[1]
                # Validate if the provided channel ID exists
                if client.get_channel(int(channel_id)):
                    playlist_data = playlist_storage.get(message.guild.id, {"playlist": DEFAULT_PLAYLIST_URI, "song": None, "channel": None})
                    playlist_storage[message.guild.id] = {"playlist": playlist_data["playlist"], "song": playlist_data["song"], "channel": int(channel_id)}
                    await message.channel.send("Channel successfully set!")
                else:
                    await message.channel.send("Error: Invalid channel ID.")
            else:
                await message.channel.send("You don't have the required permissions to set the channel.")


def get_playlist_id(playlist_url):
    # Extract playlist ID from the URL using regex
    pattern = r'/playlist/([\w\d]+)'
    match = re.search(pattern, playlist_url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid playlist URL")


# Task to send the song of the day message
async def send_song_of_the_day():
    for guild_id, playlist_data in playlist_storage.items():
        channel_id = playlist_data.get("channel")
        if channel_id:
            channel = client.get_channel(channel_id)
            if channel:
                playlist_uri = playlist_data["playlist"]
                playlist_tracks = sp.playlist_tracks(playlist_uri)

                # Check if it's a new day or if the playlist has changed
                today = date.today()
                last_selected_song = playlist_data["song"]
                if last_selected_song is None or last_selected_song["date"] != today.strftime('%Y-%m-%d'):
                    random_track = random.choice(playlist_tracks['items'])
                    playlist_storage[guild_id] = {"playlist": playlist_uri, "song": {"date": today.strftime('%Y-%m-%d'), "track": random_track}, "channel": channel_id}
                else:
                    random_track = last_selected_song["track"]

                song_name = random_track['track']['name']
                artist_name = random_track['track']['artists'][0]['name']
                message_text = f"Today's song of the day is {song_name} by {artist_name}!\nCheck it out on Spotify: {random_track['track']['external_urls']['spotify']}"
                await channel.send(message_text)


async def schedule_send_song_of_the_day():
    while not client.is_closed():
        current_time = datetime.now().time()
        target_datetime = datetime.combine(date.today(), target_time)

        # Check if the current time is after the target time for today
        if current_time > target_time:
            # Add one day to the target date to schedule for the next day
            target_datetime += timedelta(days=1)

        # Calculate the seconds to sleep until the target time
        sleep_seconds = (target_datetime - datetime.now()).total_seconds()
        await asyncio.sleep(sleep_seconds)

        await send_song_of_the_day()
        # Add one day to the target date to schedule for the next day
        target_datetime += timedelta(days=1)


async def run_bot():
    await client.start(DISCORD_TOKEN)

try:
    asyncio.run(run_bot())
except KeyboardInterrupt:
    asyncio.run(client.close())
