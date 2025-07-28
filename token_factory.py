# token_factory.py

import hashlib
import time

class Token:
    def __init__(self, symbol, name, creator_address, total_supply, decimals=8):
        self.symbol = symbol.upper()
        self.name = name
        self.creator = creator_address
        self.total_supply = total_supply
        self.decimals = decimals
        self.created_at = time.time()
        self.balances = {creator_address: total_supply}
        self.token_id = self.generate_token_id()

    def generate_token_id(self):
        raw = f"{self.symbol}:{self.creator}:{self.created_at}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def mint(self, to_address, amount):
        if self.creator != to_address:
            raise Exception("Only the creator can mint tokens.")
        if to_address not in self.balances:
            self.balances[to_address] = 0
        self.balances[to_address] += amount
        self.total_supply += amount

    def transfer(self, from_addr, to_addr, amount):
        if self.balances.get(from_addr, 0) < amount:
            raise Exception("Insufficient token balance")
        self.balances[from_addr] -= amount
        self.balances[to_addr] = self.balances.get(to_addr, 0) + amount

    def balance_of(self, address):
        return self.balances.get(address, 0)
