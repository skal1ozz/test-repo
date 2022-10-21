""" Token Helper """
import asyncio
from calendar import timegm
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, Union

from Crypto.Hash import SHA256

from entities.json.admin_user import AdminUser
from utils.azure_key_vault_client import AzureKeyVaultClient
from utils.functions import b64encode_str, b64encode_np
from utils.json_func import json_dumps


class MimeTypes:
    """ Token Types selection """
    JWT = "jwt"


class TokenHelper:
    """ Token Helper implementation """

    def __init__(self, azure_cli: AzureKeyVaultClient):
        self.azure_cli = azure_cli
        self.executor = ThreadPoolExecutor(10)
        self.io_loop = asyncio.get_event_loop()

    def sign_token_bl(self, header: Dict[str, Union[str, int]],
                      body: Dict[str, Union[str, int]],
                      alg: str) -> str:
        """ Sign token and return "{token}.{signature}" """
        from config import Auth

        if alg == Auth.RS256:
            """ RSA signature with SHA-256 """
            key = self.azure_cli.get_or_create_random_key_bl()
            header.update(dict(kid=key.name))

            token_unsigned = "{}.{}".format(b64encode_str(json_dumps(header)),
                                            b64encode_str(json_dumps(body)))
            signature = SHA256.new(token_unsigned.encode("utf-8")).digest()
            signature_encrypted = self.azure_cli.encrypt_bl(key, signature)
            signature_b64 = b64encode_np(signature_encrypted).decode("utf-8")
            return "{}.{}".format(token_unsigned, signature_b64)
        elif alg == Auth.HS256:
            """ HMAC with SHA-256 (HS256) """
            pass
        raise NotImplementedError("'{}' ALGORITHM ISN'T SUPPORTED".format(alg))

    def create_token_bl(self, login: str, ttl_seconds=3600) -> str:
        """ Create JWT token for the User, blocking """
        from config import Auth

        date = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        exp = timegm(date.utctimetuple())
        alg = Auth.CURRENT
        jwt_head = dict(typ=MimeTypes.JWT, alg=alg)
        jwt_body = dict(sub=login, exp=exp)
        token_signed = self.sign_token_bl(jwt_head, jwt_body, alg)
        return token_signed

    def do_auth_bl(self, user: AdminUser):
        """ Perform Auth blocking """
        from config import Auth

        kv_login = self.azure_cli.get_secret_bl(Auth.ADMIN_LOGIN_SECRET).value
        kv_passw = self.azure_cli.get_secret_bl(Auth.ADMIN_PASSW_SECRET).value
        if user.login == kv_login and user.password == kv_passw:
            ttl = 3600
            token = self.create_token_bl(user.login, ttl)
            return dict(tokenType="Bearer",
                        expiresIn=ttl,
                        accessToken=token)
        raise None

    def do_auth(self, user: AdminUser):
        """ Perform auth async """
        return self.io_loop.run_in_executor(self.executor, self.do_auth_bl,
                                            user)
