import requests
from validator import load_validators, save_validators

def remove_unresponsive_validators(timeout=3):
    """
    Ping all validators' api_url/ping endpoint.
    Remove validators that don't respond within the timeout.
    """
    validators = load_validators()
    active_validators = []

    for v in validators:
        try:
            response = requests.get(f"{v['api_url']}/ping", timeout=timeout)
            if response.status_code == 200:
                active_validators.append(v)
            else:
                print(f"[WARN] Validator {v['address']} ping failed with status {response.status_code}")
        except Exception as e:
            print(f"[WARN] Removing validator {v['address']} — offline or unreachable: {str(e)}")

    save_validators(active_validators)
