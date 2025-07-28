import json
import threading

VALIDATOR_FILE = "validators.json"
file_lock = threading.Lock()

def load_validators():
    """Load validators from JSON file safely."""
    try:
        with file_lock:
            with open(VALIDATOR_FILE, "r") as f:
                return json.load(f)
    except FileNotFoundError:
        return []

def save_validators(validators):
    """Save validators to JSON file safely."""
    with file_lock:
        with open(VALIDATOR_FILE, "w") as f:
            json.dump(validators, f, indent=4)

def is_validator(address):
    """Check if given address is registered as a validator."""
    return any(v["address"] == address for v in load_validators())

def add_validator_if_valid_stake(address, stake, api_url, min_stake=1000):
    """
    Add validator automatically if stake >= min_stake.
    If validator exists, update stake and api_url if necessary.
    """
    if stake < min_stake:
        return False  # Stake too low, do not add

    validators = load_validators()
    for v in validators:
        if v["address"] == address:
            # Validator exists, update info if stake higher
            v["stake"] = max(v["stake"], stake)
            v["api_url"] = api_url
            save_validators(validators)
            return True

    # Add new validator entry
    validators.append({
        "address": address,
        "stake": stake,
        "api_url": api_url,
        "active": True
    })
    save_validators(validators)
    return True

def remove_validator(address):
    """Remove validator by address."""
    validators = load_validators()
    updated = [v for v in validators if v["address"] != address]
    if len(updated) == len(validators):
        return False  # Nothing removed
    save_validators(updated)
    return True

def get_current_validator_id():
    """Return the address of validator with highest stake, or None if no validators."""
    validators = load_validators()
    if not validators:
        return None
    validators.sort(key=lambda v: v["stake"], reverse=True)
    return validators[0]["address"]

def is_validator_active(address):
    """Check if a validator is active."""
    validators = load_validators()
    for v in validators:
        if v["address"] == address:
            return v.get("active", True)
    return False

# Alias to maintain compatibility with app.py imports
add_validator = add_validator_if_valid_stake
