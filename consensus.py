# consensus.py

import time
import threading
import hashlib

from validator import is_validator, load_validators
from blockchain import Blockchain, add_block, get_pending_transactions, clear_pending_transactions
from validator import get_current_validator_id, is_validator_active

from vote import reset_votes_for_new_block


class Consensus:
    def __init__(self, blockchain: Blockchain):
        self.blockchain = blockchain
        self.pending_block = None
        self.pending_block_votes = {}
        self.CONSENSUS_THRESHOLD = 0.66  # 66% required for approval

    def calculate_hash(self, index, previous_hash, timestamp, transactions, proposer):
        block_string = f"{index}{previous_hash}{timestamp}{transactions}{proposer}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def reset(self):
        self.pending_block = None
        self.pending_block_votes = {}

    def propose_block(self):
        if self.pending_block is not None:
            return {"message": "Block already proposed"}

        validator_id = get_current_validator_id()
        if not validator_id or not is_validator_active(validator_id):
            return {"error": "Not a valid or active validator"}, 403

        txs = get_pending_transactions()
        if not txs:
            return {"message": "No transactions to include in block"}

        last_block = self.blockchain.chain[-1]
        new_index = last_block.index + 1
        timestamp = time.time()
        previous_hash = last_block.hash
        new_hash = self.calculate_hash(new_index, previous_hash, timestamp, txs, validator_id)

        new_block = {
            'index': new_index,
            'previous_hash': previous_hash,
            'timestamp': timestamp,
            'transactions': txs,
            'validator': validator_id,
            'hash': new_hash
        }

        self.pending_block = new_block
        self.pending_block_votes = {}
        reset_votes_for_new_block()  # Reset global state too
        print(f"[Propose] Block #{new_index} proposed by validator {validator_id}")

        return {"message": "Block proposed", "block": new_block}

    def vote_on_block(self, validator_address: str, approve: bool):
        if not is_validator(validator_address):
            return {"error": "Not a registered validator"}, 403

        if self.pending_block is None:
            return {"error": "No block proposed yet"}, 400

        self.pending_block_votes[validator_address] = approve
        print(f"[Vote] Validator {validator_address} voted {'✅ Yes' if approve else '❌ No'}")
        return {"message": "Vote recorded"}

    def check_and_finalize_block(self):
        if self.pending_block is None:
            return {"message": "No pending block"}, 200

        validators = load_validators()
        total = len(validators)
        if total == 0:
            return {"error": "No validators registered"}, 500

        votes = self.pending_block_votes
        yes_votes = sum(1 for v in votes.values() if v is True)

        if yes_votes / total >= self.CONSENSUS_THRESHOLD:
            add_block(self.pending_block)
            clear_pending_transactions()
            print(f"[Consensus ✅] Block #{self.pending_block['index']} finalized with {yes_votes}/{total} votes")
            self.reset()
            return {"message": "Block finalized and added"}
        else:
            print(f"[Consensus ❌] Waiting for more votes ({yes_votes}/{total})")
            return {"message": "Waiting for more votes"}

    def auto_propose_and_vote_check(self):
        while True:
            time.sleep(60)  # ⏱️ Check every 60 seconds

            if self.pending_block is None:
                print("[Auto] No pending block. Trying to propose one...")
                self.propose_block()
            else:
                print("[Auto] Pending block exists. Checking votes...")
                self.check_and_finalize_block()


# ✅ Create global consensus object
blockchain = Blockchain()
consensus = Consensus(blockchain)

# ✅ Start the background thread
auto_thread = threading.Thread(target=consensus.auto_propose_and_vote_check)
auto_thread.daemon = True  # Automatically ends when main program stops
auto_thread.start()
