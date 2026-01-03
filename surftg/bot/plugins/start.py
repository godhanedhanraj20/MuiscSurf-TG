import random
from surftg.config import Telegram
from surftg.helper.database import Database
from surftg.helper.file_size import get_readable_file_size
from surftg.bot import StreamBot
from pyrogram import filters, Client
from pyrogram.types import Message

# Initialize the existing database connection
db = Database()

# --- HELPER FUNCTIONS ---

def get_random_id():
    """Generates a unique fake ID so the database accepts the song."""
    return random.randint(100000, 999999)

# --- COMMAND HANDLERS ---

@StreamBot.on_message(filters.command('start') & filters.private)
async def start(bot: Client, message: Message):
    """Standard start message to check if bot is alive."""
    await message.reply_text("🎵 Audiophile Music Bot is Online! Upload FLAC/MP3 files to index them.")

@StreamBot.on_message(filters.command('log') & filters.private)
async def log_handler(bot: Client, message: Message):
    """Keeps the existing log functionality."""
    try:
        from os import path as ospath
        path = ospath.abspath('log.txt')
        await message.reply_document(document=path, quote=True)
    except Exception as e:
        print(f"Log Error: {e}")

# --- MAIN MUSIC HANDLER ---

@StreamBot.on_message(
    filters.channel
    & (
        filters.audio 
        | filters.document
    )
)
async def file_receive_handler(bot: Client, message: Message):
    """
    Triggers when a file is posted to the channel.
    Extracts Artist/Title/Cover from the file itself.
    """
    # 1. AUTH CHECK: Ensure we only index files from the allowed channel
    channel_id = str(message.chat.id)
    AUTH_CHANNEL = await db.get_variable('auth_channel')
    
    if AUTH_CHANNEL:
        valid_channels = [ch.strip() for ch in AUTH_CHANNEL.split(",")]
    else:
        valid_channels = Telegram.AUTH_CHANNEL

    if channel_id not in valid_channels:
        return # Ignore files from other channels

    try:
        # 2. GET FILE: Prefer 'audio' attribute as it has better metadata
        media = message.audio or message.document
        if not media:
            return

        # 3. EXTRACT METADATA (Artist & Title)
        # Telegram automatically reads tags from FLAC/MP3 files.
        artist = getattr(media, "performer", None) or "Unknown Artist"
        title = getattr(media, "title", None) or media.file_name or "Unknown Track"
        
        # Format the title nicely: "Artist - Track Name"
        if artist != "Unknown Artist":
            clean_title = f"{artist} - {title}"
        else:
            clean_title = title

        # Clean up technical junk from filename if metadata was missing
        clean_title = clean_title.replace("_", " ").replace(".flac", "").replace(".mp3", "")
        
        # 4. GET TECHNICAL DETAILS
        size = get_readable_file_size(media.file_size)
        file_type = media.mime_type or "audio/flac"
        msg_id = message.id
        file_hash = media.file_unique_id[:6]
        cid = str(message.chat.id).replace("-100", "")

        # 5. GET ALBUM ART
        # We use Surf-TG's built-in thumbnail API. 
        # It serves the picture embedded in your FLAC file.
        poster_link = f"/api/thumb/-100{cid}?id={msg_id}"

        # 6. PREPARE DATABASE ENTRY
        # We format it like a "Movie" so the existing website can read it.
        quality_info = {
            "quality": "FLAC" if "flac" in str(file_type).lower() else "MP3", 
            "size": size,
            "type": file_type,
            "hash": file_hash,
            "cid": int(cid),
            "msg_id": msg_id
        }

        song_doc = {
            "tmdb_id": get_random_id(), 
            "title": clean_title,       
            "rating": 10.0,             
            "description": f"Artist: {artist}\nTrack: {title}\nFormat: {file_type}\nSize: {size}", 
            "release_date": "2024-01-01", 
            "poster": poster_link,  # Shows your FLAC cover art
            "backdrop": poster_link,
            "genres": ["Music"],
            "type": "movie", # "movie" tag ensures it appears on the homepage           
            "qualities": [quality_info]
        }

        # 7. SAVE TO DATABASE
        await db.add_tgjson(song_doc)
        
        print(f"✅ Indexed: {clean_title}")

    except Exception as e:
        print(f"❌ Error indexing file: {e}")