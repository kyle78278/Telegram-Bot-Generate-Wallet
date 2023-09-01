import logging
import os
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from wallet import generate_private_key, generate_wallet, display_eth_balance, display_usdc_balance, withdraw_all_usdc, withdraw_all_eth
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning


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
WALLET_MENU,
WITHDRAWL,
INPUT_ETH_ADDRESS,
INPUT_USDC_ADDRESS) = range(8)
  
async def read_or_generate_private_key(user_id):
    file_path = os.path.abspath(f"private_keys/{user_id}_private_key.txt")
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            private_key_str = f.read().strip()
        if len(private_key_str) == 64:
            return bytes.fromhex(private_key_str)
        else:
            os.remove(file_path)
    new_private_key = generate_private_key()
    with open(file_path, "w") as f:
        f.write(new_private_key.hex())
    return new_private_key

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    private_key = await read_or_generate_private_key(user_id)
    if private_key:
        return await show_main_menu(update, context)
    else:
        welcome_msg = "Hello, welcome to Customized Trading Bot. Please click 'Generate Wallet' to begin."
        keyboard = [[InlineKeyboardButton("Generate Wallet", callback_data="generate_wallet")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(welcome_msg, reply_markup=reply_markup)
        return START_ROUTES

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
    file_path = os.path.abspath(f"private_keys/{user_id}_private_key.txt")
    if not os.path.exists(file_path):
        return await start(update, context)
    with open(file_path, "r") as f:
        private_key_str = f.read().strip()
    private_key = bytes.fromhex(private_key_str)
    address = generate_wallet(private_key)
    eth_balance = display_eth_balance(user_id)
    usdc_balance = display_usdc_balance(user_id)
    menu_msg = f"Current deposit address: `{address}`\nCurrent ETH balance: {eth_balance}\nCurrent USDC balance: {usdc_balance}"
    keyboard = [
        [InlineKeyboardButton("Trade", callback_data="show_trade_menu")],
        [InlineKeyboardButton("Wallet", callback_data="show_wallet_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(menu_msg, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.message.edit_text(menu_msg, reply_markup=reply_markup, parse_mode='Markdown')
    context.user_data['state'] = MAIN_MENU
    return MAIN_MENU

async def show_wallet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user_id = update.callback_query.from_user.id if update.callback_query else update.message.from_user.id
        eth_balance = display_eth_balance(user_id)
        usdc_balance = display_usdc_balance(user_id)
        if eth_balance is None or usdc_balance is None:
            print("Error: Couldn't fetch balances.")
            return WALLET_MENU
        eth_balance = float(eth_balance)
        usdc_balance = float(usdc_balance)
        file_path = os.path.abspath(f"private_keys/{user_id}_private_key.txt")
        with open(file_path, "r") as f:
            private_key_str = f.read().strip()
        private_key = bytes.fromhex(private_key_str)
        address = generate_wallet(private_key)
        balance_msg = f"Current deposit address: `{address}`\nCurrent ETH balance: {eth_balance}\nCurrent USDC balance: {usdc_balance}"
        keyboard = [
            [InlineKeyboardButton("Refresh", callback_data="refresh_balance")],
            [InlineKeyboardButton("Show Private Key", callback_data="get_private_key")],
            [InlineKeyboardButton("Back", callback_data="back_to_main")]
        ]
        if eth_balance > 0:
            keyboard.insert(2, [InlineKeyboardButton("Withdraw All ETH", callback_data="withdraw_all_eth")])
        if usdc_balance > 0:
            keyboard.insert(3, [InlineKeyboardButton("Withdraw All USDC", callback_data="withdraw_all_usdc")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.callback_query:
            await update.callback_query.message.edit_text(balance_msg, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(balance_msg, reply_markup=reply_markup, parse_mode='Markdown')
        return WALLET_MENU
    except Exception as e:
        print(f"An error occurred: {e}")
        return WALLET_MENU


async def generate_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    private_key = generate_private_key()
    wallet_address = generate_wallet(private_key)
    with open(f"private_keys/{user_id}_private_key.txt", "w") as f:
        f.write(private_key.hex())
    eth_balance = display_eth_balance(user_id)
    usdc_balance = display_usdc_balance(user_id)
    balance_msg = f"ERC20 deposit address: `{wallet_address}`\nCurrent ETH balance: {eth_balance}\nCurrent USDC balance: {usdc_balance}"
    keyboard = [
        [InlineKeyboardButton("Trade", callback_data="show_trade_menu")],
        [InlineKeyboardButton("Wallet", callback_data="show_wallet_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(balance_msg, reply_markup=reply_markup, parse_mode='Markdown')
    return MAIN_MENU

async def input_eth_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    to_address = update.message.text
    if re.match("^0x[a-fA-F0-9]{40}$", to_address):
        try:
            result = await withdraw_all_eth(user_id, to_address)
            if "Transaction sent with hash:" in result:
                await update.message.reply_text(result)
                logger.info("Transaction successful for user_id: %s, to_address: %s", user_id, to_address)
        except Exception as e:
            await update.message.reply_text("An error occurred.")
            logger.error("An exception occurred: %s", str(e))
    else:
        await update.message.reply_text("Invalid Ethereum address. Please try again.")
    return await start(update, context)

async def input_usdc_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Entered input_usdc_address")
    user_id = update.message.from_user.id
    to_address = update.message.text
    usdc_contract_address = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48' 
    if re.match("^0x[a-fA-F0-9]{40}$", to_address):
        try:
            result = await withdraw_all_usdc(user_id, to_address, usdc_contract_address)
            if "Transaction sent with hash:" in result:
                await update.message.reply_text(result)
                logger.info("Transaction successful for user_id: %s, to_address: %s", user_id, to_address)
            else:
                await update.message.reply_text("Failed to send USDC. Please try again.")
        except Exception as e:
            await update.message.reply_text("An error occurred.")
            logger.error("An exception occurred: %s", str(e))
    else:
        await update.message.reply_text("Invalid Ethereum address. Please try again.")
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

async def withdraw_all_usdc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    usdc_balance_str = display_usdc_balance(user_id) 
    try:
        usdc_balance = float(usdc_balance_str)
        if usdc_balance <= 0:
            await update.callback_query.message.reply_text("This address has no USDC!")
            return END_ROUTES
        else:
            await update.callback_query.message.reply_text("Please enter the destination address for USDC:")
            return INPUT_USDC_ADDRESS
    except Exception as e:
        await update.callback_query.message.reply_text("An error occurred.")
        return ConversationHandler.END

async def refresh_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user_id = update.callback_query.from_user.id
        await update.callback_query.message.edit_text("Refreshing ...")
        eth_balance = display_eth_balance(user_id)
        usdc_balance = display_usdc_balance(user_id)
        file_path = os.path.abspath(f"private_keys/{user_id}_private_key.txt")
        with open(file_path, "r") as f:
            private_key_str = f.read().strip()
        private_key = bytes.fromhex(private_key_str)
        address = generate_wallet(private_key)
        balance_msg = f"Current deposit address: `{address}`\nCurrent ETH balance: {eth_balance}\nCurrent USDC balance: {usdc_balance}"
        keyboard = [
            [InlineKeyboardButton("Refresh", callback_data="refresh_balance")],
            [InlineKeyboardButton("Show Private Key", callback_data="get_private_key")],
            [InlineKeyboardButton("Back", callback_data="back_to_main")]
        ]
        if float(eth_balance) > 0:
            keyboard.insert(-1, [InlineKeyboardButton("Withdraw All ETH", callback_data="withdraw_all_eth")])
        if float(usdc_balance) > 0:
            keyboard.insert(-1, [InlineKeyboardButton("Withdraw All USDC", callback_data="withdraw_all_usdc")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(balance_msg, reply_markup=reply_markup, parse_mode='Markdown')
        return WALLET_MENU
    except Exception as e:
        logger.error(f"An error occurred in refresh_balance: {e}")
        await update.callback_query.message.edit_text("An error occurred while refreshing the balance.")
        return ConversationHandler.END

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
    await update.callback_query.message.edit_text(warning_msg, reply_markup=reply_markup, parse_mode='Markdown')
    return WALLET_MENU

async def delete_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Entered delete_wallet function")
    await update.callback_query.message.edit_text("Deleting...")
    user_id = update.callback_query.from_user.id
    file_path = f"private_keys/{user_id}_private_key.txt"
    logging.info(f"Attempting to delete file: {file_path}")
    try:
        os.remove(file_path)
        logging.info(f"Successfully deleted private key for user {user_id}")
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
        logging.error(f"Failed to delete private key for user {user_id}: File not found")
        await update.callback_query.message.edit_text("Error: Private key file not found.")
        return START_ROUTES
    except Exception as e:
        logging.error(f"Failed to delete private key for user {user_id}: {e}") 
        await update.callback_query.message.edit_text("Error: Could not delete private key.")
        return START_ROUTES


async def show_trade_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Back", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_reply_markup(reply_markup=reply_markup)
    return TRADE_MENU

def main() -> None:
    application = Application.builder().token(TELEGRAM_API_KEY).build()
    start_handler = CommandHandler('start', start, block=True)
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
    CallbackQueryHandler(show_wallet_menu, pattern='^back_to_wallet_menu$', block=True),
    CallbackQueryHandler(show_main_menu, pattern='^back_to_main$', block=True),
    CallbackQueryHandler(delete_wallet, pattern='^delete_wallet$', block=True),
    CallbackQueryHandler(withdraw_all_eth_command, pattern='^withdraw_all_eth$', block=True),
    CallbackQueryHandler(withdraw_all_usdc_command, pattern='^withdraw_all_usdc$', block=True),
],
            INPUT_USDC_ADDRESS: [
    MessageHandler(filters.TEXT, input_usdc_address, block=True)
],
            INPUT_ETH_ADDRESS: [
    MessageHandler(filters.TEXT, input_eth_address, block=True)
]  
        },
        fallbacks=[start_handler],
        map_to_parent={
        }
    )
    application.add_handler(conv_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()