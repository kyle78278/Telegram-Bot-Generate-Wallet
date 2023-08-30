from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)
from wallet import generate_private_key, generate_wallet, display_eth_balance, display_usdt_balance, withdraw_all_usdt, withdraw_all_eth
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
import logging
import os
import re

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

TELEGRAM_API_KEY = os.environ.get('TELEGRAM_API_KEY')

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("error_logs.txt"),
        logging.StreamHandler()
    ]
)

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


START_ROUTES, END_ROUTES, INPUT_ETH_ADDRESS, INPUT_USDT_ADDRESS = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    file_path = os.path.abspath(f"private_keys/{user_id}_private_key.txt")
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            private_key_str = f.read().strip()
        private_key = bytes.fromhex(private_key_str)
        address = generate_wallet(private_key)
        eth_balance = display_eth_balance(user_id)
        usdt_balance = display_usdt_balance(user_id)
        welcome_msg = f"Current deposit address: `{address}`\nCurrent ETH balance: {eth_balance}\nCurrent USDT balance: {usdt_balance}"
        keyboard = [
            [InlineKeyboardButton("Refresh", callback_data="refresh_balance")],
            [InlineKeyboardButton("Show Private Key", callback_data="get_private_key")],
            [InlineKeyboardButton("Withdraw All ETH", callback_data="withdraw_all_eth")],
            [InlineKeyboardButton("Withdraw All USDT", callback_data="withdraw_all_usdt")]
        ]
    else:
        welcome_msg = "Hello, welcome to Customized Trading Bot. Please click 'Generate Wallet' to begin."
        keyboard = [[InlineKeyboardButton("Generate Wallet", callback_data="generate_wallet")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_msg, reply_markup=reply_markup, parse_mode='Markdown')
    return START_ROUTES

async def input_eth_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    to_address = update.message.text

    # Validate Ethereum address
    if re.match("^0x[a-fA-F0-9]{40}$", to_address):
        try:
            result = await withdraw_all_eth(user_id, to_address)  # Make sure to await here
            if "Transaction sent with hash:" in result:
                await update.message.reply_text(result)
                logger.info("Transaction successful for user_id: %s, to_address: %s", user_id, to_address)
        except Exception as e:
            await update.message.reply_text("An error occurred.")
            logger.error("An exception occurred: %s", str(e))
    else:
        await update.message.reply_text("Invalid Ethereum address. Please try again.")

    return await start(update, context)

async def input_usdt_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Entered input_eth_address")
    user_id = update.message.from_user.id
    to_address = update.message.text
    usdt_contract_address = '0xdAC17F958D2ee523a2206206994597C13D831ec7'
    result = withdraw_all_usdt(user_id, to_address, usdt_contract_address)
    await update.message.reply_text(result)
    return await start(update, context)

async def withdraw_all_eth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    eth_balance_str = display_eth_balance(user_id)
    
    try:
        eth_balance = float(eth_balance_str)
        
        if eth_balance <= 0:
            await update.callback_query.message.reply_text("This address has no ETH!")
            return END_ROUTES
        else:
            await update.callback_query.message.reply_text("Please enter the destination address for ETH:")
            return INPUT_ETH_ADDRESS
    except Exception as e:
        await update.callback_query.message.reply_text("An error occurred.")
        return ConversationHandler.END

async def withdraw_all_usdt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("Please enter the destination address for USDT (Contract: 0xdAC17F958D2ee523a2206206994597C13D831ec7):")
    return INPUT_USDT_ADDRESS

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

        return START_ROUTES 
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

    start_handler = CommandHandler('start', start, block=True)

    conv_handler = ConversationHandler(
        entry_points=[start_handler],
        states={
            START_ROUTES: [
                CallbackQueryHandler(generate_wallet_command, pattern='^generate_wallet$', block=True),
                CallbackQueryHandler(get_private_key, pattern='^get_private_key$', block=True),
                CallbackQueryHandler(withdraw_all_eth_command, pattern='^withdraw_all_eth$', block=True),
                CallbackQueryHandler(withdraw_all_usdt_command, pattern='^withdraw_all_usdt$', block=True),
                CallbackQueryHandler(refresh_balance, pattern='^refresh_balance$', block=True)
            ],
            INPUT_ETH_ADDRESS: [
                MessageHandler(filters.TEXT, input_eth_address, block=True)
            ],
            # ... (other states)
        },
        fallbacks=[],
        map_to_parent={
            # ... (map_to_parent)
        }
    )
    
    application.add_handler(conv_handler)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()