import os, json, asyncio, logging, re, base64, textwrap, discord
from datetime import timedelta
from geminibot_utils import ask_gemini    
import google.generativeai as genai
from google.generativeai.types.safety_types import (
    HarmCategory, HarmBlockThreshold,
)

VISION_MODEL = "gemini-1.5-flash-latest"
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT:        HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH:       HarmBlockThreshold.BLOCK_NONE,
}
logging.basicConfig(level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

with open("config.json", encoding="utf-8") as f:
    CFG = json.load(f)

API_KEYS = [k.strip() for k in CFG.get("gemini_api_key", "").split("|") if k.strip()]
if not API_KEYS:
    raise RuntimeError("gemini_api_key 为空！")

pers_cfg = CFG.get("persona", "").strip()
if pers_cfg.lower().endswith(".txt") and os.path.exists(pers_cfg):
    PERSONA = open(pers_cfg, encoding="utf-8").read()
else:
    PERSONA = pers_cfg or "You are a helpful assistant."
TRIG_WORDS = CFG.get("trigger_keywords", [])
if isinstance(TRIG_WORDS, str):
    TRIG_WORDS = [TRIG_WORDS]
TRIG_WORDS = [w.lower() for w in TRIG_WORDS]

TOKEN = os.getenv("DISCORD_TOKEN") or CFG.get("discord_token")
if not TOKEN:
    raise RuntimeError("Discord TOKEN 缺失！")

# ──────────────── Discord ────────────────
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

COOLDOWN_SEC = 3
_last_reply: dict[int, float] = {}

def ask_gemini_vision(image_parts, text="", api_key="", system_prompt=""):
    genai.configure(api_key=api_key or API_KEYS[0])
    model = genai.GenerativeModel(VISION_MODEL, safety_settings=SAFETY_SETTINGS,
                                  system_instruction=system_prompt.strip())
    parts = image_parts[:]
    if text:
        parts.append(text)
    return model.generate_content(parts).text.strip()

async def build_image_parts(atts: list[discord.Attachment]):
    parts = []
    for att in atts:
        if att.content_type and att.content_type.startswith("image"):
            try:
                data = await att.read()
                parts.append({"mime_type": att.content_type, "data": base64.b64encode(data).decode()})
            except Exception as e:
                logger.warning("读取图片失败 %s: %s", att.filename, e)
    return parts

def should_trigger(msg: discord.Message):
    if msg.author.bot:
        return False
    if bot.user in msg.mentions:
        return True
    return any(w in msg.content.lower() for w in TRIG_WORDS)

@bot.event
async def on_ready():
    logger.info("Logged in as %s (%s)", bot.user, bot.user.id)

@bot.event
async def on_message(message: discord.Message):
    if not should_trigger(message):
        return
    now = discord.utils.utcnow().timestamp()
    if now - _last_reply.get(message.channel.id, 0) < COOLDOWN_SEC:
        return
    _last_reply[message.channel.id] = now
    text = re.sub(fr"<@!?{bot.user.id}>", "", message.content).strip()
    img_parts = await build_image_parts(message.attachments)

    try:
        async with message.channel.typing():
            if img_parts:
                reply = await asyncio.to_thread(
                    ask_gemini_vision,
                    image_parts=img_parts,
                    text=text or "请评价这张图片。",
                    api_key=API_KEYS[0],
                    system_prompt=PERSONA,
                )
            else:
                prompt = text or "Hello"
                reply = await asyncio.to_thread(
                    ask_gemini,
                    messages=[{"role": "user", "parts": [prompt]}],
                    api_keys=API_KEYS,
                    system_prompt=PERSONA,
                )
        if len(reply) <= 2000:
            await message.reply(reply, mention_author=False)
        else:
            for chunk in textwrap.wrap(reply, 2000, break_long_words=False, replace_whitespace=False):
                await message.reply(chunk, mention_author=False)

    except Exception as e:
        logger.exception("Gemini 调用失败")
        await message.reply(f"⚠️ 出错：{e}")

# ───────────────
if __name__ == "__main__":
    bot.run(TOKEN)
