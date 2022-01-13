import os
from typing import TYPE_CHECKING, List, Dict, Set, Type, Optional

from d20.Manual.Logger import logging, Logger
from d20.Manual.Registration import BackStoryRegistrationForm
from d20.Manual.Utils import loadExtras
from d20.Manual.Facts import Fact, getFactClass
from d20.Manual.Config import Configuration, EntityConfiguration
from d20.version import GAME_ENGINE_VERSION


if TYPE_CHECKING:
    from d20.Manual.Templates import BackStoryTemplate


LOADED: Set = set()
STORIES: Dict[str, 'BackStory'] = dict()
LOGGER: Logger = logging.getLogger(__name__)


class BackStory:
    def __init__(self, name: str, cls: Type['BackStoryTemplate'],
                 registration: BackStoryRegistrationForm) -> None:
        self.name: str = name
        self.cls: Type['BackStoryTemplate'] = cls
        self.registration: BackStoryRegistrationForm = registration
        self.config: Optional[EntityConfiguration] = None


def resolveBackStoryFacts(backstory_facts: Dict) -> List[Fact]:
    """Takes list of dicts that are then turned into fact class instances

    Arguments:
        backstory_facts {list(dict)]} -- A list of dicts that represent
            d20 facts
    """
    try:
        backstory_facts['facts']
    except KeyError:
        LOGGER.error("Provide backstory facts are malformed")
        return []

    facts: List[Fact] = list()
    for fact_template in backstory_facts['facts']:
        try:
            fact_class: Type[Fact] = getFactClass(fact_template['name'])
            LOGGER.debug(fact_class)
        except Exception:
            LOGGER.exception("Unknown fact class %s" % (fact_template['name']))
            continue

        arguments = fact_template['arguments']
        fact: Fact = fact_class(**arguments)
        facts.append(fact)

    return facts


def verifyBackStories(extra_backstories: List[str],
                      config: Configuration) -> List[BackStory]:
    """Load and verify BackStories

        This function takes backstories found on-disk and loads them
        for use by the framework

        Args:
            extra_backstories: List of paths where external backstories
                may be found
            config: Config object instance

        Return: A list of objects which contains each backstory's information.
            Each object contains the following:
                name - The name of the backstory
                cls - The class of the backstory
                registration - The registration information for the backstory
                config - The config for the specific backstory
    """
    try:
        loadBackStories(extra_backstories)
    except Exception:
        LOGGER.exception("Unable to load BackStories")
        raise

    # Iterate through BackStories and inject configuration
    for (backstory_class_name, backstory) in STORIES.items():
        backstory.config = config.backStoryConfig(backstory.name)

    return list(STORIES.values())


def loadBackStory(backstory_class: Type['BackStoryTemplate'],
                  **kwargs: str) -> None:
    reg: BackStoryRegistrationForm = BackStoryRegistrationForm(**kwargs)
    ev: str = GAME_ENGINE_VERSION
    if reg.engine_version is not None and reg.engine_version > ev:
        raise ValueError("BackStory %s expects version %s or newer"
                         % (reg.name, reg.engine_version))

    if reg.name is None:
        raise ValueError("NPC does not have a name")

    global STORIES
    clsname: str = backstory_class.__qualname__
    if clsname in STORIES:
        LOGGER.warning("BackStory with class name %s already registered"
                       % (clsname))
        return

    for (name, ncls) in STORIES.items():
        if reg.name == ncls.registration.name:
            LOGGER.warning("BackStory with name %s already registered"
                           % (reg.name))
            return

    # If no errors, add backstory to list
    STORIES[clsname] = BackStory(reg.name, backstory_class, reg)


def loadBackStories(extra_backstories: List[str]) -> None:
    # Get this files directory
    paths: List[str] = [os.path.dirname(os.path.abspath(__file__))]
    paths.extend(extra_backstories)

    loadExtras(paths, LOADED)


__all__ = ["loadBackStories",
           "loadBackStory",
           "resolveBackStoryFacts"]
