""" AzureVaultClient implementation """
import asyncio
import random
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Awaitable

# noinspection PyPackageRequirements
from azure.keyvault.keys import KeyClient, KeyVaultKey
# noinspection PyPackageRequirements
from azure.keyvault.keys.crypto import CryptographyClient, EncryptionAlgorithm
# noinspection PyPackageRequirements
from azure.keyvault.secrets import SecretClient, KeyVaultSecret
# noinspection PyPackageRequirements
from azure.identity import ClientSecretCredential, DefaultAzureCredential, \
    ManagedIdentityCredential


class AzureKeyVaultClient:
    """ Azure Key Vault Client """
    def __init__(self, client_id: str, key_vault: str):
        self.executor = ThreadPoolExecutor(10)
        self.io_loop = asyncio.get_event_loop()
        self.key_vault = key_vault
        self.key_vault_uri = "https://{key_vault}.vault.azure.net".format(
            key_vault=key_vault
        )
        self.credential = ManagedIdentityCredential(client_id=client_id)
        # self.credential = DefaultAzureCredential()
        self.key_client = KeyClient(vault_url=self.key_vault_uri,
                                    credential=self.credential)
        self.secret_client = SecretClient(vault_url=self.key_vault_uri,
                                          credential=self.credential)

    def execute_blocking(self, bl, *args):
        """ Execute blocking code """
        return self.io_loop.run_in_executor(self.executor, bl, *args)

    def set_secret(self, name: str, value: str) -> Awaitable["KeyVaultSecret"]:
        """ Async set secret """
        return self.execute_blocking(self.secret_client.set_secret, name,
                                     value)

    def get_secret_bl(self, name: str) -> "KeyVaultSecret":
        """ Get secret blocking """
        return self.secret_client.get_secret(name)

    def set_secret_bl(self, name: str, value: str) -> "KeyVaultSecret":
        """ Get secret blocking """
        return self.secret_client.set_secret(name, value)

    def get_secret(self, name: str) -> Awaitable["KeyVaultSecret"]:
        """ Async get secret """
        return self.execute_blocking(self.secret_client.get_secret, name)

    def get_key_bl(self, name: str) -> "KeyVaultKey":
        """ Get key, blocking """
        return self.key_client.get_key(name)

    def get_key(self, name: str) -> Awaitable["KeyVaultKey"]:
        """ Get key, Async """
        return self.execute_blocking(self.key_client.get_key, name)

    def create_key(self, name: str) -> Awaitable["KeyVaultKey"]:
        """ Async create key """
        return self.execute_blocking(self.key_client.create_rsa_key, name)

    def get_or_create_random_key_bl(self, quantity=10) -> KeyVaultKey:
        """ Get or Create random key """
        random_key = None
        try:
            random_key = self.get_random_key_bl()
        except IndexError:
            # create keys here
            for _ in range(quantity):
                name = "%i" % (datetime.now().timestamp() * 1000000)
                expires_on = datetime.now() + timedelta(days=7)
                random_key = self.key_client.create_rsa_key(
                    name, expires_on=expires_on
                )
        return random_key

    def get_random_key_bl(self) -> KeyVaultKey:
        """ Blocking get random key """
        keys = self.key_client.list_properties_of_keys()
        all_keys = []
        for key in keys:
            all_keys.append(key)
        random_key = random.choice(all_keys)
        return self.key_client.get_key(random_key.name)

    def get_random_key(self) -> Awaitable["KeyVaultKey"]:
        """ Async get random key """
        return self.execute_blocking(self.get_random_key_bl)

    def get_cipher(self, key: KeyVaultKey) -> CryptographyClient:
        """ Get Cipher """
        return CryptographyClient(key, self.credential)

    def encrypt_bl(self, key: KeyVaultKey, data: bytes) -> bytes:
        """ Encrypt data """
        cipher = CryptographyClient(key, self.credential)
        result = cipher.encrypt(EncryptionAlgorithm.rsa_oaep, data)
        return result.ciphertext

    def decrypt_bl(self, key: KeyVaultKey, data: bytes) -> bytes:
        """ Decrypt data """
        cipher = CryptographyClient(key, self.credential)
        result = cipher.decrypt(EncryptionAlgorithm.rsa_oaep, data)
        return result.plaintext

    def encrypt(self, key: KeyVaultKey, data: bytes) -> Awaitable[bytes]:
        """ Encrypt data """
        return self.execute_blocking(self.encrypt_bl, key, data)

    def decrypt(self, key: KeyVaultKey, data: bytes) -> Awaitable[bytes]:
        """ Decrypt data """
        return self.execute_blocking(self.decrypt_bl, key, data)
