import discord
import spotipy
import random
import re
import os
import asyncio
import requests

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
target_time = time(14, 20)  


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
        target_datetime += timedelta(hours=1)

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
                spotify_track_url = random_track['track']['external_urls']['spotify']

                # Get the cover image URL for the selected song
                cover_image_url = get_cover_image(spotify_track_url)

                if cover_image_url:
                    # Download the cover image
                    response = requests.get(cover_image_url)
                    if response.status_code == 200:
                        with open("cover_image.jpg", "wb") as f:
                            f.write(response.content)

                        # Send the message with the cover image
                        message_text = f"Today's song of the day is {song_name} by {artist_name}!\n{spotify_track_url}"
                        await channel.send(message_text, file=discord.File("cover_image.jpg"))
                        os.remove("cover_image.jpg")
                    else:
                        # If there was an issue with the cover image, send the message without it
                        message_text = f"Today's song of the day is {song_name} by {artist_name}!\n{spotify_track_url}"
                        await channel.send(message_text)
                else:
                    # If cover image URL could not be retrieved, send the message without it
                    message_text = f"Today's song of the day is {song_name} by {artist_name}!\n{spotify_track_url}"
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
        await asyncio.sleep(3600)

        # Schedule the task for the next hour
        target_datetime += timedelta(hours=1)

async def run_bot():
    await client.login(DISCORD_TOKEN)  # Login the Discord client using the token
    print('Bot is online and connected to Discord.')
    client.loop.create_task(schedule_send_song_of_the_day())  # Schedule the task to start immediately
    await client.start(DISCORD_TOKEN)  # Start the client using the token

# Run the bot
loop = asyncio.get_event_loop()
loop.run_until_complete(run_bot())
