""" Config """
import os

from azure.cosmos import PartitionKey

from utils.azure_key_vault_client import AzureKeyVaultClient
from utils.cosmos_client import CosmosClient
from utils.token_helper import TokenHelper

PROJECT_ROOT_PATH = os.path.dirname(os.path.abspath("__file__"))
ASSETS_PATH = os.path.join(PROJECT_ROOT_PATH, "assets")
CARDS_PATH = os.path.join(ASSETS_PATH, "cards")
STRINGS_PATH = os.path.join(ASSETS_PATH, "strings")


APP_VERSION = "1.1.188"


class Auth:
    """ Auth type """
    class Types:
        """ Auth types """
        BEARER = "Bearer"
        BASIC = "Basic"

    class Algorithms:
        """ Auth Algorithms """
        RS256 = "RS256"
        HS256 = "HS256"

    TYPE = Types.BEARER
    ALGORITHM = Algorithms.RS256
    TOKEN_TYPE = "JWT"

    ADMIN_LOGIN_SECRET = "adminLogin"
    ADMIN_PASSW_SECRET = "adminPassword"


class TeamsAppConfig:
    """ Teams app config """
    teams_app_items = os.path.join(ASSETS_PATH, "teams_app_items")
    manifest = os.path.join(teams_app_items, "manifest.json")
    image_192x192 = os.path.join(teams_app_items, "color.png")
    image_32x32 = os.path.join(teams_app_items, "outline.png")
    zip_name = "app.zip"
    zip_file = os.path.join(teams_app_items, zip_name)


class TaskModuleConfig:
    """ Task Module config """
    TITLE = os.environ.get("TASK_MODULE_TITLE",
                           "Example portal")
    URL = os.environ.get("TASK_MODULE_URL",
                         "https://fake.s1z.info/show-channel.html")
    WIDTH = "large"
    HEIGHT = "large"
    VALID_DOMAINS = os.environ.get("VALID_DOMAINS", '[{"validDomain": ""}]')


class AppConfig:
    """ Bot Configuration """

    CLIENT_ID = os.environ.get("CLIENT_ID",
                               "00000000-0000-0000-0000-000000000000")
    KEY_VAULT = os.environ.get("KEY_VAULT", "key-vault")
    PORT = os.environ.get("HOST_PORT", 8000)
    TENANT_ID = os.environ.get("TENANT_ID",
                               "00000000-0000-0000-0000-000000000000")

    BOT_NAME = os.environ.get("BOT_NAME", 'TheBot')
    WEB_APP_NAME = os.environ.get("WEB_APP_NAME", "wa-name")
    APP_ID = os.environ.get("MS_APP_ID", "app-id")
    APP_PASSWORD = os.environ.get("MS_APP_PASSWORD", "app-password")
    PA_URL = os.environ.get(
        "PA_URL", (
            "https://prod-204.westeurope.logic.azure.com:443/workflows/"
            "7780619c3381411991bf5c161719d0bf/triggers/manual/paths/"
            "invoke?api-version=2016-06-01&sp=%2Ftriggers%2Fmanual%2Frun&"
            "sv=1.0&sig=yQiQs3aA_nT_NilCzFzQgYj14UgOAXluUyDfphatx-4"
        )
    )


class CosmosDBConfig:
    """ Cosmos Databases """
    HOST = os.environ.get("ACCOUNT_HOST", "host")
    KEY = os.environ.get("COSMOS_KEY", "key")

    class Conversations:
        """ Conversation DB """
        DATABASE = "bot"
        CONTAINER = "conversations"
        PK = "id"
        PARTITION_KEY = PartitionKey(path="/conversation/tenantId")

    class Notifications:
        """ Notifications DB """
        DATABASE = "bot"
        CONTAINER = "notifications"
        PK = "id"
        PARTITION_KEY = PartitionKey(path="/tenantId")

    class Acknowledges:
        """ Acknowledges"""
        DATABASE = "bot"
        CONTAINER = "acknowledges"
        PK = "id"
        PARTITION_KEY = PartitionKey(path="/notificationId")

    class Initiations:
        """ Initiations """
        DATABASE = "bot"
        CONTAINER = "initiations"
        PK = "id"
        PARTITION_KEY = PartitionKey(path="/notificationId")

    class Flows:
        """ Flows """
        DATABASE = "bot"
        CONTAINER = "flows"
        PK = "id"
        PARTITION_KEY = PartitionKey(path="/tenantId")


COSMOS_CLIENT = CosmosClient(CosmosDBConfig.HOST, CosmosDBConfig.KEY)
KEY_VAULT_CLIENT = AzureKeyVaultClient(AppConfig.CLIENT_ID,
                                       AppConfig.KEY_VAULT)
TOKEN_HELPER = TokenHelper(KEY_VAULT_CLIENT)
