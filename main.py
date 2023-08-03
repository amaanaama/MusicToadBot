import discord
import spotipy
import random
import config
import re
from spotipy.oauth2 import SpotifyClientCredentials
from datetime import date


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


@client.event
async def on_ready():
    print('Logged in as {0.user}'.format(client))


@client.event
async def on_message(message):
    if message.content.startswith(COMMAND_PREFIX):
        command = message.content[len(COMMAND_PREFIX):].lower()
        
        
        if command.startswith('sp'):
            playlist_url = message.content.split(' ')[1]
            try:
                playlist_id = get_playlist_id(playlist_url)
                playlist_uri = f'spotify:playlist:{playlist_id}'
                sp.playlist(playlist_uri)  # This will validate the playlist
                playlist_storage[message.guild.id] = {"playlist": playlist_uri, "song": None}
                await message.channel.send(f"Playlist successfully set!")
            except Exception as e:
                await message.channel.send("Error: Invalid playlist URL. Please provide a valid Spotify playlist URL.")


        elif command == 'sotd':
            playlist_data = playlist_storage.get(message.guild.id, {"playlist": DEFAULT_PLAYLIST_URI, "song": None})
            playlist_uri = playlist_data["playlist"]
            playlist_tracks = sp.playlist_tracks(playlist_uri)

            # Check if it's a new day or if the playlist has changed
            today = date.today()
            last_selected_song = playlist_data["song"]
            if last_selected_song is None or last_selected_song["date"] != today.strftime('%Y-%m-%d'):
                random_track = random.choice(playlist_tracks['items'])
                playlist_storage[message.guild.id] = {"playlist": playlist_uri, "song": {"date": today.strftime('%Y-%m-%d'), "track": random_track}}
            else:
                random_track = last_selected_song["track"]

            song_name = random_track['track']['name']
            artist_name = random_track['track']['artists'][0]['name']
            message_text = f"Today's song of the day is {song_name} by {artist_name}!\nCheck it out on Spotify: {random_track['track']['external_urls']['spotify']}"
            await message.channel.send(message_text)


def get_playlist_id(playlist_url):
    # Extract playlist ID from the URL using regex
    pattern = r'/playlist/([\w\d]+)'
    match = re.search(pattern, playlist_url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid playlist URL")


client.run(DISCORD_TOKEN)
