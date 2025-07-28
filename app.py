from flask import Flask, request, jsonify
from blockchain import Blockchain
from wallet import Wallet, verify_signature
from reward_backend import RewardSystem
from validator import (
    add_validator,
    is_validator,
    get_current_validator_id
)
from monitor_validators import remove_unresponsive_validators
from consensus import Consensus
import token_factory  # Your token creation/minting logic
import threading
import time
from utils import generate_txid, current_time



app = Flask(__name__)

# Initialize core components
blockchain = Blockchain()
consensus = Consensus(blockchain)
rewards = RewardSystem()

# Commission and staking params
AINC_FEE_PERCENTAGE = 0.01
STAKE_FREE_THRESHOLD = 2000
REFERRAL_COMMISSION_RATE = 0.02

# Wallet/referral tracking
wallets = {}
referrals = {}
referral_rewards = {}



def background_consensus_runner():
    while True:
        consensus.check_and_finalize_block()
        time.sleep(60)  # Run every 60 seconds

# Start background thread for auto-finalizing blocks
threading.Thread(target=background_consensus_runner, daemon=True).start()



pending_transactions = []

@app.route('/submit_tx', methods=['POST'])
def submit_tx():
    data = request.get_json()

    # Validate required fields
    required = ['sender', 'receiver', 'amount', 'signature', 'public_key']
    if not all(k in data for k in required):
        return jsonify({"status": "error", "message": "Missing transaction fields"}), 400

    # Signature verification
    if not verify_signature(data["public_key"], f"{data['sender']}-{data['receiver']}-{data['amount']}", data["signature"]):
        return jsonify({"status": "error", "message": "Invalid signature"}), 400

    # Generate transaction
    tx = {
        "sender": data["sender"],
        "receiver": data["receiver"],
        "amount": data["amount"],
        "timestamp": current_time(),
    }
    tx["txid"] = generate_txid(tx)

    # Add to pending tx pool
    blockchain.add_pending_transaction(tx)


    return jsonify({"status": "success", "txid": tx["txid"]}), 200

@app.route('/join-validator', methods=['POST'])
def join_validator():
    data = request.json
    address = data.get("address")
    stake = data.get("stake")
    api_url = data.get("api_url")

    if not address or not stake or not api_url:
        return jsonify({"error": "Missing data"}), 400

    if int(stake) < 10000:
        return jsonify({"error": "Minimum 10,000 ZINC required"}), 403

    if add_validator(address, stake, api_url):
        return jsonify({"message": "Validator added successfully"})
    else:
        return jsonify({"message": "Validator already exists"}), 409

@app.route('/remove-validator', methods=['POST'])
def remove_validator():
    data = request.json
    address = data.get("address")

    if not address:
        return jsonify({"error": "Missing address"}), 400

    from validator import remove_validator  # implement this function

    if remove_validator(address):
        return jsonify({"message": "Validator removed successfully"})
    else:
        return jsonify({"error": "Validator not found"}), 404


@app.route('/validators', methods=['GET'])
def get_validators():
    from validator import load_validators
    return jsonify(load_validators()), 200




    

@app.route('/receive_block', methods=['POST'])
def receive_block():
    data = request.get_json()

    validator_address = data.get("validator")
    if not is_validator(validator_address):
        return jsonify({"error": "Block sender is not a registered validator."}), 403

    block = Block.from_dict(data)

    if blockchain.add_block(block):
        return jsonify({"message": "Block accepted."}), 201
    else:
        return jsonify({"error": "Invalid block."}), 400


@app.route('/add_block', methods=['POST'])
def add_block():
    data = request.get_json()
    validator_address = data.get("validator")

    if not is_validator(validator_address):
        return jsonify({"error": "Not authorized validator."}), 403

    new_block = Block.create_block_from_data(data)
    
    if blockchain.add_block(new_block):
        # ✅ Broadcast to all known nodes
        for node in blockchain.nodes:
            try:
                url = f"{node}/receive_block"
                requests.post(url, json=new_block.to_dict())
            except Exception as e:
                print(f"[WARN] Could not send block to {node}: {str(e)}")

        return jsonify({"message": "Block created and broadcasted."}), 201
    else:
        return jsonify({"error": "Failed to add block."}), 400











@app.route('/')
def index():
    return "Welcome to Zinc Blockchain API with Referral, Commission, and Token Factory"

@app.route('/wallet/create', methods=['POST'])
def create_wallet():
    try:
        data = request.get_json(force=True) or {}
    except:
        return jsonify({'error': 'Invalid JSON format'}), 400

    referrer = data.get('referrer')

    private_key, public_key = Wallet.create_wallet()
    address = Wallet.get_address_from_pubkey(public_key)

    wallets[address] = {
        'private_key': private_key,
        'public_key': public_key,
        'referrer': None
    }

    if referrer and referrer != address and referrer in wallets:
        wallets[address]['referrer'] = referrer
        referrals[address] = referrer

    return jsonify({
        'address': address,
        'private_key': private_key,
        'public_key': public_key,
        'referrer': wallets[address]['referrer']
    }), 200


@app.route('/balance/<address>', methods=['GET'])
def get_balance(address):
    balance = blockchain.get_balance(address)
    ainc_balance = blockchain.get_balance_ainc(address)
    return jsonify({'zinc_balance': balance, 'ainc_balance': ainc_balance}), 200

