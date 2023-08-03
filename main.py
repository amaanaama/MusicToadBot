import discord
import spotipy
import random
import config 
from spotipy.oauth2 import SpotifyClientCredentials

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
        if command == 'setplaylist':
            playlist_uri = message.content.split(' ')[1]
            playlist_storage[message.guild.id] = playlist_uri
        elif command == 'sotd':
            playlist_uri = playlist_storage.get(message.guild.id, DEFAULT_PLAYLIST_URI)
            playlist_tracks = sp.playlist_tracks(playlist_uri)
            random_track = random.choice(playlist_tracks['items'])

            song_name = random_track['track']['name']
            artist_name = random_track['track']['artists'][0]['name']
            message_text = f"Today's song of the day is {song_name} by {artist_name}!\nCheck it out on Spotify: {random_track['track']['external_urls']['spotify']}"
            await message.channel.send(message_text)

client.run(DISCORD_TOKEN)