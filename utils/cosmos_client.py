""" Cosmos Client implementation """
import asyncio
import sys
import uuid
from concurrent import futures
from typing import Any, Dict, Optional, Union, List, Tuple

import azure.cosmos.cosmos_client as cosmos_client
import azure.cosmos.exceptions as exceptions
from azure.cosmos import DatabaseProxy, ContainerProxy, documents
from azure.identity import ManagedIdentityCredential, DefaultAzureCredential
from botbuilder.core import TurnContext
from botbuilder.schema import ChannelAccount
from marshmallow import EXCLUDE

from entities.json.acknowledge import Acknowledge
from entities.json.acknowledge_schema import AcknowledgeSchema
from entities.json.camel_case_mixin import timestamp_factory
from entities.json.conversation_reference import ConversationReference
from entities.json.flow import Flow
from entities.json.initiation import Initiation
from entities.json.notification import NotificationCosmos
from utils.functions import get_first_or_none
from utils.log import Log


TAG = __name__


class CosmosClientException(Exception):
    """ Cosmos Client base exception """
    def __init__(self, message: str):
        self.message = message


class ItemExists(CosmosClientException):
    """ Item already exists in the DB """
    pass


class SaveItemError(CosmosClientException):
    """ Save Item Error """
    pass


class SaveConversationError(CosmosClientException):
    """ Save Conversation Error """
    pass


class ItemNotFound(CosmosClientException):
    """ Item not found """
    pass


