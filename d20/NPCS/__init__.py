import os
from d20.Manual.Config import Configuration

from d20.Manual.Logger import logging
from d20.Manual.Registration import RegistrationForm
from d20.Manual.Utils import loadExtras
from d20.version import GAME_ENGINE_VERSION

from typing import List, Dict, TYPE_CHECKING, Set, TypeVar, Type, Optional
if TYPE_CHECKING:
    from d20.Manual.Logger import Logger
    Tnpc = TypeVar('Tnpc', bound='NPC')


LOADED: Set[str] = set()
NPCS: Dict[str, 'NPC'] = dict()
LOGGER: Logger = logging.getLogger(__name__)


class NPC:
    def __init__(self, name: str, cls: Type[Tnpc],
                 registration: RegistrationForm) -> None:
        self.name: str = name
        self.cls: Type[Tnpc] = cls
        self.registration: RegistrationForm = registration
        self.config: Optional[Configuration] = None


def verifyNPCs(extra_npcs: List[str], config: Configuration) -> List[NPC]:
    """Load and verify NPCS

        This function takes npcs found on-disk and loads them
        for use by the framework

        Args:
            extra_npcs: List of paths where external npcs may be found
            config: Config object instance

        Return: A list of objects which contains each npc's information.
            Each object contains the following:
                name - The name of the npc
                cls - The class of the npc
                registration - The registration information for the npc
                config - The config for the specific npc
    """
    try:
        loadNPCS(extra_npcs)
    except Exception:
        LOGGER.exception("Unable to load NPCS")
        raise

    # Iterate through NPCs and inject configuration
    for (npc_class_name, npc) in NPCS.items():
        npc.config = config.npcConfig(npc.name)

    return list(NPCS.values())


def loadNPC(npc_class: Type[Tnpc], **kwargs: str) -> None:
    reg: RegistrationForm = RegistrationForm(**kwargs)
    ev: str = GAME_ENGINE_VERSION
    if reg.engine_version > ev:
        raise ValueError("NPC %s expects version %s or newer"
                         % (reg.name, reg.engine_version))

    global NPCS
    clsname: str = npc_class.__qualname__
    if clsname in NPCS:
        LOGGER.warning("NPC with class name %s already registered"
                       % (clsname))
        return

    for (name, ncls) in NPCS.items():
        if reg.name == ncls.registration.name:
            LOGGER.warning("NPC with name %s already registered"
                           % (reg.name))
            return

    # If no erorrs, add npc to list
    NPCS[clsname] = NPC(reg.name, npc_class, reg)


def loadNPCS(extra_npcs: List[str]) -> None:
    # Get this files directory
    paths: List[str] = [os.path.dirname(os.path.abspath(__file__))]
    paths.extend(extra_npcs)

    loadExtras(paths, LOADED)


__all__ = ["loadNPCS",
           "loadNPC"]
