from ecdsa import SigningKey, SECP256k1, VerifyingKey, BadSignatureError
import hashlib


class Wallet:
    def __init__(self, private_key=None):
        if private_key:
            self.sk = SigningKey.from_string(bytes.fromhex(private_key), curve=SECP256k1)
        else:
            self.sk = SigningKey.generate(curve=SECP256k1)
        self.vk = self.sk.verifying_key

    def sign(self, message: str) -> str:
        return self.sk.sign(message.encode()).hex()

    def get_address(self) -> str:
        # Address = RIPEMD160(SHA256(pubkey))
        pubkey_bytes = self.vk.to_string()
        sha = hashlib.sha256(pubkey_bytes).digest()
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(sha)
        return ripemd160.hexdigest()

    def get_private_key(self) -> str:
        return self.sk.to_string().hex()

    def get_public_key(self) -> str:
        return self.vk.to_string().hex()


class WalletUtils:
    @staticmethod
    def create_wallet():
        wallet = Wallet()
        return wallet.get_private_key(), wallet.get_public_key()

    @staticmethod
    def get_address_from_pubkey(pubkey_hex):
        pubkey_bytes = bytes.fromhex(pubkey_hex)
        sha = hashlib.sha256(pubkey_bytes).digest()
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(sha)
        return ripemd160.hexdigest()


def verify_signature(pubkey_hex: str, message: str, signature_hex: str) -> bool:
    vk = VerifyingKey.from_string(bytes.fromhex(pubkey_hex), curve=SECP256k1)
    try:
        return vk.verify(bytes.fromhex(signature_hex), message.encode())
    except BadSignatureError:
        return False
