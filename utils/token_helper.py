""" Token Helper """
import asyncio
from calendar import timegm
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Dict, Union

from Crypto.Hash import SHA256
from aiohttp.web import Request, Response
from azure.core.exceptions import ResourceNotFoundError, HttpResponseError

from entities.json.admin_user import AdminUser
from utils.azure_key_vault_client import AzureKeyVaultClient
from utils.functions import b64encode_str, b64encode_np, parse_auth_header, \
    b64decode_str
from utils.json_func import json_dumps, json_loads
from utils.log import Log


class MimeTypes:
    """ Token Types selection """
    JWT = "jwt"


class TokenHelper:
    """ Token Helper implementation """

    def __init__(self, azure_kv: AzureKeyVaultClient):
        self.azure_kv = azure_kv
        self.executor = ThreadPoolExecutor(10)
        self.io_loop = asyncio.get_event_loop()

    def sign_token_bl(self, header: Dict[str, Union[str, int]],
                      body: Dict[str, Union[str, int]],
                      alg: str) -> str:
        """ Sign token and return "{token}.{signature}" """
        from config import Auth

        if alg == Auth.Algorithms.RS256:
            """ RSA signature with SHA-256 """
            key = self.azure_kv.get_or_create_random_key_bl()
            header.update(dict(kid=key.name))

            token_unsigned = "{}.{}".format(b64encode_str(json_dumps(header)),
                                            b64encode_str(json_dumps(body)))
            signature = SHA256.new(token_unsigned.encode("utf-8")).digest()
            signature_encrypted = self.azure_kv.encrypt_bl(key, signature)
            signature_b64 = b64encode_np(signature_encrypted).decode("utf-8")
            return "{}.{}".format(token_unsigned, signature_b64)
        elif alg == Auth.Algorithms.HS256:
            """ HMAC with SHA-256 (HS256) """
            pass
        raise NotImplementedError("'{}' ALGORITHM ISN'T SUPPORTED".format(alg))

    def create_token_bl(self, login: str, ttl_seconds=3600) -> str:
        """ Create JWT token for the User, blocking """
        from config import Auth

        date = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        exp = timegm(date.utctimetuple())
        alg = Auth.ALGORITHM
        jwt_head = dict(typ=MimeTypes.JWT, alg=alg)
        jwt_body = dict(sub=login, exp=exp)
        token_signed = self.sign_token_bl(jwt_head, jwt_body, alg)
        return token_signed

    def do_auth_bl(self, user: AdminUser):
        """ Perform Auth blocking """
        from config import Auth

        login = self.azure_kv.get_secret_bl(Auth.ADMIN_LOGIN_SECRET).value
        passw = self.azure_kv.get_secret_bl(Auth.ADMIN_PASSW_SECRET).value
        if user.login == login and user.password == passw:
            ttl = 3600
            token = self.create_token_bl(user.login, ttl)
            return dict(tokenType=Auth.TYPE,
                        expiresIn=ttl,
                        accessToken=token)
        return None

    def do_auth(self, user: AdminUser):
        """ Perform auth async """
        return self.io_loop.run_in_executor(self.executor, self.do_auth_bl,
                                            user)

    def is_token_valid(self, token: str) -> bool:
        """ Check if token is Valid """
        from config import Auth

        # split first
        header_b64_str, body_b64_str, signature = token.split(".")
        token_unsigned = "{}.{}".format(header_b64_str, body_b64_str)

        # parse
        header = json_loads(b64decode_str(header_b64_str))
        body = json_loads(b64decode_str(body_b64_str))

        # check fields
        token_typ = header.get("typ", None)
        token_alg = header.get("alg", None)
        token_kid = header.get("kid", None)
        token_sub = body.get("sub", None)
        token_exp = body.get("exp", None)
        if None in [token_typ, token_alg, token_kid, token_sub, token_exp]:
            return False

        # check type
        if token_typ != Auth.TOKEN_TYPE:
            return False

        # check alg
        if token_alg != Auth.ALGORITHM:
            return False

        # check expiration
        if datetime.utcnow().timestamp() > token_exp:
            return False

        # TODO(s1z): Cache this please
        # check sub
        login = self.azure_kv.get_secret_bl(Auth.ADMIN_LOGIN_SECRET).value
        if token_sub != login:
            return False

        # check signature
        try:
            key = self.azure_kv.get_key_bl(token_kid)
        except (ResourceNotFoundError, HttpResponseError):
            Log.e(__name__, "Key not found: '{}'".format(token_kid))
            return False

        signature_gen = SHA256.new(token_unsigned.encode("utf-8")).digest()
        signature_encrypted = self.azure_kv.encrypt_bl(key, signature_gen)
        signature_gen = b64encode_np(signature_encrypted).decode("utf-8")
        if signature != signature_gen:
            return False
        return True

    def is_auth(self, f):
        """ Is auth decorator """
        from config import Auth

        async def wr(request: Request) -> Response:
            """ Wrapper """
            a_type, a_value = parse_auth_header(
                request.headers.get("Authorization")
            )
            if a_type == Auth.TYPE and self.is_token_valid(a_value):
                return await f(request)
            return Response(status=HTTPStatus.FORBIDDEN)
        return wr
