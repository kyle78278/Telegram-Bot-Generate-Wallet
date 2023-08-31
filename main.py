import logging
import os
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from wallet import generate_private_key, generate_wallet, display_eth_balance, display_usdt_balance, withdraw_all_usdt, withdraw_all_eth
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
from enum import Enum, auto


filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

TELEGRAM_API_KEY = os.environ.get('TELEGRAM_API_KEY')

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


(START_ROUTES,
GENERATE_WALLET,
MAIN_MENU,
TRADE_MENU,
WALLET_MENU,) = range(5)
  
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    file_path = os.path.abspath(f"private_keys/{user_id}_private_key.txt")
    
    if os.path.exists(file_path):
        # If the user already has a wallet
        return await show_main_menu(update, context)
    else:
        # If the user doesn't have a wallet
        welcome_msg = "Hello, welcome to Customized Trading Bot. Please click 'Generate Wallet' to begin."
        keyboard = [[InlineKeyboardButton("Generate Wallet", callback_data="generate_wallet")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(welcome_msg, reply_markup=reply_markup)
        return START_ROUTES

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
    file_path = os.path.abspath(f"private_keys/{user_id}_private_key.txt")

    with open(file_path, "r") as f:
        private_key_str = f.read().strip()
    
    private_key = bytes.fromhex(private_key_str)
    address = generate_wallet(private_key)
    eth_balance = display_eth_balance(user_id)
    usdt_balance = display_usdt_balance(user_id)
    menu_msg = f"Current deposit address: `{address}`\nCurrent ETH balance: {eth_balance}\nCurrent USDT balance: {usdt_balance}"

    keyboard = [
        [InlineKeyboardButton("Trade", callback_data="show_trade_menu")],
        [InlineKeyboardButton("Wallet", callback_data="show_wallet_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(menu_msg, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.message.edit_text(menu_msg, reply_markup=reply_markup, parse_mode='Markdown')
    return MAIN_MENU

async def show_wallet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Refresh", callback_data="refresh_balance")],
        [InlineKeyboardButton("Show Private Key", callback_data="get_private_key")],
        [InlineKeyboardButton("Withdraw All ETH", callback_data="withdraw_all_eth")],
        [InlineKeyboardButton("Withdraw All USDT", callback_data="withdraw_all_usdt")],
        [InlineKeyboardButton("Back", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_reply_markup(reply_markup=reply_markup)
    return WALLET_MENU

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

async def generate_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    private_key = generate_private_key()
    wallet_address = generate_wallet(private_key)
    with open(f"private_keys/{user_id}_private_key.txt", "w") as f:
        f.write(private_key.hex())
    
    # Get the updated balances
    eth_balance = display_eth_balance(user_id)
    usdt_balance = display_usdt_balance(user_id)

    # Message to display deposit address and balances
    balance_msg = f"ERC20 deposit address: `{wallet_address}`\nCurrent ETH balance: {eth_balance}\nCurrent USDT balance: {usdt_balance}"

    # Update the keyboard buttons to be the same as when the user already has a wallet
    keyboard = [
        [InlineKeyboardButton("Trade", callback_data="show_trade_menu")],
        [InlineKeyboardButton("Wallet", callback_data="show_wallet_menu")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(balance_msg, reply_markup=reply_markup, parse_mode='Markdown')
    return MAIN_MENU

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
            return WALLET_MENU
    except Exception as e:
        await update.callback_query.message.reply_text("An error occurred.")
        return ConversationHandler.END

async def withdraw_all_usdt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("Please enter the destination address for USDT (Contract: 0xdAC17F958D2ee523a2206206994597C13D831ec7):")
    return WALLET_MENU

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

        return WALLET_MENU 
    except Exception as e:
        logger.error(f"An error occurred in refresh_balance: {e}")
        await update.callback_query.message.edit_text("An error occurred while refreshing the balance.")
        return ConversationHandler.END  # Make sure ConversationHandler is imported or defined


async def get_private_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id

    with open(f"private_keys/{user_id}_private_key.txt", "r") as f:
        private_key = f.read()

    warning_msg = ("Here is your private key. DO NOT SHARE IT WITH ANYONE OR YOU WILL LOSE YOUR FUNDS.\n\n"
                   f"Private key: `{private_key}`")

    keyboard = [
        [InlineKeyboardButton("Delete Wallet", callback_data="delete_wallet")],
        [InlineKeyboardButton("Back to Wallet Menu", callback_data="back_to_wallet_menu")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.message.reply_text(warning_msg, reply_markup=reply_markup, parse_mode='Markdown')
    return WALLET_MENU

async def delete_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Entered delete_wallet function")  # To confirm function entry

    # Immediately update the text to "Deleting..."
    await update.callback_query.message.edit_text("Deleting...")

    user_id = update.callback_query.from_user.id
    file_path = f"private_keys/{user_id}_private_key.txt"

    logging.info(f"Attempting to delete file: {file_path}")  # Debugging info

    try:
        os.remove(file_path)
        logging.info(f"Successfully deleted private key for user {user_id}")  # Debugging info

        # Update the text and add a "Generate Wallet" button
        keyboard = [
            [InlineKeyboardButton("Generate Wallet", callback_data="generate_wallet")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(
            "Your wallet has been successfully deleted. Click 'Generate Wallet' to get a new wallet address.",
            reply_markup=reply_markup
        )

        return START_ROUTES
    except FileNotFoundError:
        logging.error(f"Failed to delete private key for user {user_id}: File not found")  # Error log
        await update.callback_query.message.edit_text("Error: Private key file not found.")
        return START_ROUTES
    except Exception as e:
        logging.error(f"Failed to delete private key for user {user_id}: {e}")  # Error log
        await update.callback_query.message.edit_text("Error: Could not delete private key.")
        return START_ROUTES


async def after_delete_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Generate Wallet", callback_data="generate_wallet")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_reply_markup(reply_markup=reply_markup)
    return START_ROUTES

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

async def show_trade_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Back", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_reply_markup(reply_markup=reply_markup)
    return TRADE_MENU

AFTER_DELETE_WALLET = "AFTER_DELETE_WALLET"  # New state constant

def main() -> None:
    application = Application.builder().token(TELEGRAM_API_KEY).build()

    # Initialize the /start command handler
    start_handler = CommandHandler('start', start, block=True)

    # Initialize the conversation handler
    conv_handler = ConversationHandler(
        entry_points=[start_handler],
        states={
            START_ROUTES: [
                CallbackQueryHandler(generate_wallet_command, pattern='^generate_wallet$', block=True)
            ],
            GENERATE_WALLET: [
                CallbackQueryHandler(show_main_menu, pattern='^back_to_main$', block=True),
                CallbackQueryHandler(show_wallet_menu, pattern='^show_wallet_menu$', block=True),
                CallbackQueryHandler(show_trade_menu, pattern='^show_trade_menu$', block=True)
            ],
            MAIN_MENU: [
                CallbackQueryHandler(show_wallet_menu, pattern='^show_wallet_menu$', block=True),
                CallbackQueryHandler(show_trade_menu, pattern='^show_trade_menu$', block=True),
                CallbackQueryHandler(delete_wallet, pattern='^delete_wallet$', block=True),
            ],
            TRADE_MENU: [
                CallbackQueryHandler(show_main_menu, pattern='^back_to_main$', block=True)
            ],
            WALLET_MENU: [
                CallbackQueryHandler(get_private_key, pattern='^get_private_key$', block=True),
                CallbackQueryHandler(refresh_balance, pattern='^refresh_balance$', block=True),
                CallbackQueryHandler(withdraw_all_eth_command, pattern='^withdraw_all_eth$', block=True),
                CallbackQueryHandler(withdraw_all_usdt_command, pattern='^withdraw_all_usdt$', block=True),
                CallbackQueryHandler(show_wallet_menu, pattern='^back_to_wallet_menu$', block=True),
                CallbackQueryHandler(delete_wallet, pattern='^delete_wallet$', block=True),
                MessageHandler(filters.TEXT, input_eth_address, block=True)
            ],
        },
        fallbacks=[],
        map_to_parent={
        }
    )

    # Add the conversation handler to the application
    application.add_handler(conv_handler)

    # Run the application
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

