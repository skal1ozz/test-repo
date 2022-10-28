from __future__ import absolute_import
from __future__ import unicode_literals
import traceback
import logging


def init_logging(filename=None, level=None):
    """ init logging on the app level """
    logging_config = {"format": "%(asctime)-23s %(levelname)8s::%(filename)s::"
                                "%(funcName)s: %(message)s",
                      "level": level or logging.DEBUG}
    if filename is not None:
        logging_config["filename"] = filename
    logging.getLogger().handlers = []
    logging.basicConfig(**logging_config)


class Log(object):
    """ Logger class """

    LEVEL = logging.DEBUG

    logger = logging.getLogger()
    logging_config = {"format": "%(asctime)-23s %(levelname)8s::"
                                "%(filename)s::%(funcName)s: %(message)s",
                      "level": logging.DEBUG}
    logging.basicConfig(**logging_config)

    @staticmethod
    def log(level, source, message="", exc_info=None):
        """ log method """
        logger = logging.getLogger(source)
        line = "{message}{exc}"
        exc = ''
        if isinstance(exc_info, (list, tuple)):
            ex_type, ex_value, ex_traceback = exc_info
            exc = ": " + ''.join(
                traceback.format_exception(ex_type, ex_value, ex_traceback)
            )
        message = "::{}".format(message) if message else ''
        logger.log(level, line.format(message=message, exc=exc))

    @staticmethod
    def w(source, message="", exc_info=None):
        """ warning level """
        return Log.log(logging.WARN, source, message, exc_info)

    @staticmethod
    def d(source, message="", exc_info=None):
        """ debug level """
        return Log.log(logging.DEBUG, source, message, exc_info)

    @staticmethod
    def i(source, message="", exc_info=None):
        """ info level """
        return Log.log(logging.INFO, source, message, exc_info)

    @staticmethod
    def e(source, message="error", exc_info=None):
        """ error level """
        return Log.log(logging.ERROR, source, message, exc_info)
