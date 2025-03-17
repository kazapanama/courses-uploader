import os
import asyncio
from asyncio import WindowsSelectorEventLoopPolicy
from telegram import Bot
from telegram.constants import ParseMode
from dotenv import load_dotenv


load_dotenv()

# Get configuration from environment variables
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
channel_username = os.getenv('TELEGRAM_CHANNEL_USERNAME')
root_folder = os.getenv('VIDEO_ROOT_FOLDER')


# List of video extensions to look for
video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp']

class VideoUploader:
    def __init__(self, bot_token, channel_username, root_folder):
        self.bot_token = bot_token
        self.channel_username = channel_username
        self.root_folder = root_folder
        self.bot = None
        self.channel_id = None
        self.failed_uploads = {}   # Store failed uploads and error messages
        self.uploaded_videos = {}  # Track videos uploaded in this session
    
    async def initialize(self):
        self.bot = Bot(token=self.bot_token)
        
        try:
            # Check if we're using a channel ID (starts with -) or a username
            if str(self.channel_username).startswith('-'):
                self.channel_id = self.channel_username
                print(f"Connecting to channel using ID: {self.channel_id}")
                
                # Send a test message to verify channel access
                test_message = await self.bot.send_message(chat_id=self.channel_id, text="Initializing video uploader...")
            else:
                # We're using a username
                if self.channel_username.startswith('@'):
                    channel_name = self.channel_username[1:]
                else:
                    channel_name = self.channel_username
                    
                channel_username_with_at = f"@{channel_name}"
                print(f"Connecting to channel: {channel_username_with_at}")
                
                # Send a test message to get channel info
                test_message = await self.bot.send_message(chat_id=channel_username_with_at, text="Initializing video uploader...")
                self.channel_id = test_message.chat_id
            
            # Delete the test message
            await self.bot.delete_message(chat_id=self.channel_id, message_id=test_message.message_id)
            
            print(f"Successfully connected to channel. Chat ID: {self.channel_id}")
            return True
        except Exception as e:
            print(f"Error initializing: {str(e)}")
            print("Make sure:")
            print("1. Your bot is added to the channel")
            print("2. The bot has admin privileges in the channel")
            print("3. The channel username is correct")
            return False
    
    def get_all_video_files(self):
        """Get a list of all video files in the directory structure"""
        video_files = []
        
        for folder_path, _, files in os.walk(self.root_folder):
            for file in files:
                if os.path.splitext(file)[1].lower() in video_extensions:
                    full_path = os.path.join(folder_path, file)
                    video_files.append(full_path)
        
        return video_files
    
    async def check_if_already_uploaded(self, file_path, caption):
        """Check if a video is already uploaded by testing upload"""
        try:
            # First, send a message about what we're doing
            video_name = os.path.basename(file_path)
            test_msg = await self.bot.send_message(
                chat_id=self.channel_id,
                text=f"Testing if {video_name} is already uploaded..."
            )
            
            # Try to send 1 second of the video as a test
            with open(file_path, 'rb') as video:
                try:
                    test_upload = await self.bot.send_video(
                        chat_id=self.channel_id,
                        video=video,
                        caption=f"[TEST] {caption}",
                        duration=1,
                        supports_streaming=True,
                        width=720,
                        height=480,
                    )
                    
                    # If we get here, the video wasn't already uploaded
                    # Delete the test upload
                    await self.bot.delete_message(
                        chat_id=self.channel_id,
                        message_id=test_upload.message_id
                    )
                    
                    # Delete the info message
                    await self.bot.delete_message(
                        chat_id=self.channel_id,
                        message_id=test_msg.message_id
                    )
                    
                    # Video not found in channel
                    return False
                    
                except Exception as e:
                    error_text = str(e)
                    # If telegram says the file already exists, it's already uploaded
                    if "file is already uploaded" in error_text.lower() or "file reference" in error_text.lower():
                        print(f"Video was already uploaded to channel: {video_name}")
                        
                        # Update the message to show it's already uploaded
                        await self.bot.edit_message_text(
                            chat_id=self.channel_id,
                            message_id=test_msg.message_id,
                            text=f"✅ {video_name} is already in the channel"
                        )
                        
                        # Wait a moment then delete the message
                        await asyncio.sleep(2)
                        await self.bot.delete_message(
                            chat_id=self.channel_id,
                            message_id=test_msg.message_id
                        )
                        
                        return True
                    else:
                        # Some other error occurred
                        await self.bot.delete_message(
                            chat_id=self.channel_id,
                            message_id=test_msg.message_id
                        )
                        return False
                        
        except Exception as e:
            # If any error, assume not uploaded
            print(f"Error checking if already uploaded: {str(e)}")
            return False
    
    async def upload_video(self, file_path):
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        # If video is already uploaded in this session, skip it
        if file_path in self.uploaded_videos:
            print(f"Skipping already uploaded in this session: {file_name}")
            return True
        
        # Get relative path for the folder
        folder_path = os.path.dirname(file_path)
        rel_path = os.path.relpath(folder_path, self.root_folder)
        if rel_path == '.':
            rel_path = 'Root folder'
        
        # Format caption
        caption = f"{file_name}"
        if rel_path != "Root folder":
            caption = f"[{rel_path}] {file_name}"
        
        # Check if already uploaded to channel
        if await self.check_if_already_uploaded(file_path, caption):
            self.uploaded_videos[file_path] = "already_exists"
            return True
        
        print(f"Uploading: {file_name} ({file_size / (1024 * 1024):.2f} MB)")
        
        # Check file size - Telegram has a 50MB limit for standard bots
        if file_size > 50 * 1024 * 1024:  # 50MB in bytes
            error_msg = f"File exceeds Telegram bot API size limit (50MB)"
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=f"⚠️ Skipping {file_name}: {error_msg}"
            )
            print(f"Skipping {file_name}: {error_msg}")
            self.failed_uploads[file_path] = error_msg
            return False
        
        # Try to upload, with multiple attempts
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                with open(file_path, 'rb') as video:
                    message = await self.bot.send_video(
                        chat_id=self.channel_id,
                        video=video,
                        caption=caption,
                        supports_streaming=True,
                        width=720,
                        height=480,
                    )
                
                # Store successful upload
                self.uploaded_videos[file_path] = message.message_id
                
                # Remove from failed uploads if it was there
                if file_path in self.failed_uploads:
                    del self.failed_uploads[file_path]
                
                print(f"Successfully uploaded: {file_name} (Attempt {attempt})")
                return True
                
            except Exception as e:
                error_msg = str(e)
                print(f"Error uploading {file_name} (Attempt {attempt}/{max_attempts}): {error_msg}")
                
                # Check if the error indicates the file is already uploaded
                if "file is already uploaded" in error_msg.lower() or "file reference" in error_msg.lower():
                    print(f"Video was already uploaded to channel: {file_name}")
                    self.uploaded_videos[file_path] = "already_exists"
                    return True
                
                # If this is the last attempt, record the failure
                if attempt == max_attempts:
                    self.failed_uploads[file_path] = error_msg
                    await self.bot.send_message(
                        chat_id=self.channel_id,
                        text=f"⚠️ Error uploading {file_name}: {error_msg}"
                    )
                    return False
                else:
                    # Wait longer between each retry
                    await asyncio.sleep(5 * attempt)
    
    async def retry_failed_uploads(self):
        if not self.failed_uploads:
            print("No failed uploads to retry")
            return
        
        print(f"\nRetrying {len(self.failed_uploads)} failed uploads...")
        failed_files = list(self.failed_uploads.keys())
        
        for file_path in failed_files:
            if os.path.exists(file_path):
                print(f"Retrying upload for: {os.path.basename(file_path)}")
                
                # Try to upload again
                success = await self.upload_video(file_path)
                if success:
                    print(f"Successfully re-uploaded: {os.path.basename(file_path)}")
            else:
                print(f"Could not find file for retry: {file_path}")
                
            # Small delay between retries
            await asyncio.sleep(2)
    
    async def process_videos(self):
        print(f"Starting upload process for folder: {self.root_folder}")
        
        # Get all video files
        all_videos = self.get_all_video_files()
        videos_by_folder = {}
        
        # Group videos by folder
        for video_path in all_videos:
            folder_path = os.path.dirname(video_path)
            if folder_path not in videos_by_folder:
                videos_by_folder[folder_path] = []
            videos_by_folder[folder_path].append(video_path)
        
        # Process folders in sorted order
        for folder_path in sorted(videos_by_folder.keys()):
            # Get relative path for display
            rel_path = os.path.relpath(folder_path, self.root_folder)
            if rel_path == '.':
                rel_path = 'Root folder'
            
            # Send folder message
            folder_msg = await self.bot.send_message(
                chat_id=self.channel_id, 
                text=f"📁 **Folder: {rel_path}**", 
                parse_mode=ParseMode.MARKDOWN
            )
            print(f"\nUploading from folder: {rel_path}")
            
            # Track if we actually uploaded anything in this folder
            uploaded_count = 0
            
            # Upload each video in the current folder
            for video_path in sorted(videos_by_folder[folder_path]):
                # Upload the video (function will check if already uploaded)
                success = await self.upload_video(video_path)
                if success and video_path in self.uploaded_videos:
                    if self.uploaded_videos[video_path] != "already_exists":
                        uploaded_count += 1
                
                # Add a small delay between uploads to avoid flooding
                await asyncio.sleep(2)
            
            # If we didn't upload anything new in this folder, delete the folder message
            if uploaded_count == 0:
                try:
                    await self.bot.delete_message(
                        chat_id=self.channel_id,
                        message_id=folder_msg.message_id
                    )
                    print(f"No new uploads in folder {rel_path}, removed folder message")
                except:
                    pass
        
        # After processing all videos, retry any that failed
        await self.retry_failed_uploads()
        
        print("\nUpload process completed!")
        await self.bot.send_message(chat_id=self.channel_id, text="✅ Video upload process completed!")

async def main():
    uploader = VideoUploader(bot_token, channel_username, root_folder)
    
    if await uploader.initialize():
        await uploader.process_videos()
    else:
        print("Initialization failed. Exiting.")

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