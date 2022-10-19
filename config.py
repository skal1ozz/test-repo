""" Config """
import os

from azure.cosmos import PartitionKey

from utils.azure_key_vault_client import AzureKeyVaultClient
from utils.cosmos_client import CosmosClient


PROJECT_ROOT_PATH = os.path.dirname(os.path.abspath("__file__"))
CARDS_PATH = os.path.join(PROJECT_ROOT_PATH, "assets/cards")


class TeamsAppConfig:
    """ Teams app config """
    teams_app_items = "teams_app_items"
    manifest = os.path.join(PROJECT_ROOT_PATH, teams_app_items,
                                 "manifest,json")
    image_192x192 = os.path.join(PROJECT_ROOT_PATH, teams_app_items,
                                 "color_192x192.png")
    image_32x32 = os.path.join(PROJECT_ROOT_PATH, teams_app_items,
                               "outline_32x32.png")
    zip_file = os.path.join(PROJECT_ROOT_PATH, teams_app_items, "app.zip")


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

    CLIENT_ID = os.environ.get("CLIENT_ID", None)
    KEY_VAULT = os.environ.get("KEY_VAULT", '')
    PORT = os.environ.get("HOST_PORT", 8000)
    TENANT_ID = os.environ.get("TENANT_ID",
                               "5df91ebc-64fa-4aa1-862c-bdc0cba3c656")

    WEB_APP_NAME = os.environ.get("WEB_APP_NAME", "")
    APP_ID = os.environ.get("MS_APP_ID", "")
    APP_PASSWORD = os.environ.get("MS_APP_PASSWORD", "")


class CosmosDBConfig:
    """ Cosmos Databases """
    HOST = os.environ.get('ACCOUNT_HOST', '')
    KEY = os.environ.get('COSMOS_KEY', '')

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
