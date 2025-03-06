import os
# import time
# import requests
import asyncio
from asyncio import WindowsSelectorEventLoopPolicy
from telegram import Bot
from telegram.constants import ParseMode
# import mimetypes

# Telegram Bot credentials
bot_token = '7290280499:AAFDVJ04ZkDG2mbaOj-ODqzTrmRVGkptNMU'    # Replace with your bot token
channel_username = '-1002486284380'  # Replace with your channel username (e.g., 'mychannel' without the @)
# Alternatively, you can use channel ID if you know it (e.g., '-1001234567890')

# Path to the root folder containing videos
root_folder = r'E:\torrent\Pluralsight - Windows Server Administration Concepts series 2020'  # Path to your video folder

# List of video extensions to look for
video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp']

async def main():
    # Initialize the Telegram bot
    bot = Bot(token=bot_token)
    
    # Get the chat ID for the group
    try:
        # Check if we're using a channel ID (starts with -) or a username
        if str(channel_username).startswith('-'):
            # We're using a channel ID directly
            channel_id = channel_username
            print(f"Connecting to channel using ID: {channel_id}")
            
            # Send a test message to verify channel access
            test_message = await bot.send_message(chat_id=channel_id, text="Initializing video uploader...")
        else:
            # We're using a username
            # If channel_username starts with @, remove it
            if channel_username.startswith('@'):
                channel_name = channel_username[1:]
            else:
                channel_name = channel_username
                
            channel_username_with_at = f"@{channel_name}"
            print(f"Connecting to channel: {channel_username_with_at}")
            
            # Send a test message to get channel info
            test_message = await bot.send_message(chat_id=channel_username_with_at, text="Initializing video uploader...")
            channel_id = test_message.chat_id
        
        # Delete the test message
        await bot.delete_message(chat_id=channel_id, message_id=test_message.message_id)
        
        print(f"Successfully connected to channel. Chat ID: {channel_id}")
    except Exception as e:
        print(f"Error finding channel: {str(e)}")
        print("Make sure:")
        print("1. Your bot is added to the channel")
        print("2. The bot has admin privileges in the channel")
        print("3. The channel username is correct")
        return
    
    print(f"Starting upload process for folder: {root_folder}")
    
    # Walk through the directory structure
    for folder_path, _, files in sorted(os.walk(root_folder)):
        # Filter and sort video files
        video_files = [f for f in sorted(files) if os.path.splitext(f)[1].lower() in video_extensions]
        
        if video_files:
            # Get relative path for display
            rel_path = os.path.relpath(folder_path, root_folder)
            if rel_path == '.':
                rel_path = 'Root folder'
            
            # Send a message indicating the current folder
            await bot.send_message(
                chat_id=channel_id, 
                text=f"📁 **Folder: {rel_path}**", 
                parse_mode=ParseMode.MARKDOWN
            )
            print(f"\nUploading from folder: {rel_path}")
            
            # Upload each video in the current folder
            for video_file in video_files:
                file_path = os.path.join(folder_path, video_file)
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                
                print(f"Uploading: {file_name} ({file_size / (1024 * 1024):.2f} MB)")
                
                try:
                    # Check file size - Telegram has a 50MB limit for standard bots
                    if file_size > 50 * 1024 * 1024:  # 50MB in bytes
                        await bot.send_message(
                            chat_id=channel_id,
                            text=f"⚠️ Skipping {file_name}: File exceeds Telegram bot API size limit (50MB)"
                        )
                        print(f"Skipping {file_name}: File exceeds size limit")
                        continue
                    
                    # Upload the video with the filename as caption
                    with open(file_path, 'rb') as video:
                        message = await bot.send_video(
                            chat_id=channel_id,
                            video=video,
                            caption=file_name,
                            supports_streaming=True,
                            width=720,  # Default width, will be ignored if video has different dimensions
                            height=480,  # Default height, will be ignored if video has different dimensions
                        )
                    
                    print(f"Successfully uploaded: {file_name}")
                    
                    # Add a small delay between uploads to avoid flooding
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    print(f"Error uploading {file_name}: {str(e)}")
                    await bot.send_message(
                        chat_id=channel_id,
                        text=f"⚠️ Error uploading {file_name}: {str(e)}"
                    )
    
    print("\nUpload process completed!")
    await bot.send_message(chat_id=channel_id, text="✅ Video upload process completed!")

if __name__ == '__main__':
    # Set up the event loop
    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())  # Fix for Windows event loop issue
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Process interrupted by user")
    finally:
        loop.close()