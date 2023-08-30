from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)
from wallet import generate_private_key, generate_wallet, display_eth_balance,display_usdt_balance
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
import logging
import os

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

TELEGRAM_API_KEY = os.environ.get('TELEGRAM_API_KEY')

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

START_ROUTES, END_ROUTES = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    file_path = os.path.abspath(f"private_keys/{user_id}_private_key.txt")
    
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            private_key_str = f.read().strip()
        
        # Convert the private key to bytes
        private_key = bytes.fromhex(private_key_str)
        
        address = generate_wallet(private_key)
        eth_balance = display_eth_balance(user_id)
        usdt_balance = display_usdt_balance(user_id)  # Assuming you have this function

        welcome_msg = f"Current deposit address: `{address}`\nCurrent ETH balance: {eth_balance}\nCurrent USDT balance: {usdt_balance}"
        keyboard = [
            [InlineKeyboardButton("Get Private Key", callback_data="get_private_key")],
            [InlineKeyboardButton("Refresh Balance", callback_data="refresh_balance")]
        ]
    else:
        welcome_msg = "Hello, welcome to Customized Trading Bot. Please click 'Generate Wallet' to begin."
        keyboard = [[InlineKeyboardButton("Generate Wallet", callback_data="generate_wallet")]]
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_msg, reply_markup=reply_markup, parse_mode='Markdown')
    return START_ROUTES

async def refresh_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        # Step 1: User clicks refresh
        user_id = update.callback_query.from_user.id

        # Step 2: Menu and balance disappear, replaced with "Refreshing..."
        await update.callback_query.message.edit_text("Refreshing ...")

        # Fetch the updated balances
        eth_balance = display_eth_balance(user_id)  # Assuming this function returns ETH balance
        usdt_balance = display_usdt_balance(user_id)  # Assuming you have this function

        # Fetch the deposit address
        file_path = os.path.abspath(f"private_keys/{user_id}_private_key.txt")
    
    #if os.path.exists(file_path):
        with open(file_path, "r") as f:
            private_key_str = f.read().strip()
        
        # Convert the private key to bytes
        private_key = bytes.fromhex(private_key_str)
        address = generate_wallet(private_key)

        # Step 3: Balance, deposit address, and buttons reappear with refreshed values
        balance_msg = f"Current deposit address: `{address}`\nCurrent ETH balance: {eth_balance}\nCurrent USDT balance: {usdt_balance}"
        keyboard = [
            [InlineKeyboardButton("Get Private Key", callback_data="get_private_key")],
            [InlineKeyboardButton("Refresh Balance", callback_data="refresh_balance")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(balance_msg, reply_markup=reply_markup, parse_mode='Markdown')

        return END_ROUTES  # Make sure END_ROUTES is defined
    except Exception as e:
        logger.error(f"An error occurred in refresh_balance: {e}")
        await update.callback_query.message.edit_text("An error occurred while refreshing the balance.")
        return ConversationHandler.END  # Make sure ConversationHandler is imported or defined

async def generate_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    private_key = generate_private_key()
    wallet_address = generate_wallet(private_key)
    with open(f"private_keys/{user_id}_private_key.txt", "w") as f:
        f.write(private_key.hex())
    keyboard = [
        [InlineKeyboardButton("Get Private Key", callback_data="get_private_key"),
         InlineKeyboardButton("Show ETH Balance", callback_data="show_eth_balance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(f"ERC20 deposit address: {wallet_address}", reply_markup=reply_markup)
    return END_ROUTES

async def get_private_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    with open(f"private_keys/{user_id}_private_key.txt", "r") as f:
        private_key = f.read()
    await update.callback_query.message.reply_text(f"Your stored Private Key: {private_key}")
    return END_ROUTES

async def show_my_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    with open(f"private_keys/{user_id}_private_key.txt", "r") as f:
        private_key = f.read()
    private_key_bytes = bytes.fromhex(private_key)  # Convert to byte string
    wallet_address = generate_wallet(private_key_bytes)  # Pass byte string
    keyboard = [
        [InlineKeyboardButton("Get Private Key", callback_data="get_private_key"),
         InlineKeyboardButton("Show ETH Balance", callback_data="show_eth_balance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(f"ERC20 deposit address: {wallet_address}", reply_markup=reply_markup)
    return END_ROUTES


async def show_eth_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user_id = update.callback_query.from_user.id  # Extract user_id here
        balance = display_eth_balance(user_id)  # Pass user_id as an argument
        await update.callback_query.message.reply_text(f"Your ETH Balance: {balance}")
        return END_ROUTES
    except Exception as e:
        logger.error(f"An error occurred in show_eth_balance: {e}")
        await update.callback_query.message.reply_text(f"An error occurred while retrieving the ETH balance: {e}")
        return ConversationHandler.END


def main() -> None:
    application = Application.builder().token(TELEGRAM_API_KEY).build()
    
    # Command Handlers
    start_handler = CommandHandler('start', start)
    
    # Callback Query Handlers
    generate_wallet_handler = CallbackQueryHandler(generate_wallet_command, pattern='^generate_wallet$')
    get_private_key_handler = CallbackQueryHandler(get_private_key, pattern='^get_private_key$')
    show_my_wallet_handler = CallbackQueryHandler(show_my_wallet, pattern='^show_my_wallet$')
    show_eth_balance_handler = CallbackQueryHandler(show_eth_balance, pattern='^show_eth_balance$')
    refresh_balance_handler = CallbackQueryHandler(refresh_balance, pattern='^refresh_balance$')  # New handler
    
    # Add Handlers to Application
    application.add_handler(start_handler)
    application.add_handler(generate_wallet_handler)
    application.add_handler(get_private_key_handler)
    application.add_handler(show_my_wallet_handler)
    application.add_handler(show_eth_balance_handler)
    application.add_handler(refresh_balance_handler)  # Add the new handler here
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

