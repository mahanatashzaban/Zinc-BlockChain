import hashlib
import json
import time
import random
from ecdsa import VerifyingKey, SECP256k1

class Transaction:
    def __init__(self, sender, recipient, amount, signature="", **kwargs):
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.signature = signature

    def to_dict(self):
        return {
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'signature': self.signature
        }

    def compute_hash(self):
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()

class Block:
    def __init__(self, index, previous_hash, transactions, timestamp=None, validator=None, hash=None):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp or time.time()
        self.transactions = transactions  # List of Transaction objects
        self.validator = validator
        self.hash = hash or self.compute_hash()

    def compute_hash(self):
        block_data = json.dumps({
            'index': self.index,
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'validator': self.validator
        }, sort_keys=True).encode()
        return hashlib.sha256(block_data).hexdigest()

    def to_dict(self):
        return {
            'index': self.index,
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'validator': self.validator,
            'hash': self.hash
        }

    @staticmethod
    def from_dict(data):
        transactions = [Transaction(**tx) for tx in data['transactions']]
        return Block(
            index=data['index'],
            previous_hash=data['previous_hash'],
            transactions=transactions,
            timestamp=data['timestamp'],
            validator=data['validator'],
            hash=data.get('hash')
        )

    @staticmethod
    def create_block_from_data(data):
        transactions = [Transaction(**tx) for tx in data['transactions']]
        return Block(
            index=data['index'],
            previous_hash=data['previous_hash'],
            transactions=transactions,
            timestamp=data.get('timestamp'),
            validator=data.get('validator')
        )


class Blockchain:
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.balances = {}
        self.stakes = {}
        self.nodes = set()
        self.create_genesis_block()
        self.pending_transactions = []

    def add_pending_transaction(self, tx):
        self.pending_transactions.append(tx)

    def get_pending_transactions(self):
        return self.pending_transactions

    def clear_pending_transactions(self):
        self.pending_transactions = []

    def create_genesis_block(self):
        genesis_block = Block(0, "0", [], time.time(), validator="genesis")
        self.chain.append(genesis_block)

    def get_last_block(self):
        return self.chain[-1]

    def add_transaction(self, sender, recipient, amount, signature):
        if sender != "ZINC_REWARD" and self.balances.get(sender, 0) < amount:
            return False
        tx = Transaction(sender, recipient, amount, signature)
        self.current_transactions.append(tx)
        return True

    def verify_signature(self, sender, signature, message):
        try:
            vk = VerifyingKey.from_string(bytes.fromhex(sender), curve=SECP256k1)
            return vk.verify(bytes.fromhex(signature), message.encode())
        except:
            return False

    def select_validator(self):
        total_stake = sum(self.stakes.values())
        if total_stake == 0:
            return "genesis"
        r = random.uniform(0, total_stake)
        upto = 0
        for k, stake in self.stakes.items():
            upto += stake
            if upto >= r:
                return k
        return "genesis"

    def forge_block(self):
        validator = self.select_validator()
        block = Block(
            index=len(self.chain),
            previous_hash=self.get_last_block().hash,
            transactions=self.current_transactions,
            validator=validator
        )
        self.chain.append(block)
        for tx in self.current_transactions:
            self.balances[tx.sender] = self.balances.get(tx.sender, 0) - tx.amount
            self.balances[tx.recipient] = self.balances.get(tx.recipient, 0) + tx.amount
        reward_tx = Transaction("ZINC_REWARD", validator, 10)
        self.balances[validator] = self.balances.get(validator, 0) + 10
        self.current_transactions = [reward_tx]

    def stake(self, public_key, amount):
        if self.balances.get(public_key, 0) >= amount:
            self.balances[public_key] -= amount
            self.stakes[public_key] = self.stakes.get(public_key, 0) + amount
            return True
        return False

# Expose standalone functions for consensus.py or other files if needed

blockchain = Blockchain()

def add_block(block):
    blockchain.chain.append(block)

def get_pending_transactions():
    return blockchain.get_pending_transactions()

def clear_pending_transactions():
    blockchain.clear_pending_transactions()
