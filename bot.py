import os
import asyncio
from aiohttp import web, ClientSession
import pyttsx3

# 1. Fetch Environment Variables
TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}/"

# 2. Web Server Route (Health Check for Render)
async def handle_health(request):
    return web.Response(text="EchoVocal is active!")

# 3. Synchronous Audio Generation Helper
# (We isolate this to prevent blocking the async application loop)
def generate_speech_file(text, output_filename):
    engine = pyttsx3.init()
    
    # Adjust speech rate/speed (Optional: 150-200 is standard)
    engine.setProperty('rate', 165) 
    
    # Save directly to a local audio file
    engine.save_to_file(text, output_filename)
    engine.runAndWait()

# 4. Handle Text-to-Speech Requests
async def process_text_to_speech(session, chat_id, text):
    # Let the user know the bot is rendering the voice
    await session.post(f"{API_URL}sendMessage", data={"chat_id": chat_id, "text": "🎙️ Generating audio file, please wait..."})
    
    output_filename = f"speech_{chat_id}.mp3"
    
    try:
        # Run the synchronous file generation safely in an executor thread
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, generate_speech_file, text, output_filename)
        
        # Check if file was successfully created
        if os.path.exists(output_filename) and os.path.getsize(output_filename) > 0:
            # Prepare the audio file to upload via Telegram API
            send_voice_url = f"{API_URL}sendVoice"
            
            # Use standard multipart form upload
            with open(output_filename, 'rb') as audio_file:
                # We format a clean API post payload for the binary data
                from aiohttp import FormData
                data = FormData()
                data.add_field('chat_id', str(chat_id))
                data.add_field('voice', audio_file, filename='voice.mp3', content_type='audio/mpeg')
                
                async with session.post(send_voice_url, data=data) as resp:
                    if resp.status != 200:
                        raise Exception("Failed to upload the audio file to Telegram.")
        else:
            raise Exception("Audio file generation failed or was empty.")
            
    except Exception as e:
        print(f"Error processing TTS: {e}")
        await session.post(f"{API_URL}sendMessage", data={"chat_id": chat_id, "text": "❌ An error occurred while generating speech. Please try shorter text."})
        
    finally:
        # Clean up the generated file from Render's local disk space safely
        if os.path.exists(output_filename):
            try:
                os.remove(output_filename)
            except Exception:
                pass

# 5. Main Bot Long Polling
async def bot_polling():
    offset = 0
    print("EchoVocal polling started...")
    
    async with ClientSession() as session:
        while True:
            try:
                url = f"{API_URL}getUpdates"
                params = {"offset": offset, "timeout": 30}
                
                async with session.get(url, params=params, timeout=35) as response:
                    res_json = await response.json()
                    
                    if res_json.get("ok") and res_json.get("result"):
                        for update in res_json["result"]:
                            offset = update["update_id"] + 1
                            message = update.get("message", {})
                            chat_id = message.get("chat", {}).get("id")
                            text = message.get("text", "")
                            
                            if not chat_id:
                                continue
                                
                            if text == "/start":
                                msg = "Hello! Send me any text sentence or paragraph, and I will speak it back to you as an audio message!"
                                await session.post(f"{API_URL}sendMessage", data={"chat_id": chat_id, "text": msg})
                            elif text:
                                # Hand off text to processing task safely
                                asyncio.create_task(process_text_to_speech(session, chat_id, text))
                                
            except Exception as e:
                print(f"Polling error: {e}")
                await asyncio.sleep(5)

# 6. Application Launcher
async def main():
    app = web.Application()
    app.router.add_get('/', handle_health)
    
    port = int(os.getenv("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    await site.start()
    await bot_polling()

if __name__ == "__main__":
    asyncio.run(main())
