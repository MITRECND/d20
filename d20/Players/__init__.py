import os

from d20.Manual.Logger import logging
from d20.Manual.Registration import RegistrationForm
from d20.Manual.Utils import loadExtras
from d20.version import GAME_ENGINE_VERSION

from typing import Dict, Set

LOADED: Set = set()
PLAYERS: Dict = dict()
LOGGER = logging.getLogger(__name__)


class Player:
    def __init__(self, name, cls, registration):
        self.name = name
        self.cls = cls
        self.registration = registration
        self.config = None


def verifyPlayers(extra_players, config):
    """Load and verify players

        This function finds and loads player from on-disk for use
        by the framework

        Args:
            extra_players: List of where external players may be found
            config: A Config object instance

        Return: A list of objects which contains each player's information.
            Each object contains the following:
                name - The name of the player
                cls - The class of the player
                registration - The registration information for the player
                config - The config for the specific player
    """
    try:
        loadPlayers(extra_players)
    except Exception:
        LOGGER.exception("Unable to load players")
        raise

    # Iterate through Players and register them
    for (player_class_name, player) in PLAYERS.items():
        player.config = config.playerConfig(player.name)

    return list(PLAYERS.values())


def loadPlayer(player_class, **kwargs):
    reg = RegistrationForm(**kwargs)
    ev = GAME_ENGINE_VERSION
    if reg.engine_version > ev:
        raise ValueError("Player %s expects version %s or newer"
                         % (reg.name, reg.engine_version))
    global PLAYERS
    clsname = player_class.__qualname__
    if clsname in PLAYERS:
        raise ValueError("Player with class name %s already registered"
                         % (clsname))
    else:
        PLAYERS[clsname] = Player(reg.name, player_class, reg)


def loadPlayers(extra_players):
    # Get this files directory
    paths = [os.path.dirname(os.path.abspath(__file__))]
    paths.extend(extra_players)

    # Players will load via decorator invocation
    loadExtras(paths, LOADED)

    return PLAYERS


__all__ = ["loadPlayers",
           "loadPlayer"]
