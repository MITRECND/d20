class WaitTimeoutError(Exception):
    """Exception to indicate a timeout occurred waiting
       for a fact to arrive"""


class StreamTimeoutError(Exception):
    """Exception to indicate timeout
       has been reached"""


class PlayerCreationError(Exception):
    """Exception to indicate a player could not be created
    """


class DuplicateObjectError(Exception):
    """Exception to indicate an object already exists
    """


class TemporaryDirectoryError(Exception):
    """Exception to indicate issue with temporary directory setup
    """


class ConsoleError(Exception):
    """Exception to indicate an issue with the console
    """


class NotFoundError(Exception):
    """Exception to indicate an item was not found
    """


class RPCTimeoutError(Exception):
    """Exception to indicate a timeout occurred when waiting
       for a RPCResponse"""


class ConfigNotFoundError(Exception):
    """Exception to indicate a config file was not found in
       the entity"""


__all__ = ["WaitTimeoutError",
           "StreamTimeoutError",
           "PlayerCreationError",
           "DuplicateObjectError",
           "TemporaryDirectoryError",
           "ConsoleError",
           "NotFoundError",
           "RPCTimeoutError",
           "ConfigNotFoundError"
           ]
