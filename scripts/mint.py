#!/usr/bin/env python3
"""
Artbot daily minting script on Base mainnet.
Uses standard ERC-1155 contract: 0xd987fBe8a978787272B994929A3514C21ae34Df1
"""
import os
import sys
import json
from web3 import Web3

RPC_URL = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0xd987fBe8a978787272B994929A3514C21ae34Df1")

if not PRIVATE_KEY:
    print("Error: WALLET_PRIVATE_KEY environment variable not set")
    sys.exit(1)

w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = w3.eth.account.from_key(PRIVATE_KEY)

artifact_path = os.path.join(os.path.dirname(__file__), "..", "contracts", "ArtbotERC1155.json")
with open(artifact_path, "r") as f:
    artifact = json.load(f)

contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=artifact["abi"])

def mint(token_id, metadata_uri, to_address=None):
    if to_address is None:
        to_address = account.address

    print(f"Minting Token ID {token_id} to {to_address}...")
    tx = contract.functions.mint(
        Web3.to_checksum_address(to_address),
        int(token_id),
        metadata_uri
    ).build_transaction({
        from: account.address,
        nonce: w3.eth.get_transaction_count(account.address),
        gasPrice: w3.eth.gas_price
    })

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"TX submitted: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Confirmed in block {receipt.blockNumber}! Status: {receipt.status}")
    return tx_hash.hex()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 mint.py <TOKEN_ID> <METADATA_URI> [TO_ADDRESS]")
        sys.exit(1)
    mint(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
