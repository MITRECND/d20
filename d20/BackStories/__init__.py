import os

from d20.Manual.Logger import logging
from d20.Manual.Registration import BackStoryRegistrationForm
from d20.Manual.Utils import loadExtras
from d20.version import GAME_ENGINE_VERSION
from d20.Manual.Facts import getFactClass

from typing import Set, Dict

LOADED: Set = set()
STORIES: Dict = dict()
LOGGER = logging.getLogger(__name__)


class BackStory:
    def __init__(self, name, cls, registration):
        self.name = name
        self.cls = cls
        self.registration = registration
        self.config = None


def resolveBackStoryFacts(backstory_facts):
    """Takes list of dicts that are then turned into fact class instances

    Arguments:
        backstory_facts {list(dict)]} -- A list of dicts that represent
            d20 facts
    """
    try:
        backstory_facts['facts']
    except KeyError:
        LOGGER.error("Provide backstory facts are malformed")
        return

    facts = list()
    for fact_template in backstory_facts['facts']:
        try:
            fact_class = getFactClass(fact_template['name'])
            LOGGER.debug(fact_class)
        except Exception:
            LOGGER.exception("Unknown fact class %s" % (fact_template['name']))
            continue

        arguments = fact_template['arguments']
        fact = fact_class(**arguments)
        facts.append(fact)

    return facts


def verifyBackStories(extra_backstories, config):
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


def loadBackStory(backstory_class, **kwargs):
    reg = BackStoryRegistrationForm(**kwargs)
    ev = GAME_ENGINE_VERSION
    if reg.engine_version > ev:
        raise ValueError("BackStory %s expects version %s or newer"
                         % (reg.name, reg.engine_version))

    global STORIES
    clsname = backstory_class.__qualname__
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


def loadBackStories(extra_backstories):
    # Get this files directory
    paths = [os.path.dirname(os.path.abspath(__file__))]
    paths.extend(extra_backstories)

    loadExtras(paths, LOADED)


__all__ = ["loadBackStories",
           "loadBackStory",
           "resolveBackStoryFacts"]