@app.route('/stake', methods=['POST'])
def stake_and_register():
    data = request.get_json()

    address = data.get("address")
    stake = data.get("stake")
    api_url = data.get("api_url")

    if not address or not stake or not api_url:
        return jsonify({"error": "Missing address, stake, or api_url"}), 400

    if is_validator(address):
        return jsonify({"message": "Already a validator."}), 200

    success = add_validator(address, stake, api_url)
    if success:
        return jsonify({"message": "Validator registered successfully."}), 201
    else:
        return jsonify({"error": "Could not register validator."}), 500


@app.route('/claim_rewards', methods=['POST'])
def claim_rewards():
    data = request.get_json()
    address = data.get('address')
    if not address:
        return jsonify({'error': 'Missing address'}), 400

    reward = rewards.claim_reward(address)
    if reward > 0:
        blockchain.add_transaction("staking_pool", address, reward, "reward_signature")

    return jsonify({'reward': reward}), 200

@app.route('/stake_info/<address>', methods=['GET'])
def stake_info(address):
    info = rewards.get_stake_info(address)
    return jsonify(info), 200

@app.route('/transfer', methods=['POST'])
def transfer():
    data = request.get_json()
    required = ['sender', 'recipient', 'amount', 'signature']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing transaction fields'}), 400

    sender = data['sender']
    recipient = data['recipient']
    amount = float(data['amount'])
    signature = data['signature']

    sender_balance = blockchain.get_balance(sender)
    if sender_balance < amount:
        return jsonify({'error': 'Insufficient Zinc balance'}), 400

    stake_info = rewards.get_stake_info(sender)
    staked_amount = stake_info.get('amount', 0)
    free_transfer = staked_amount >= STAKE_FREE_THRESHOLD

    fee_in_ainc = 0
    if not free_transfer:
        fee_in_ainc = amount * AINC_FEE_PERCENTAGE
        ainc_balance = blockchain.get_balance_ainc(sender)
        if ainc_balance < fee_in_ainc:
            return jsonify({'error': f'Insufficient AINC balance to pay fee of {fee_in_ainc}'}), 400

    message = f"{sender}{recipient}{amount}"
    sender_pubkey = wallets.get(sender, {}).get("public_key")
    if not sender_pubkey or not verify_signature(sender_pubkey, message, signature):
        return jsonify({'error': 'Invalid signature'}), 400

    blockchain.add_transaction(sender, recipient, amount, signature)

    if fee_in_ainc > 0:
        blockchain.add_transaction(sender, "ainc_fee_pool", fee_in_ainc, "fee_signature")

    referrer = wallets.get(sender, {}).get('referrer')
    if referrer:
        commission = amount * REFERRAL_COMMISSION_RATE
        blockchain.add_transaction(sender, referrer, commission, "commission_signature")
        referral_rewards[referrer] = referral_rewards.get(referrer, 0) + commission

    return jsonify({
        'message': 'Transfer successful',
        'fee_charged_in_ainc': fee_in_ainc,
        'commission_to_referrer': amount * REFERRAL_COMMISSION_RATE if referrer else 0
    }), 200

# ---------------- Token Factory Routes ----------------

@app.route('/token/create', methods=['POST'])
def create_token():
    data = request.get_json()
    creator = data.get('creator')
    name = data.get('name')
    symbol = data.get('symbol')
    decimals = data.get('decimals', 18)
    supply = data.get('initial_supply', 0)

    if not all([creator, name, symbol]):
        return jsonify({'error': 'Missing required fields'}), 400

    token = token_factory.create_token(creator, name, symbol, decimals, supply)
    return jsonify({'message': 'Token created successfully', 'token': token}), 200

@app.route('/token/mint', methods=['POST'])
def mint_token():
    data = request.get_json()
    creator = data.get('creator')
    symbol = data.get('symbol')
    amount = data.get('amount')

    if not all([creator, symbol, amount]):
        return jsonify({'error': 'Missing mint parameters'}), 400

    success, result = token_factory.mint_token(creator, symbol, amount)
    if not success:
        return jsonify({'error': result}), 400

    return jsonify({'message': 'Mint successful', 'new_total_supply': result}), 200

@app.route('/token/info/<symbol>', methods=['GET'])
def token_info(symbol):
    token = token_factory.get_token(symbol)
    if not token:
        return jsonify({'error': 'Token not found'}), 404
    return jsonify(token), 200

# ------------------------------------------------------
def run_validator_monitor(interval=600):  # check every 10 minutes
    while True:
        print("Checking validators...")
        remove_unresponsive_validators()
        time.sleep(interval)

@app.route('/vote', methods=['POST'])
def vote_on_block():
    data = request.json
    validator = data.get("validator")
    approve = data.get("approve")

    result = consensus.vote_on_block(validator, approve)
    return jsonify(result)

@app.route('/propose', methods=['POST'])
def propose_block():
    validator = request.json.get("validator")
    result = consensus.propose_new_block(validator)
    return jsonify(result)




if __name__ == '__main__':
    threading.Thread(target=run_validator_monitor, daemon=True).start()
    app.run(debug=True, port=5000)

