from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, CallbackQueryHandler
import yt_dlp
import asyncio
import os

# Replace with your actual bot token
TOKEN = '7691286417:AAGwgVEO9A_T23-UMyEZGxdQbc8dJPV4-_A'

# Store the URLs for each chat
user_video_links = {}

class MyLogger:
    @staticmethod
    def debug(msg):
        print(msg)

    @staticmethod
    def warning(msg):
        print(msg)

    @staticmethod
    def error(msg):
        print(msg)

async def handle_message(update: Update, context):
    message_text = update.message.text
    chat_id = update.message.chat.id

    print(f"Received message: {message_text} from chat ID: {chat_id}")

    if "youtube.com" in message_text or "youtu.be" in message_text:
        await update.message.reply_text("Processing your YouTube link...")

        try:
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'cookies': 'path/to/cookies.txt',  # Optional: Add cookies if video is private or age-restricted
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                },
                'force_generic_extractor': True,  # Handle non-standard formats
                'quiet': True,                    # Silence unnecessary logs
                'logger': MyLogger(),            # Use custom logger
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(message_text, download=False)
                print(f"Video info: {info}")

            # Store the YouTube link for later
            user_video_links[chat_id] = message_text

            formats = info.get('formats', [])
            buttons = []

            for format in formats:
                if format.get('vcodec') != 'none':  # Ignore audio-only formats
                    format_id = format['format_id']
                    resolution = format.get('resolution', 'N/A')
                    buttons.append([InlineKeyboardButton(f"{resolution} - {format_id}", callback_data=format_id)])

            if buttons:
                reply_markup = InlineKeyboardMarkup(buttons)
                await update.message.reply_text(
                    "Please choose a video format to download:",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text("No video formats found. Please try again.")
        except Exception as e:
            print(f"Error: {e}")
            await update.message.reply_text("Failed to process the YouTube link. Please try again.")
    else:
        await update.message.reply_text("Please send a valid YouTube link.")

async def handle_callback_query(update: Update, context):
    query = update.callback_query
    format_id = query.data  # This is the format selected by the user
    chat_id = query.message.chat.id

    # Retrieve the YouTube link from the stored dictionary
    video_url = user_video_links.get(chat_id)

    if not video_url:
        await query.answer()
        await query.edit_message_text(text="No YouTube link found for this request.")
        return

    try:
        await query.answer()  # Acknowledge the callback
        await query.edit_message_text(text=f"Downloading format: {format_id}...")

        # Use yt-dlp to download the selected format
        ydl_opts = {
            'format': format_id,
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'cookies': 'path/to/cookies.txt',  # Optional: Add cookies for restricted content
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            },
            'force_generic_extractor': True,  # Use generic extractor if format is unsupported
            'quiet': True,
            'socket_timeout': 300,  # Increased timeout
            'retries': 10,          # Retry up to 10 times
            'continuedl': True,     # Resume partial downloads
            'http_chunk_size': 1024 * 512,  # Smaller chunks (512 KB)
            'ratelimit': 1 * 1024 * 1024,  # Limit download speed to 1 MB/s
            'logger': MyLogger(),  # Custom logger
        }

        os.makedirs("downloads", exist_ok=True)  # Ensure the downloads directory exists

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            print(f"Downloaded video info: {info}")
            file_path = ydl.prepare_filename(info)

        await query.edit_message_text(text="Download complete! Sending your video...")

        with open(file_path, "rb") as video_file:
            await context.bot.send_video(chat_id=chat_id, video=video_file)

    except Exception as e:
        print(f"Error: {e}")
        await query.edit_message_text(text="Failed to download the video. Please try again.")

async def main():
    application = Application.builder().token(TOKEN).build()

    # Handlers
    message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    callback_query_handler = CallbackQueryHandler(handle_callback_query)
    application.add_handler(message_handler)
    application.add_handler(callback_query_handler)

    print("Bot is running... Waiting for messages.")
    await application.run_polling()

if __name__ == '__main__':
    # Just run the main function directly, no need for asyncio.run()
    import nest_asyncio
    nest_asyncio.apply()  # This allows running nested event loops, especially in environments like Jupyter or certain IDEs
    asyncio.run(main())
