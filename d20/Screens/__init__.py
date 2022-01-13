import os
from typing import TYPE_CHECKING, List, Dict, Set, Type, Optional

from d20.Manual.Logger import logging, Logger
from d20.Manual.Registration import ScreenRegistrationForm
from d20.Manual.Config import Configuration, EntityConfiguration
from d20.Manual.Utils import loadExtras
from d20.version import GAME_ENGINE_VERSION


if TYPE_CHECKING:
    from d20.Manual.Templates import ScreenTemplate


LOADED: Set[str] = set()
SCREENS: Dict[str, 'Screen'] = dict()
LOGGER: Logger = logging.getLogger(__name__)


class Screen:
    def __init__(self, name: str, cls: Type['ScreenTemplate'],
                 registration: ScreenRegistrationForm) -> None:
        self.name: str = name
        self.cls: Type['ScreenTemplate'] = cls
        self.registration: ScreenRegistrationForm = registration
        self.config: Optional[EntityConfiguration] = None


def verifyScreens(extra_screens: List[str],
                  config: Configuration) -> Dict[str, Screen]:
    """Load and verify screens

        This function takes screens available on-disk and loads
        them for use by the framework

        Args:
            extra_screens: List locations of where external screens reside
            config: Config object

        Return: A dict of screen names to objects which contains each
            screen's information. Each object contains the following:
                name - The name of the Screen
                cls - The class of the screen
                engine_version - The engine version specified by the screen
                config - The config for the specific screen
    """

    try:
        loadScreens(extra_screens)
    except Exception:
        LOGGER.exception("Unable to load screens")
        raise

    screens = dict()
    # Iterate through screens and register them
    for (screen_class_name, screen) in SCREENS.items():
        screen.config = config.screenConfig(screen.name)
        screens[screen.name] = screen

    return dict(screens)


def loadScreen(screen_class: Type['ScreenTemplate'], **kwargs: str) -> None:
    reg: ScreenRegistrationForm = ScreenRegistrationForm(**kwargs)
    ev: str = GAME_ENGINE_VERSION
    if reg.engine_version > ev:
        raise ValueError("Player %s expects version %s or newer"
                         % (reg.name, reg.engine_version))

    if reg.name is None:
        raise ValueError("NPC does not have a name")

    global SCREENS
    clsname: str = screen_class.__qualname__
    if clsname in SCREENS:
        LOGGER.warning("Screen with class name %s already registered"
                       % (clsname))
        return

    for (name, scls) in SCREENS.items():
        if reg.name == scls.registration.name:
            LOGGER.warning("Screen with name %s already registered"
                           % (reg.name))
            return

    # If no errors, add screen to list
    SCREENS[clsname] = Screen(reg.name, screen_class, reg)


def loadScreens(extra_screens: List[str]) -> Dict[str, Screen]:
    # Get this files directory
    paths = [os.path.dirname(os.path.abspath(__file__))]
    paths.extend(extra_screens)

    loadExtras(paths, LOADED)

    return SCREENS


__all__ = ["loadScreens",
           "loadScreen"]
