import logging as origLogging
import sys

from typing import Set

default_log_format = "%(message)s"
debug_log_format = ('%(levelname) -10s %(asctime)s %(name) '
                    '-30s %(funcName) -35s %(lineno) -5d: %(message)s')

DEFAULT_LEVEL = origLogging.INFO
SUPPRESS_LEVEL = origLogging.ERROR


class logging:
    ENABLE_DEBUG = False
    ENABLE_VERBOSE = False
    LOGGERS: Set[origLogging.Logger] = set()

    @staticmethod
    def setupLogger(
            debug=False,
            verbose=False,
            console=False):
        """Setup origLogging infrastructure

            This function sets up the logger based on the args, changing
            the output depending on level
        """

        logging.ENABLE_DEBUG = debug
        logging.ENABLE_VERBOSE = verbose

        # Setup logging to stdout
        if console:
            try:
                logHandler = origLogging.StreamHandler(sys.stdout)
            except Exception as e:
                raise Exception(("Unable to setup logger to stdout\n"
                                "Error Message: %s\n" % str(e)))
            logFormatter = origLogging.Formatter(
                debug_log_format
                if logging.ENABLE_DEBUG
                else default_log_format
            )
            logHandler.setFormatter(logFormatter)

            # Set defaults for all loggers
            root_logger = origLogging.getLogger()
            root_logger.handlers = []
            root_logger.addHandler(logHandler)
            if logging.ENABLE_DEBUG or logging.ENABLE_VERBOSE:
                root_logger.setLevel(DEFAULT_LEVEL)
            else:
                root_logger.setLevel(SUPPRESS_LEVEL)

        # Update any loggers that have already been provisioned
        for logger in logging.LOGGERS:
            logging.setLoggerLevel(logger)

    @staticmethod
    def setLoggerLevel(logger):
        if logging.ENABLE_DEBUG:
            logger.setLevel(origLogging.DEBUG)
        elif logging.ENABLE_VERBOSE:
            logger.setLevel(DEFAULT_LEVEL)
        else:
            logger.setLevel(SUPPRESS_LEVEL)

    @staticmethod
    def getLogger(name=None):
        logger = origLogging.getLogger(name)
        if logger.name.startswith('d20'):
            logging.setLoggerLevel(logger)
            logging.LOGGERS.add(logger)
        return logger
