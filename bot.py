import os
from collections import defaultdict
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, MessageHandler, filters
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
SYSTEM = os.getenv(
    "SYSTEM_PROMPT",
    "You are a friendly member of a Telegram group. "
    "Reply in the same language as the user, short and casual.",
)
history = defaultdict(list)


async def reply(update, context):
    msg = update.message
    if not msg or not msg.text:
        return

    me = context.bot.username
    if msg.chat.type in ("group", "supergroup"):
        mentioned = f"@{me}" in msg.text
        replied = (
            msg.reply_to_message
            and msg.reply_to_message.from_user
            and msg.reply_to_message.from_user.id == context.bot.id
        )
        if not (mentioned or replied):
            return

    text = msg.text.replace(f"@{me}", "").strip()
    h = history[msg.chat_id]
    h.append({"role": "user", "content": f"{msg.from_user.first_name}: {text}"})
    del h[:-20]  # only the last 20 messages

    await context.bot.send_chat_action(msg.chat_id, ChatAction.TYPING)
    r = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": SYSTEM}] + h,
    )
    answer = r.choices[0].message.content
    h.append({"role": "assistant", "content": answer})
    await msg.reply_text(answer)


app = ApplicationBuilder().token(os.environ["TELEGRAM_TOKEN"]).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
app.run_polling()
