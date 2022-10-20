""" Config """
import os

from azure.cosmos import PartitionKey

from utils.azure_key_vault_client import AzureKeyVaultClient
from utils.cosmos_client import CosmosClient


PROJECT_ROOT_PATH = os.path.dirname(os.path.abspath("__file__"))
ASSETS_PATH = os.path.join(PROJECT_ROOT_PATH, "assets")
CARDS_PATH = os.path.join(ASSETS_PATH, "cards")


class TeamsAppConfig:
    """ Teams app config """
    teams_app_items = os.path.join(ASSETS_PATH, "teams_app_items")
    manifest = os.path.join(teams_app_items, "manifest,json")
    image_192x192 = os.path.join(teams_app_items, "color_192x192.png")
    image_32x32 = os.path.join(teams_app_items, "outline_32x32.png")
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


class AppConfig:
    """ Bot Configuration """

    CLIENT_ID = os.environ.get("CLIENT_ID",
                               "00000000-0000-0000-0000-000000000000")
    KEY_VAULT = os.environ.get("KEY_VAULT", "key-vault")
    PORT = os.environ.get("HOST_PORT", 8000)
    TENANT_ID = os.environ.get("TENANT_ID",
                               "00000000-0000-0000-0000-000000000000")

    WEB_APP_NAME = os.environ.get("WEB_APP_NAME", "wa-name")
    APP_ID = os.environ.get("MS_APP_ID", "app-id")
    APP_PASSWORD = os.environ.get("MS_APP_PASSWORD", "app-password")


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


COSMOS_CLIENT = CosmosClient(CosmosDBConfig.HOST, CosmosDBConfig.KEY)
KEY_VAULT_CLIENT = AzureKeyVaultClient(AppConfig.CLIENT_ID,
                                       AppConfig.KEY_VAULT)
