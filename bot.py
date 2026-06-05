import os
import io
import asyncio
import struct
from aiohttp import web, ClientSession
import speech_recognition as sr
import soundfile as sf
import librosa

# 1. Fetch Environment Variables
TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}/"
FILE_URL = f"https://api.telegram.org/file/bot{TOKEN}/"

# 2. Web Server Route (Health Check for SnapDeploy)
async def handle_health(request):
    return web.Response(text="VoxScribe Voice Engine is active!")

# 3. Handle Voice Messages Safely
async def process_voice(session, chat_id, file_id):
    await session.post(f"{API_URL}sendMessage", data={"chat_id": chat_id, "text": "🔄 Transcribing your audio file locally, please wait..."})

    try:
        # Get file path from Telegram API
        async with session.get(f"{API_URL}getFile", params={"file_id": file_id}) as res:
            res_data = await res.json()
            if not res_data.get("ok"):
                raise Exception("Failed to get file path from Telegram.")
            file_path = res_data["result"]["file_path"]

        # Download the raw audio file into memory
        async with session.get(f"{FILE_URL}{file_path}") as file_res:
            ogg_bytes = await file_res.read()

        # Convert the audio array into memory using librosa
        ogg_io = io.BytesIO(ogg_bytes)
        audio_data, sample_rate = librosa.load(ogg_io, sr=16000)
        
        # Build a safe in-memory WAV container explicitly structured for PocketSphinx
        wav_io = io.BytesIO()
        sf.write(wav_io, audio_data, sample_rate, format='WAV', subtype='PCM_16')
        wav_io.seek(0)

        # Pass the formatted WAV directly to the Recognizer
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_io) as source:
            # Adjust slightly for any background hiss or low mic input
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.record(source)
        
        # Transcribe locally 
        text_result = recognizer.recognize_sphinx(audio)
        
        if not text_result.strip():
            reply_text = "⚠️ Audio processed, but no clear words were recognized. Try speaking slower and closer to the mic."
        else:
            reply_text = f"📝 **Transcription:**\n\n\"{text_result}\""

    except sr.UnknownValueError:
        reply_text = "❌ Audio structure was parsed, but the local engine couldn't match the words. Make sure you are speaking clearly in English."
    except Exception as e:
        print(f"Internal processing error: {e}")
        reply_text = "❌ Local voice engine layout mismatch. Try sending a very short 2-3 second voice clip to test."

    # Send the final response back to the user
    await session.post(f"{API_URL}sendMessage", data={"chat_id": chat_id, "text": reply_text, "parse_mode": "Markdown"})

# 4. Main Bot Long Polling Loop
async def bot_polling():
    offset = 0
    print("VoxScribe polling loop started...")
    
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
                            text = message.get("text
