""" Config """
import os

from azure.cosmos import PartitionKey

from utils.cosmos_client import CosmosClient


PROJECT_ROOT_PATH = os.path.dirname(os.path.abspath("__file__"))
CARDS_PATH = os.path.join(PROJECT_ROOT_PATH, "assets/cards")


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

    PORT = 3978
    APP_ID = os.environ.get("MS_APP_ID",
                            "d472f12a-323b-4058-b89b-7a4b15c48ab7")
    APP_PASSWORD = os.environ.get("MS_APP_PASSWORD",
                                  "ZdL|zw:]Io_}goFfWs2{w70g+.FXwQ")
    TENANT_ID = os.environ.get("TENANT_ID",
                               "5df91ebc-64fa-4aa1-862c-bdc0cba3c656")


class CosmosDBConfig:
    """ Cosmos Databases """
    HOST = os.environ.get('ACCOUNT_HOST',
                          'https://nancycosomsdb.documents.azure.com:443/')
    KEY = os.environ.get('ACCOUNT_KEY',
                         'fNVRCesO1NAb9MYZNK2rKdAPkY9J4O5ntR8CRuKu6wVGhndiaXch'
                         'Q6fKwrTTnTbv4tPM8S74YjZsfcX4uAHgiw==')

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
