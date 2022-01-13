import os
from typing import List, Dict, Set, Type, Optional, TYPE_CHECKING

from d20.Manual.Logger import logging, Logger
from d20.Manual.Registration import RegistrationForm
from d20.Manual.Config import Configuration, EntityConfiguration
from d20.Manual.Utils import loadExtras
from d20.version import GAME_ENGINE_VERSION


if TYPE_CHECKING:
    from d20.Manual.Templates import PlayerTemplate


LOADED: Set[str] = set()
PLAYERS: Dict[str, 'Player'] = dict()
LOGGER: Logger = logging.getLogger(__name__)


class Player:
    def __init__(self, name: str, cls: Type['PlayerTemplate'],
                 registration: RegistrationForm) -> None:
        self.name: str = name
        self.cls: Type['PlayerTemplate'] = cls
        self.registration: RegistrationForm = registration
        self.config: Optional[EntityConfiguration] = None


def verifyPlayers(extra_players: List[str],
                  config: Configuration) -> List[Player]:
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


def loadPlayer(player_class: Type['PlayerTemplate'], **kwargs: str) -> None:
    reg: RegistrationForm = RegistrationForm(**kwargs)
    ev: str = GAME_ENGINE_VERSION
    if reg.engine_version is not None and reg.engine_version > ev:
        raise ValueError("NPC %s expects version %s or newer"
                         % (reg.name, reg.engine_version))

    if reg.name is None:
        raise ValueError("NPC does not have a name")

    global PLAYERS
    clsname: str = player_class.__qualname__
    if clsname in PLAYERS:
        raise ValueError("Player with class name %s already registered"
                         % (clsname))
    else:
        PLAYERS[clsname] = Player(reg.name, player_class, reg)


def loadPlayers(extra_players: List[str]) -> Dict[str, Player]:
    # Get this files directory
    paths: List[str] = [os.path.dirname(os.path.abspath(__file__))]
    paths.extend(extra_players)

    # Players will load via decorator invocation
    loadExtras(paths, LOADED)

    return PLAYERS


__all__ = ["loadPlayers",
           "loadPlayer"]
