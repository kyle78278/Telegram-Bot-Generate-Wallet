import secrets
from web3 import Web3
from eth_keys import keys
import os
import json

with open("ERC20_abi/USDT_abi.json", "r") as f:
    usdt_abi = json.load(f)


INFURA_API_KEY = os.environ.get('INFURA_API_KEY')
INFURA_URL = f"https://mainnet.infura.io/v3/{INFURA_API_KEY}"
w3 = Web3(Web3.HTTPProvider(INFURA_URL))

USDT = '0xdAC17F958D2ee523a2206206994597C13D831ec7'

def generate_private_key():
    # Generate a secure random 32-byte private key
    private_key = secrets.token_bytes(32)
    return private_key

def generate_wallet(private_key: bytes):
    # Generate the public key
    public_key = keys.PrivateKey(private_key).public_key
    
    # Generate the wallet address
    wallet_address = public_key.to_address()
    return wallet_address


def display_eth_balance(user_id: int) -> str:
    file_path = os.path.abspath(f"private_keys/{user_id}_private_key.txt")
    print(f"Looking for private key at {file_path}")  # Debugging line

    if os.path.exists(file_path):
        print("File exists.")  # Debugging line
        try:
            # Read the private key from the file
            with open(file_path, "r") as f:
                private_key = f.read().strip()

            # Calculate the public address from the private key
            account = w3.eth.account.from_key(private_key)
            address = account.address
            
            # Fetch the balance
            balance_wei = w3.eth.get_balance(address)
            balance_eth = Web3.from_wei(balance_wei, 'ether')  # Use Web3.fromWei here
            
            return str(balance_eth)
        except Exception as e:
            return f"An error occurred: {e}"
    else:
        print("File does not exist.")  # Debugging line
        return "Private key not found."

def display_usdt_balance(user_id: int) -> str:  # Removed usdt_contract_address argument
    file_path = os.path.abspath(f"private_keys/{user_id}_private_key.txt")
    print(f"Looking for private key at {file_path}")  # Debugging line

    if os.path.exists(file_path):
        print("File exists.")  # Debugging line
        try:
            # Read the private key from the file
            with open(file_path, "r") as f:
                private_key = f.read().strip()

            # Calculate the public address from the private key
            account = w3.eth.account.from_key(private_key)
            address = account.address

            # Interact with the USDT contract
            usdt_contract = w3.eth.contract(address=USDT, abi=usdt_abi)  # Using global USDT variable
            balance = usdt_contract.functions.balanceOf(address).call()
            balance_usdt = balance / (10 ** 6)  # Assuming USDT has 6 decimals

            return str(balance_usdt)
        except Exception as e:
            return f"An error occurred: {e}"
    else:
        print("File does not exist.")  # Debugging line
        return "Private key not found."

