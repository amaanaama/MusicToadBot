import discord
import spotipy
import random
import re
import os
import asyncio
import requests
from discord.ext import tasks

from spotipy.oauth2 import SpotifyClientCredentials
from datetime import date, time, timedelta, datetime


DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
DEFAULT_PLAYLIST_URI = 'spotify:playlist:6s8pr9gAJ4Ja2oNK90ddhL'
COMMAND_PREFIX = '!'

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))

playlist_storage = {}
target_time = time(13, 25)  


@client.event
async def on_ready():
    print('Logged in as {0.user}'.format(client))
    client.loop.create_task(schedule_send_song_of_the_day(target_time))


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

        elif command.startswith('sc'):
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

        elif command.startswith('tl'):
            await display_time_left(message.channel)

async def display_time_left(channel):
    current_time = datetime.now().time()
    target_datetime = datetime.combine(date.today(), target_time)

    if current_time > target_time:
        target_datetime += timedelta(days=1)

    time_left = target_datetime - datetime.now()
    hours_left = time_left.seconds // 3600
    minutes_left = (time_left.seconds // 60) % 60
    seconds_left = time_left.seconds % 60

    await channel.send(f"Time left until the next song of the day message: {hours_left} hours, {minutes_left} minutes, {seconds_left} seconds.")

def get_playlist_id(playlist_url):
    # Extract playlist ID from the URL using regex
    pattern = r'/playlist/([\w\d]+)'
    match = re.search(pattern, playlist_url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid playlist URL")


# Task to send the song of the day message


def get_cover_image(song_link):
    track_id = song_link.split('/')[-1].split('?')[0]
    track_info = sp.track(track_id)
    if track_info and 'album' in track_info and 'images' in track_info['album'] and len(track_info['album']['images']) > 0:
        cover_image_url = track_info['album']['images'][0]['url']
        return cover_image_url
    else:
        return None

@tasks.loop(hours=24)
async def send_song_of_the_day():
    current_time = datetime.now().time()
    target_datetime = datetime.combine(date.today(), target_time)

    if current_time > target_time:
        target_datetime += timedelta(days=1)

    time_left = target_datetime - datetime.now()
    sleep_seconds = time_left.total_seconds()

    await asyncio.sleep(sleep_seconds)

    for guild_id, playlist_data in playlist_storage.items():
        channel_id = playlist_data.get("channel")
        if channel_id:
            channel = client.get_channel(channel_id)
            if channel:
                playlist_uri = playlist_data["playlist"]
                playlist_tracks = sp.playlist_tracks(playlist_uri)

                today = date.today()
                last_selected_song = playlist_data["song"]
                if last_selected_song is None or last_selected_song["date"] != today.strftime('%Y-%m-%d'):
                    random_track = random.choice(playlist_tracks['items'])
                    playlist_storage[guild_id] = {"playlist": playlist_uri, "song": {"date": today.strftime('%Y-%m-%d'), "track": random_track}, "channel": channel_id}
                else:
                    random_track = last_selected_song["track"]

                song_name = random_track['track']['name']
                artist_name = random_track['track']['artists'][0]['name']
                spotify_track_url = random_track['track']['external_urls']['spotify']

                await channel.send(f"Today's song of the day is {song_name} by {artist_name}!\n{spotify_track_url}")





client.run(DISCORD_TOKEN)
