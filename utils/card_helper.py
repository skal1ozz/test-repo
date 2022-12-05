import os
from typing import Dict, Any, Optional, Mapping, Union

from botbuilder.core import TurnContext

from config import CARDS_PATH
from entities.json.notification import NotificationCosmos
from utils.functions import get_i18n
from utils.json_func import json_loads


FILE = "__file__"


class CardHelper:
    """ Card Helper """

    @staticmethod
    def load_assets_card(name: str) -> Union[dict[str, Any],
                                             Mapping[str, Any]]:
        """ Load a card from assets """
        filename = name + ".json" if name.find(".json") < 0 else name
        filename_path = os.path.join(CARDS_PATH, filename)
        with open(filename_path, "r") as f:
            card_data = f.read()
            card_json = json_loads(card_data)
            return card_json

    @staticmethod
    def load_portal_card(turn_context: TurnContext) -> \
            Union[dict[str, Any], Mapping[str, Any]]:
        """ Load portal card """
        u18n = get_i18n(turn_context)

        # TODO(s1z): Change this crap please and create a constructor!
        portal_card = CardHelper.load_assets_card("default_card")
        portal_card["body"][0]["items"][0]["text"] = u18n.t("portal_text")
        portal_card["body"][1]["items"][0]["actions"][0]["title"] = u18n.t(
            "portal_button_text"
        )
        return portal_card

    @staticmethod
    def create_notification_card(notification: NotificationCosmos,
                                 acknowledged_by: Optional[str] = None)\
            -> Dict[str, Any]:
        """ Create notification card """

        title = notification.title or "You got a new notification!"
        notification_id = notification.id or None
        subject = notification.subject or None
        message = notification.message or None
        url = notification.url or None
        acknowledge = notification.acknowledge
        card_body = []

        # ======================= TITLE =======================================
        if title is not None:
            card_body.append({"type": "TextBlock",
                              "size": "Medium",
                              "weight": "Bolder",
                              "text": title})

        # ======================= SUBJ and MESSAGE ============================
        if subject is not None:
            card_body.append({"type": "FactSet",
                              "facts": [{"title": "Subject:",
                                         "value": subject}]})

        # ======================= MESSAGE =================================== #
        if message is not None:
            card_body.append({"type": "FactSet",
                              "facts": [{"title": "Message:",
                                         "value": message}]})

        # ======================= URL =========================================
        if url is not None and notification_id is not None:
            url_title = url.title or "Open Notification"
            card_body.append({
                "type": "ActionSet",
                "actions": [{"type": "Action.Submit",
                             "title": url_title,
                             "data": {
                                 "msteams": {
                                     "type": "task/fetch"
                                 },
                                 "mx": {
                                     "type": "task/notification",
                                     "notificationId": notification_id
                                 }
                             }}]
            })
            card_body.append({
                "type": "Container",
                "items": [
                    {
                        "type": "ActionSet",
                        "actions": [
                            {
                                "type": "Action.OpenUrl",
                                "title": "Open in Browser",
                                "url": url.link
                            }
                        ]
                    }
                ]
            })
        # ======================= URL =========================================
        if acknowledge is not None and acknowledge and acknowledged_by is None:
            card_body.append({
                "type": "ActionSet",
                "actions": [{"type": "Action.Submit",
                             "title": "Acknowledge",
                             "data": {
                                 "mx": {
                                     "type": "acknowledge",
                                     "notificationId": notification_id
                                 }
                             }}]
            })
        if acknowledged_by is not None:
            card_body.append({"type": "FactSet",
                              "facts": [{"title": "Acknowledged:",
                                         "value": acknowledged_by}]})

        return {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.5",
            "body": card_body
        }