class CosmosClient:
    """ Cosmos Client class """
    def __init__(self, host: str, master_key: str):
        self.executor = futures.ThreadPoolExecutor()
        # mgmt_credentials = ManagedIdentityCredential(client_id=client_id)
        # self.client = cosmos_client.CosmosClient(
        #     host, mgmt_credentials,
        #     consistency_level=documents.ConsistencyLevel.Strong
        # )
        self.client = cosmos_client.CosmosClient(host,
                                                 dict(masterKey=master_key))

    async def execute_blocking(self, bl, *args):
        """ Execute blocking code """
        return await asyncio.get_event_loop().run_in_executor(self.executor,
                                                              bl,
                                                              *args)

    async def get_db(self, database_id: str) -> DatabaseProxy:
        """ Get or create DB """

        def bl() -> DatabaseProxy:
            """ Get Notifications container blocking """
            return self.client.get_database_client(database_id)

        return await self.execute_blocking(bl)

    async def create_db(self, database_id: str) -> DatabaseProxy:
        """ Create DB """
        def bl() -> DatabaseProxy:
            """ Get Notifications container blocking """
            try:
                return self.client.create_database(id=database_id)
            except exceptions.CosmosResourceExistsError:
                return self.client.get_database_client(database_id)

        return await self.execute_blocking(bl)

    async def create_container(self, database_id: str, container_id: str,
                               partition_key: Any, **kwargs) -> ContainerProxy:
        """ Create container """
        db = await self.get_db(database_id)

        def bl() -> ContainerProxy:
            """ Get Notifications container blocking """
            try:
                return db.create_container(container_id, partition_key,
                                           **kwargs)
            except exceptions.CosmosResourceExistsError:
                return db.get_container_client(container_id)

        return await self.execute_blocking(bl)

    async def get_container(self, database_id: str, container_id: str,
                            partition_key: Any, **kwargs) -> ContainerProxy:
        """ Get or create container """
        db = await self.get_db(database_id)

        def bl() -> ContainerProxy:
            """ Get Notifications container blocking """
            return db.get_container_client(container_id)

        return await self.execute_blocking(bl)

    @staticmethod
    def get_next_page_bl(pager) -> List[Dict[any, any]]:
        """ Get Next page items Blocking """
        try:
            return list(pager.next())
        except StopIteration:
            Log.e(TAG, "get_next_page_bl:: no items found, returning '[]'",
                  exc_info=sys.exc_info())
        return list()

    async def get_initiation_items(self, notification_id,
                                   token=None) -> Tuple[List[Initiation], str]:
        """ Get Initiation Items """
        container = await self.get_initiation_container()

        def bl() -> Tuple[List[Dict[str, Any]], str]:
            """ Potential blocking code """
            # noinspection SqlDialectInspection,SqlNoDataSourceInspection
            Log.d(TAG, "get_initiation_items:: init query")
            query_iterable = container.query_items(
                query="SELECT * FROM r "
                      "WHERE r.notificationId=@notification_id "
                      "ORDER BY r._ts",
                parameters=[
                    {"name": "@notification_id", "value": notification_id},
                ],
                partition_key=notification_id,
                max_item_count=20
            )
            pager = (query_iterable.by_page(token) if token else
                     query_iterable.by_page())
            items = self.get_next_page_bl(pager)
            Log.d(TAG, f"get_initiation_items::items: {items}")
            return (
                Initiation.get_schema(unknown=EXCLUDE).load(items, many=True),
                pager.continuation_token or None
            )

        return await self.execute_blocking(bl)

    async def get_acknowledge_items(self, notification_id)\
            -> List[Acknowledge]:
        """ Get Acknowledge Items """
        container = await self.get_acknowledges_container()

        def bl() -> List[Dict[str, Any]]:
            """ Potential blocking code """
            # noinspection SqlDialectInspection,SqlNoDataSourceInspection
            items = []
            for item in container.query_items(
                query="SELECT * FROM r "
                      "WHERE r.notificationId=@notification_id "
                      "ORDER BY r._ts",
                parameters=[
                    {"name": "@notification_id", "value": notification_id},
                ],
                partition_key=notification_id
            ):
                items.append(item)
            return Acknowledge.get_schema(unknown=EXCLUDE).load(items,
                                                                many=True)

        return await self.execute_blocking(bl)

    async def query_items(self, partition_key, **kwargs):
        """ Query items """
        # TODO(s1z): IMPL ME

    async def get_item(self,
                       container: ContainerProxy,
                       item: Union[str, Dict[str, Any]],
                       partition_key: Any,
                       populate_query_metrics: Optional[bool] = None,
                       post_trigger_include: Optional[str] = None,
                       **kwargs: Any) -> Dict[str, str]:
        """ Get Item """

        def bl() -> Dict[str, str]:
            """ Potential blocking code """
            try:
                return container.read_item(
                    item=item,
                    partition_key=partition_key,
                    populate_query_metrics=populate_query_metrics,
                    post_trigger_include=post_trigger_include,
                    **kwargs)
            except exceptions.CosmosHttpResponseError as e:
                # raise
                raise ItemNotFound(e.http_error_message)
        return await self.execute_blocking(bl)

    async def create_item(self, container: ContainerProxy,
                          body: Dict[str, Any],
                          populate_query_metrics: Optional[bool] = None,
                          pre_trigger_include: Optional[str] = None,
                          post_trigger_include: Optional[str] = None,
                          indexing_directive: Optional[Any] = None,
                          **kwargs: Any) -> Dict[str, str]:
        """ Create an item in DB """

        def bl() -> Dict[str, str]:
            """ Potential blocking code """
            return container.create_item(
                body=body,
                populate_query_metrics=populate_query_metrics,
                pre_trigger_include=pre_trigger_include,
                post_trigger_include=post_trigger_include,
                indexing_directive=indexing_directive,
                **kwargs
            )
        tries = 0
        max_tries = max(kwargs.pop("max_tries", 3), 1)

        item_id = body.get("id", None)
        if item_id is None:
            body.update(dict(id=uuid.uuid4().__str__()))

        while tries < max_tries:
            try:
                return await self.execute_blocking(bl)
            except exceptions.CosmosHttpResponseError as e:
                tries += 1
                if e.status_code == 409:  # Already exists
                    # print(f"Item with {item_id} already exists")
                    if tries == max_tries:
                        raise ItemExists(e.http_error_message)
                    continue
                raise SaveItemError(e.http_error_message)
        raise SaveItemError("We've reached max_tries values!")

    async def get_conversations_container(self) -> ContainerProxy:
        """ Get Conversation container """
        from config import CosmosDBConfig

        return await self.get_container(
                CosmosDBConfig.Conversations.DATABASE,
                CosmosDBConfig.Conversations.CONTAINER,
                CosmosDBConfig.Conversations.PARTITION_KEY
            )

    async def create_notification(self, notification: NotificationCosmos)\
            -> NotificationCosmos:
        """ Crete notification to the DB """
        notification.id = uuid.uuid4().__str__()
        schema = NotificationCosmos.get_schema(unknown=EXCLUDE)
        container = await self.get_notifications_container()
        saved_item = container.create_item(body=schema.dump(notification))
        return schema.load(saved_item)

    async def get_acknowledges_container(self) -> ContainerProxy:
        """ get_acknowledges_container """
        from config import CosmosDBConfig

        return await self.get_container(
            CosmosDBConfig.Acknowledges.DATABASE,
            CosmosDBConfig.Acknowledges.CONTAINER,
            CosmosDBConfig.Acknowledges.PARTITION_KEY
        )

    async def get_notifications_container(self) -> ContainerProxy:
        """ Get Notifications container """
        from config import CosmosDBConfig

        return await self.get_container(
            CosmosDBConfig.Notifications.DATABASE,
            CosmosDBConfig.Notifications.CONTAINER,
            CosmosDBConfig.Notifications.PARTITION_KEY
        )

    async def get_messages_container(self) -> ContainerProxy:
        """ Get Messages container """
        from config import CosmosDBConfig

        return await self.get_container(
            CosmosDBConfig.Notifications.DATABASE,
            CosmosDBConfig.Notifications.CONTAINER,
            CosmosDBConfig.Notifications.PARTITION_KEY
        )

    async def get_initiation_container(self) -> ContainerProxy:
        """ Get Initiation container """
        from config import CosmosDBConfig

        return await self.get_container(
            CosmosDBConfig.Initiations.DATABASE,
            CosmosDBConfig.Initiations.CONTAINER,
            CosmosDBConfig.Initiations.PARTITION_KEY
        )

    async def get_flow_container(self) -> ContainerProxy:
        """ Get Flow container """
        from config import CosmosDBConfig

        return await self.get_container(
            CosmosDBConfig.Flows.DATABASE,
            CosmosDBConfig.Flows.CONTAINER,
            CosmosDBConfig.Flows.PARTITION_KEY
        )

    async def create_acknowledge(self, notification_id: str,
                                 account: ChannelAccount) -> Dict[str, Any]:
        """ Add acknowledge to the DB """
        container = await self.get_acknowledges_container()
        notification = AcknowledgeSchema().dump(dict(
            notification_id=notification_id,
            username=account.name,
            user_aad_id=account.aad_object_id,
            timestamp=timestamp_factory()
        ))
        return await self.create_item(container, notification)

    async def get_acknowledge(self, notification_id: str)\
            -> Optional[Acknowledge]:
        """ Get Acknowledge object """
        try:
            container = await self.get_acknowledges_container()
            items = await self.query_items(container, notification_id)
            return Acknowledge.get_schema(unknown=EXCLUDE).load(items)
        except ItemNotFound:
            return None

    async def get_conversation(self, conversation_id: str,
                               tenant_id: str = None) -> ConversationReference:
        """ Get Conversation Reference """
        from config import AppConfig

        container = await self.get_conversations_container()
        item = await self.get_item(container, conversation_id,
                                   tenant_id or AppConfig.TENANT_ID)
        return ConversationReference.get_schema(unknown=EXCLUDE)\
                                    .load(item).to_ms_reference()

    async def get_notification(self, notification_id: str)\
            -> NotificationCosmos:
        """ Get Notification """
        from config import AppConfig

        container = await self.get_notifications_container()
        item = await self.get_item(container, notification_id,
                                   AppConfig.TENANT_ID)
        return NotificationCosmos.get_schema(unknown=EXCLUDE).load(item)

    async def create_conversation_reference(self, turn_context: TurnContext)\
            -> Dict[str, Any]:
        """ Save Conversation Regerence """
        from config import CosmosDBConfig

        Log.i(__name__, "create_conversation_reference")
        activity = turn_context.activity
        reference = TurnContext.get_conversation_reference(activity)
        reference_json = ConversationReference.get_schema().dump(reference)
        container = await self.get_conversations_container()
        reference_json.update({
            CosmosDBConfig.Conversations.PK: reference.conversation.id
        })

        def bl() -> Dict[str, str]:
            """ Potential blocking code """
            return container.create_item(body=reference_json)

        try:
            return await self.execute_blocking(bl)
        except exceptions.CosmosHttpResponseError as e:
            Log.i(__name__, "create_conversation_reference::error:",
                  sys.exc_info())
            if e.status_code == 409:  # Already exists
                return reference_json
            raise SaveItemError(e.http_error_message)

    async def create_initiation(self, initiator: str,
                                notification_id: str) -> None:
        """ Save initiation """
        container = await self.get_initiation_container()
        initiation = Initiation(initiator=initiator,
                                timestamp=timestamp_factory(),
                                notification_id=notification_id)
        data = Initiation.get_schema().dump(initiation)
        await self.create_item(container, body=data)

    async def create_flow(self, cmd, url, tenant_id=None):
        """ Create Flow """
        from config import AppConfig
        container = await self.get_flow_container()
        flow = Flow(tenant_id=tenant_id or AppConfig.TENANT_ID, cmd=cmd,
                    url=url)
        data = Flow.get_schema().dump(flow)
        return await self.create_item(container, body=data)

    async def get_flow(self, cmd, tenant_id=None) -> Flow:
        """ Get Flow """
        from config import AppConfig

        container = await self.get_flow_container()
        item = await self.get_item(container, cmd,
                                   tenant_id or AppConfig.TENANT_ID)
        return Flow.get_schema(unknown=EXCLUDE).load(item)
