import logging as origLogging
import sys
from typing import Optional, Set


default_log_format: str = "%(message)s"
debug_log_format: str = ('%(levelname) -10s %(asctime)s %(name) '
                         '-30s %(funcName) -35s %(lineno) -5d: %(message)s')

DEFAULT_LEVEL: int = origLogging.INFO
SUPPRESS_LEVEL: int = origLogging.ERROR
Logger = origLogging.Logger


class logging:
    ENABLE_DEBUG: bool = False
    ENABLE_VERBOSE: bool = False
    LOGGERS: Set[origLogging.Logger] = set()

    @staticmethod
    def setupLogger(
            debug: bool = False,
            verbose: bool = False,
            console: bool = False) -> None:
        """Setup origLogging infrastructure

            This function sets up the logger based on the args, changing
            the output depending on level
        """

        logging.ENABLE_DEBUG = debug
        logging.ENABLE_VERBOSE = verbose

        # Setup logging to stdout
        if console:
            try:
                logHandler: origLogging.StreamHandler \
                     = origLogging.StreamHandler(sys.stdout)
            except Exception as e:
                raise Exception(("Unable to setup logger to stdout\n"
                                "Error Message: %s\n" % str(e)))
            logFormatter: origLogging.Formatter = origLogging.Formatter(
                debug_log_format
                if logging.ENABLE_DEBUG
                else default_log_format
            )
            logHandler.setFormatter(logFormatter)

            # Set defaults for all loggers
            root_logger: origLogging.Logger = origLogging.getLogger()
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
    def setLoggerLevel(logger: origLogging.Logger) -> None:
        if logging.ENABLE_DEBUG:
            logger.setLevel(origLogging.DEBUG)
        elif logging.ENABLE_VERBOSE:
            logger.setLevel(DEFAULT_LEVEL)
        else:
            logger.setLevel(SUPPRESS_LEVEL)

    @staticmethod
    def getLogger(name: Optional[str] = None) -> origLogging.Logger:
        logger: origLogging.Logger = origLogging.getLogger(name)
        if logger.name.startswith('d20'):
            logging.setLoggerLevel(logger)
            logging.LOGGERS.add(logger)
        return logger
