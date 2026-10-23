from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask
from threading import Thread
import logging
import os

# ================== TOKEN ==================
TOKEN = "8759339265:AAEtdNelfHf70H__ToMi3koRd6KncTeDZC8"
# ===========================================

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

games = {}

def create_board():
    return [[" " for _ in range(3)] for _ in range(3)]

def board_to_keyboard(board, game_id):
    keyboard = []
    for i in range(3):
        row = []
        for j in range(3):
            text = board[i][j] if board[i][j] != " " else "⬜"
            row.append(InlineKeyboardButton(text, callback_data=f"move_{game_id}_{i}_{j}"))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

def check_winner(board):
    lines = board + list(map(list, zip(*board)))
    lines.append([board[0][0], board[1][1], board[2][2]])
    lines.append([board[0][2], board[1][1], board[2][0]])
    for line in lines:
        if line[0] == line[1] == line[2] != " ":
            return line[0]
    return None

def is_full(board):
    return all(cell != " " for row in board for cell in row)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 *Tic-Tac-Toe Multiplayer Bot*\n\n"
        "/newgame - Naya game shuru karo\n"
        "/join - Game mein join karo\n"
        "/help - Help",
        parse_mode="Markdown"
    )

async def newgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id in games and games[chat_id].get("status") == "playing":
        await update.message.reply_text("Pehle current game khatam karo!")
        return

    games[chat_id] = {
        "board": create_board(),
        "player1": user.id,
        "player1_name": user.first_name,
        "player2": None,
        "player2_name": None,
        "turn": user.id,
        "status": "waiting",
        "symbol": {user.id: "❌"}
    }

    await update.message.reply_text(
        f"🎮 {user.first_name} ne naya game start kiya!\n\nDusra player /join likh kar join kare."
    )

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id not in games:
        await update.message.reply_text("Koi active game nahi hai. /newgame se shuru karo.")
        return

    game = games[chat_id]

    if game["status"] != "waiting":
        await update.message.reply_text("Game already chal raha hai.")
        return

    if user.id == game["player1"]:
        await update.message.reply_text("Tum pehle se player 1 ho!")
        return

    game["player2"] = user.id
    game["player2_name"] = user.first_name
    game["symbol"][user.id] = "⭕"
    game["status"] = "playing"

    text = (
        f"🎮 Game Start!\n\n"
        f"❌ {game['player1_name']} vs ⭕ {game['player2_name']}\n\n"
        f"Turn: {game['player1_name']} (❌)"
    )
    await update.message.reply_text(text, reply_markup=board_to_keyboard(game["board"], chat_id))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith("move_"):
        return

    _, game_id, row, col = data.split("_")
    game_id = int(game_id)
    row, col = int(row), int(col)

    if game_id not in games:
        await query.edit_message_text("Game khatam ho gaya.")
        return

    game = games[game_id]
    user_id = query.from_user.id

    if game["status"] != "playing":
        await query.answer("Game already khatam!", show_alert=True)
        return

    if user_id not in [game["player1"], game["player2"]]:
        await query.answer("Tum is game ke player nahi ho!", show_alert=True)
        return

    if user_id != game["turn"]:
        await query.answer("Abhi tumhari baari nahi hai!", show_alert=True)
        return

    board = game["board"]
    if board[row][col] != " ":
        await query.answer("Ye jagah already bhara hua hai!", show_alert=True)
        return

    symbol = game["symbol"][user_id]
    board[row][col] = symbol

    winner = check_winner(board)
    if winner:
        winner_name = game["player1_name"] if winner == "❌" else game["player2_name"]
        text = f"🏆 *{winner_name}* jeet gaya! ({winner})\n\nGame Over!"
        game["status"] = "finished"
        await query.edit_message_text(text, reply_markup=board_to_keyboard(board, game_id), parse_mode="Markdown")
        return

    if is_full(board):
        text = "🤝 Draw ho gaya!\n\nGame Over!"
        game["status"] = "finished"
        await query.edit_message_text(text, reply_markup=board_to_keyboard(board, game_id))
        return

    if game["turn"] == game["player1"]:
        game["turn"] = game["player2"]
        next_name = game["player2_name"]
        next_symbol = "⭕"
    else:
        game["turn"] = game["player1"]
        next_name = game["player1_name"]
        next_symbol = "❌"

    text = (
        f"🎮 *Tic-Tac-Toe*\n\n"
        f"❌ {game['player1_name']} vs ⭕ {game['player2_name']}\n\n"
        f"Turn: {next_name} ({next_symbol})"
    )
    await query.edit_message_text(text, reply_markup=board_to_keyboard(board, game_id), parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 *Kaise khele?*\n\n1. /newgame\n2. Dusra player /join\n3. Buttons se move karo",
        parse_mode="Markdown"
    )

# ---------- Keep Alive (Render ke liye) ----------
app = Flask('')

@app.route('/')
def home():
    return "Bot is Alive!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

def main():
    keep_alive()
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("newgame", newgame))
    application.add_handler(CommandHandler("join", join))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Bot started...")
    application.run_polling()

if __name__ == "__main__":
    main()
