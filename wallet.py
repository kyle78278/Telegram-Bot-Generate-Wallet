import secrets
from web3 import Web3, HTTPProvider
from eth_keys import keys
import os
import json
import requests

with open("ERC20_abi/USDC_abi.json", "r") as f:
    usdc_abi = json.load(f)

INFURA_API_KEY = os.environ.get('INFURA_API_KEY')
INFURA_URL = f"https://mainnet.infura.io/v3/{INFURA_API_KEY}"
w3 = Web3(Web3.HTTPProvider(INFURA_URL))

USDC = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'

def generate_private_key():
    private_key = secrets.token_bytes(32)
    return private_key

def generate_wallet(private_key: bytes):
    public_key = keys.PrivateKey(private_key).public_key
    wallet_address = public_key.to_address()
    return wallet_address


def display_eth_balance(user_id: int) -> str:
    file_path = os.path.abspath(f"private_keys/{user_id}_private_key.txt")
    print(f"Looking for private key at {file_path}")
    if os.path.exists(file_path):
        print("File exists.")
        try:
            with open(file_path, "r") as f:
                private_key = f.read().strip()
            account = w3.eth.account.from_key(private_key)
            address = account.address
            balance_wei = w3.eth.get_balance(address)
            balance_eth = Web3.from_wei(balance_wei, 'ether')
            return str(balance_eth)
        except Exception as e:
            return f"An error occurred: {e}"
    else:
        print("File does not exist.")
        return "Private key not found."

def display_usdc_balance(user_id: int) -> str:
    file_path = os.path.abspath(f"private_keys/{user_id}_private_key.txt")
    print(f"Looking for private key at {file_path}")
    if os.path.exists(file_path):
        print("File exists.")
        try:
            with open(file_path, "r") as f:
                private_key = f.read().strip()
            account = w3.eth.account.from_key(private_key)
            address = account.address
            usdc_contract = w3.eth.contract(address=USDC, abi=usdc_abi)
            balance = usdc_contract.functions.balanceOf(address).call()
            balance_usdc = balance / (10 ** 6)
            return str(balance_usdc)
        except Exception as e:
            return f"An error occurred: {e}"
    else:
        print("File does not exist.")
        return "Private key not found."

def fetch_gas_price_from_etherscan():
    ETHERSCAN_API_KEY = 'ZG87677RNVQ3QKZ5N3MD4VX42F37P7IF92'
    url = f"https://api.etherscan.io/api?module=gastracker&action=gasoracle&apikey={ETHERSCAN_API_KEY}"
    response = requests.get(url)
    data = response.json()
    if data['status'] == '1':
        return int(data['result']['FastGasPrice'])
    else:
        return None

async def withdraw_all_eth(user_id: int, to_address: str) -> str:
    try:
        gas_price_gwei = fetch_gas_price_from_etherscan()
        if gas_price_gwei is None:
            return "Failed to fetch gas price from Etherscan."
        gas_price_wei = w3.to_wei(gas_price_gwei, 'gwei')
        with open(f"private_keys/{user_id}_private_key.txt", "r") as f:
            private_key = f.read().strip()
        account = w3.eth.account.from_key(private_key)
        from_address = account.address
        balance = w3.eth.get_balance(from_address)
        gas_estimate = 210000 
        value_to_send = balance - (gas_estimate * gas_price_wei)
        transaction = {
            'to': to_address,
            'value': value_to_send,
            'gas': gas_estimate,
            'gasPrice': gas_price_wei,
            'nonce': w3.eth.get_transaction_count(from_address)
        }
        signed_transaction = w3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_transaction.rawTransaction)
        return f"Transaction sent with hash: {tx_hash.hex()}"
    except Exception as e:
        return f"An error occurred: {e}"

async def withdraw_all_usdc(user_id: int, to_address: str, usdc_contract_address: str) -> str:
    try:
        gas_price_gwei = fetch_gas_price_from_etherscan()
        if gas_price_gwei is None:
            return "Failed to fetch gas price from Etherscan."
        gas_price_wei = w3.to_wei(gas_price_gwei, 'gwei')
        with open(f"private_keys/{user_id}_private_key.txt", "r") as f:
            private_key = f.read().strip()
        account = w3.eth.account.from_key(private_key)
        from_address = account.address
        usdc_contract = w3.eth.contract(address=usdc_contract_address, abi=usdc_abi)
        balance = usdc_contract.functions.balanceOf(from_address).call()
        transaction = {
            'to': usdc_contract_address,
            'value': 0,
            'gas': 210000,
            'gasPrice': gas_price_wei,
            'nonce': w3.eth.get_transaction_count(from_address),
            'chainId': 1,
            'data': usdc_contract.encodeABI(fn_name='transfer', args=[to_address, balance])
        }
        signed_transaction = w3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_transaction.rawTransaction)       
        return f"Transaction sent with hash: {tx_hash.hex()}"

    except Exception as e:
        error_message = f"An error occurred: {e}. USDC balance was: {balance}"
        with open("error_logs.txt", "a") as error_log:
            error_log.write(f"{error_message}\n")
        return error_message
