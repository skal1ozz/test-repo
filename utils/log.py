""" Log helper module """
import logging
import traceback


class Log:
    """ Logger. This is a pretty useful 'Java style' logger """

    @staticmethod
    def log(level, source, message="", exc_info=None):
        """ log method """
        logger = logging.getLogger()
        line = "{source}{message}{exc}"
        exc = ''
        if isinstance(exc_info, (list, tuple)):
            ex_type, ex_value, ex_traceback = exc_info
            exc = ": " + ''.join(
                traceback.format_exception(ex_type, ex_value, ex_traceback)
            )
        message = "::{}".format(message) if message else ""
        logger.log(level, line.format(source=source, message=message, exc=exc))

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
