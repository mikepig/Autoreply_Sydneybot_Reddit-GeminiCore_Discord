import os, json, asyncio, logging, re, discord
from datetime import timedelta
from geminibot_utils import ask_gemini


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

with open("config.json", encoding="utf-8") as f:
    CFG = json.load(f)

API_KEYS = [k.strip() for k in CFG.get("gemini_api_key", "").split("|") if k.strip()]


pers_cfg = CFG.get("persona", "").strip()
if pers_cfg.lower().endswith(".txt") and os.path.exists(pers_cfg):
    with open(pers_cfg, encoding="utf-8") as f:
        PERSONA = f.read()
else:
    PERSONA = pers_cfg

if not PERSONA.strip():
    PERSONA = "You are a helpful assistant."

TRIG_WORDS = CFG.get("trigger_keywords", [])
if isinstance(TRIG_WORDS, str):
    TRIG_WORDS = [TRIG_WORDS]
TRIG_WORDS = [w.lower() for w in TRIG_WORDS]

TOKEN = os.getenv("DISCORD_TOKEN") or CFG.get("discord_token")
if not TOKEN:
    raise RuntimeError("❌  Discord Token 未提供！")

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

COOLDOWN_SEC = 3
_last_reply: dict[int, discord.utils.utcnow] = {}


def should_trigger(msg: discord.Message) -> bool:
    """决定是否触发回复"""
    if msg.author.bot:
        return False
    if bot.user in msg.mentions:
        return True
    content_lower = msg.content.lower()
    return any(w in content_lower for w in TRIG_WORDS)
@bot.event
async def on_ready():
    logger.info("Logged in as %s (%s)", bot.user, bot.user.id)

@bot.event
async def on_message(message: discord.Message):
    if not should_trigger(message):
        return

    
    now = discord.utils.utcnow()
    if (prev := _last_reply.get(message.channel.id)) and (now - prev).total_seconds() < COOLDOWN_SEC:
        return
    _last_reply[message.channel.id] = now

    
    text = re.sub(fr"<@!?{bot.user.id}>", "", message.content).strip()
    if not text:
        text = "Hello"

   
    messages = [
        {"role": "user", "parts": [text]}
    ]

    try:
        async with message.channel.typing():
            reply = await asyncio.to_thread(
                ask_gemini,
                messages=messages,
                api_keys=API_KEYS,
                system_prompt=PERSONA,
            )
        
        for chunk in [reply[i:i + 2000] for i in range(0, len(reply), 2000)]:
            await message.reply(chunk, mention_author=False)
    except Exception as exc:
        logger.exception("Gemini 调用失败")
        await message.reply(f"⚠️ 出错：{exc}")

if __name__ == "__main__":
    bot.run(TOKEN)
