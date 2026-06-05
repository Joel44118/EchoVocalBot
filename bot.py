import os
import asyncio
import random
from aiohttp import web, ClientSession

# 1. Fetch Environment Variables
TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}/"

# Vocal presets for the echoing functions
ACCENTS = {
    "robot": "🤖 [ROBOTIC MONOTONE MODE]: {} ... bzzzt ... processing completed.",
    "radio": "🎙️ [90s RADIO DJ VOCAL FILTER]: 'Allright folks, coming in hot with: \"{}\"! You're listening to EchoVocal FM!'",
    "whisper": "🤫 [ASMR WHISPER MIX]: *softly inhales* ... ( {} ) ... *gentle tapping sounds*",
    "cyberpunk": "🌆 [CYBERPUNK GLITCH SYNTH]: H-E-L-L-O... {} [Error: Audio frequency unstable]",
    "opera": "🎭 [OPERA SOPRANO RESONANCE]: 🎶 ¡¡¡ {} !!! 🎶"
}

# 2. Web Server Route (Health Check for Cloud Hosting)
async def handle_health(request):
    return web.Response(text="EchoVocal Engine is active!")

# 3. Main Bot Logic (Async Long Polling)
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
                            text = message.get("text", "").strip()
                            
                            if not chat_id or not text:
                                continue
                                
                            reply_text = ""
                            
                            # Command: /start
                            if text.startswith("/start"):
                                reply_text = (
                                    "🎙️ **Welcome to EchoVocal!**\n\n"
                                    "I am a vocal styling and linguistic simulation bot. Send me any text, sentence, or catchphrase, and I will instantly process it through different vocal models and acoustic environments!\n\n"
                                    "👉 **Just type anything to begin!**"
                                )
                            else:
                                # Process the text through all vocal filters
                                reply_text = "🎛️ **EchoVocal Audio Rendering Results:**\n\n"
                                for style, template in ACCENTS.items():
                                    reply_text += f"{template.format(text)}\n\n"
                                
                                reply_text += "✨ _All audio profiles simulated locally without external APIs._"

                            if reply_text:
                                send_url = f"{API_URL}sendMessage"
                                payload = {"chat_id": chat_id, "text": reply_text, "parse_mode": "Markdown"}
                                await session.post(send_url, data=payload)
                                
            except Exception as e:
                print(f"Polling error: {e}")
                await asyncio.sleep(5)

# 4. Application Launcher
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
