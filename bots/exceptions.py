""" Bot Exceptions """


class BotException(Exception):
    """ Base Bot Exception """
    def __init__(self, message="BotError"):
        self.message = message


class ConversationNotFound(BotException):
    """ Conversation Not found exception """
    pass


class DataParsingError(BotException):
    """ Data Parsing Error """
    pass
