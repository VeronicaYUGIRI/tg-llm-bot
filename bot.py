import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

import db
import llm

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-opus-4.7")
DEFAULT_WINDOW_SIZE = int(os.getenv("HISTORY_WINDOW_SIZE", "20"))

_allowed_chat_ids_raw = os.getenv("ALLOWED_CHAT_IDS", "").strip()
ALLOWED_CHAT_IDS = (
    {int(x.strip()) for x in _allowed_chat_ids_raw.split(",") if x.strip()}
    if _allowed_chat_ids_raw
    else None
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# chat_id -> list of {"role": "user"/"assistant", "content": str}
chat_histories: dict[int, list] = {}


def trim_history(history, max_messages):
    if len(history) > max_messages:
        del history[: len(history) - max_messages]


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Only records the message into the rolling history. Does not call the LLM."""
    message = update.message
    if message is None or not message.text:
        return

    chat_id = message.chat_id
    user = message.from_user
    username = user.username or user.first_name or str(user.id)

    settings = db.get_chat_settings(chat_id, DEFAULT_MODEL, DEFAULT_WINDOW_SIZE)
    max_messages = settings["window_size"]

    history = chat_histories.setdefault(chat_id, [])
    history.append({"role": "user", "content": f"{username}: {message.text}"})
    trim_history(history, max_messages)


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggers an LLM call using the accumulated history."""
    message = update.message
    chat_id = message.chat_id
    user = message.from_user
    username = user.username or user.first_name or str(user.id)

    settings = db.get_chat_settings(chat_id, DEFAULT_MODEL, DEFAULT_WINDOW_SIZE)
    model = settings["model"]
    max_messages = settings["window_size"]

    history = chat_histories.setdefault(chat_id, [])

    extra_text = " ".join(context.args) if context.args else ""
    if extra_text:
        history.append({"role": "user", "content": f"{username}: {extra_text}"})
        trim_history(history, max_messages)

    if not history:
        await message.reply_text("暂时没有可供回复的历史消息。")
        return

    try:
        result = await llm.call_llm(history, model, OPENROUTER_API_KEY)
    except Exception:
        logger.exception("LLM call failed")
        await message.reply_text("调用 LLM 失败,请稍后再试。")
        return

    history.append({"role": "assistant", "content": result["reply"]})
    trim_history(history, max_messages)

    timestamp = datetime.now(timezone.utc).isoformat()
    db.log_usage(
        chat_id=chat_id,
        user_id=user.id,
        username=username,
        model=model,
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
        cost=result["cost"],
        timestamp=timestamp,
    )

    totals = db.get_chat_total_cost(chat_id)
    total_tokens = result["prompt_tokens"] + result["completion_tokens"]
    usage_line = (
        f"_🤖 {model}\n"
        f"本次消耗 {total_tokens} tokens,花费 ${result['cost']:.4f}\n"
        f"累计 {totals['total_tokens']} tokens,累计花费 ${totals['total_cost']:.4f}_"
    )

    await message.reply_text(
        f"{result['reply']}\n\n{usage_line}",
        parse_mode=ParseMode.MARKDOWN,
    )


async def usage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    totals = db.get_chat_total_cost(chat_id)
    await update.message.reply_text(
        f"累计调用次数: {totals['call_count']}\n"
        f"累计 token 数: {totals['total_tokens']}\n"
        f"累计花费: ${totals['total_cost']:.4f}"
    )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    chat_histories[chat_id] = []
    await update.message.reply_text("对话历史已清空。")


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    settings = db.get_chat_settings(chat_id, DEFAULT_MODEL, DEFAULT_WINDOW_SIZE)
    totals = db.get_chat_total_cost(chat_id)
    history_len = len(chat_histories.get(chat_id, []))
    max_messages = settings["window_size"]
    await update.message.reply_text(
        f"当前模型: {settings['model']}\n"
        f"历史消息上限: {max_messages} 条\n"
        f"当前已缓存: {history_len}/{max_messages} 条\n"
        f"累计调用次数: {totals['call_count']}\n"
        f"累计 token 数: {totals['total_tokens']}\n"
        f"累计花费: ${totals['total_cost']:.4f}"
    )


async def setmodel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if not context.args:
        await update.message.reply_text("用法: /setmodel <模型ID>,例如 /setmodel anthropic/claude-opus-4.7")
        return
    model = context.args[0]
    db.set_chat_model(chat_id, model, DEFAULT_WINDOW_SIZE)
    await update.message.reply_text(f"已将本群模型设置为: {model}")


async def setwindow_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("用法: /setwindow <数字>,例如 /setwindow 20(表示最多保留20条消息)")
        return
    max_messages = int(context.args[0])
    db.set_chat_window_size(chat_id, max_messages, DEFAULT_MODEL)
    await update.message.reply_text(f"已将本群历史消息上限设置为: {max_messages} 条")


async def chatid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Not restricted by the allowlist, so you can always look up a chat_id."""
    await update.message.reply_text(f"本群 chat_id: {update.message.chat_id}")


async def dumphistory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug helper: show the raw in-memory history list for this chat."""
    chat_id = update.message.chat_id
    history = chat_histories.get(chat_id, [])
    if not history:
        await update.message.reply_text("当前历史记录为空。")
        return
    lines = [f"[{i}] {item['role']}: {item['content']}" for i, item in enumerate(history, start=1)]
    text = "\n".join(lines)
    if len(text) > 3500:
        text = text[-3500:]
    await update.message.reply_text(text)


def main():
    db.init_db()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # /chatid is never restricted, so you can always look up a chat's id.
    app.add_handler(CommandHandler("chatid", chatid_command))

    chat_filter = filters.Chat(chat_id=ALLOWED_CHAT_IDS) if ALLOWED_CHAT_IDS else filters.ALL

    app.add_handler(CommandHandler("ask", ask_command, filters=chat_filter))
    app.add_handler(CommandHandler("usage", usage_command, filters=chat_filter))
    app.add_handler(CommandHandler("settings", settings_command, filters=chat_filter))
    app.add_handler(CommandHandler("reset", reset_command, filters=chat_filter))
    app.add_handler(CommandHandler("setmodel", setmodel_command, filters=chat_filter))
    app.add_handler(CommandHandler("setwindow", setwindow_command, filters=chat_filter))
    app.add_handler(CommandHandler("dumphistory", dumphistory_command, filters=chat_filter))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & chat_filter, handle_message))

    if ALLOWED_CHAT_IDS:
        logger.info("Restricting bot to chat_ids: %s", ALLOWED_CHAT_IDS)
    else:
        logger.warning("ALLOWED_CHAT_IDS is not set - bot will respond in ANY chat it's added to.")

    logger.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
