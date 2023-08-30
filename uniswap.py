from uniswap import Uniswap
import requests
import os
import datetime
import time
import threading
import logging
from wallet import generate_private_key, generate_wallet
from API import INFURA_API_KEY, ETHERSCAN_API_KEY

# Constants
WETH_ADDRESS = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
USDT_ADDRESS = '0xdAC17F958D2ee523a2206206994597C13D831ec7'

INFURA_API_KEY = os.environ.get('INFURA_API_KEY')
ETHERSCAN_API_KEY = os.environ.get('ETHERSCAN_API_KEY')


# Initialize the Uniswap object
uniswap = Uniswap(address=address, private_key=private_key, version=3)

def new_wallet_command(update, context):
    # Generate a new private key using the imported function
    private_key = generate_private_key()
    
    # Generate a new wallet address using the imported function
    wallet_address = generate_wallet(private_key)
    
    # Send the generated private key and wallet address to the Telegram chat
    update.message.reply_text(f"Generated Private Key: {private_key.hex()}\nGenerated Wallet Address: {wallet_address}")


def get_weth_price(uniswap_instance):
    price = uniswap_instance.get_price_input(WETH_ADDRESS, USDT_ADDRESS, 10**18)
    return price / (10**6)  # Convert the price from the smallest unit of USDT (6 decimals) to a regular float

def log_price_to_file(price):
    with open("weth_price_log.txt", "a") as file:
        file.write(f"{datetime.datetime.now()}: WETH price = {price} USDT\n")

def log_weth_price_periodically(uniswap_instance, interval=1):
    """
    Log the WETH price at regular intervals.
    """
    try:
        while True:
            weth_price = get_weth_price(uniswap_instance)
            log_price_to_file(weth_price)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Logging stopped.")



def get_proposed_gas_price_from_etherscan(api_key):
    url = "https://api.etherscan.io/api"
    params = {
        "module": "gastracker",
        "action": "gasoracle",
        "apikey": api_key
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        return int(data["result"]["ProposeGasPrice"])
    except Exception as e:
        print(f"Error fetching proposed gas price: {e}")
        return None

def trade_bot():
    uniswap = Uniswap(address=address, private_key=PRIVATE_KEY, version=3, provider=INFURA_API_KEY)
    
    # Log the current WETH price
    weth_price = get_weth_price(uniswap)
    log_price_to_file(weth_price)

    # Fetch the proposed gas price from Etherscan API
    proposed_gas_price = get_proposed_gas_price_from_etherscan(ETHERSCAN_API_KEY)
    if proposed_gas_price is None:
        print("Failed to get the proposed gas price. Exiting.")
        return
    
    # Which token do you want to buy?
    token_choice = input("Are you buying WETH or USDT? ").strip().lower()
    assert token_choice in ['weth', 'usdt'], "Invalid token choice"
    
    # Determine the token used for payment and the token to receive
    spending_token = USDT_ADDRESS if token_choice == "weth" else WETH_ADDRESS
    receiving_token = WETH_ADDRESS if token_choice == "weth" else USDT_ADDRESS

    # Spending or receiving?
    direction = input(f"Do you want to specify the amount you're spending in {spending_token} or the amount you're receiving in {receiving_token}? (Type 'spending' or 'receiving'): ").strip().lower()
    assert direction in ['spending', 'receiving'], "Invalid choice"
    
    # Based on the direction, decide the trade type
    trade_type = 'exact_tokens_in' if direction == 'spending' else 'exact_tokens_out'

    # Determine the amount for the transaction based on the trade type
    if trade_type == 'exact_tokens_in':
        amount_spent = float(input(f"How much {spending_token} do you want to spend? "))
        amount = int(amount_spent * (10 ** (6 if spending_token == USDT_ADDRESS else 18)))
        tx_hash = uniswap.make_trade(spending_token, receiving_token, amount)
    else:  # exact_tokens_out
        amount_received = float(input(f"How much {receiving_token} do you want to receive? "))
        amount = int(amount_received * (10 ** (6 if receiving_token == USDT_ADDRESS else 18)))
        tx_hash = uniswap.make_trade_output(spending_token, receiving_token, amount)

    if tx_hash:
        print(f"Transaction hash: {tx_hash}")
    else:
        print("Transaction failed.")
