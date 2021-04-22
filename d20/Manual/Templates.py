from d20.Players import loadPlayer
from d20.NPCS import loadNPC
from d20.Screens import loadScreen
from d20.BackStories import loadBackStory
from d20.Manual.Logger import logging

LOGGER = logging.getLogger(__name__)


def registerNPC(*args, **kwargs):
    """A decorator for registering an NPC

        This decorator expects keyword arguments that match up with the
        RegistrationForm class from d20.Manual.Registration
    """
    def _registerNPC(cls):
        LOGGER.debug("Registering NPC %s"
                     % (cls.__qualname__))
        loadNPC(cls, **kwargs)
        return cls
    return _registerNPC


def registerBackStory(*args, **kwargs):
    """A decorator for registering an BackStory

        This decorator expects keyword arguments that match up with the
        BackStoryRegistrationForm class from d20.Manual.Registration
    """
    def _registerBackStory(cls):
        LOGGER.debug("Registering BackStory %s"
                     % (cls.__qualname__))
        loadBackStory(cls, **kwargs)
        return cls
    return _registerBackStory


def registerPlayer(*args, **kwargs):
    """A decorator for registering a Player

        This decorator expects keyword arguments that match up with the
        RegistrationForm class from d20.Manual.Registration
    """
    def _registerPlayer(cls):
        LOGGER.debug("Registering Player %s"
                     % (cls.__qualname__))
        loadPlayer(cls, **kwargs)
        return cls
    return _registerPlayer


def registerScreen(*args, **kwargs):
    """A decorator for registering a Screen

        This decorator expects kwargs which cooresponds to the
        ScreenRegistrationForm class
    """
    def _registerScreen(cls):
        LOGGER.debug("Registering Screen %s"
                     % (cls.__qualname__))
        loadScreen(cls, **kwargs)
        return cls
    return _registerScreen


class PlayerTemplate:
    """Player template to ease player creation. Inherit from this class

        This class does some basic high-level common functions required by
        the framework to work
    """
    def __init__(self, **kwargs):
        """PlayerTemplate __init__ function

            Please ensure you call this class's init function in your Player
        """
        if 'console' not in kwargs:
            raise RuntimeError("Player Console Interface not passed in "
                               "to init of Player")
        self.console = kwargs['console']
        if 'options' in kwargs:
            self.options = kwargs['options']
        else:
            self.options = dict()

    def handleFact(self, **kwargs):
        """Function that is called to handle a 'fact'

            When the framework is presented with a fact that a player has
            registered interest in, this function will be invoked in a fresh
            instance of the class.
        """
        raise NotImplementedError("Player Implementation Required")

    def handleHypothesis(self, **kwargs):
        """Function that is called to handle a 'hypothesis'

            When the framework is presented with a hypothesis that a player has
            registered interest in, this function will be invoked in a fresh
            instance of the class.
        """
        raise NotImplementedError("Player Implementation Required")

    def saveState(self, **kwargs):
        """Function that is called to enable a player instance to save state

            TBD
        """
        raise NotImplementedError("Player implementation Required")

    def loadState(self, **kwargs):
        """Function that is called to load saved state information

            TBD
        """
        raise NotImplementedError("Player implementation Required")


class NPCTemplate:
    """NPC template to ease npc creation. Inherit from this class

        This class does some basic high-level common functions required by
        the framework to work
    """
    def __init__(self, **kwargs):
        """NPCTemplate __init__ function

            Please ensure you call this class's init function in your NPC
        """
        if 'console' not in kwargs:
            raise RuntimeError("NPC Console Interface not passed in "
                               "to init of NPC")
        self.console = kwargs['console']
        if 'options' in kwargs:
            self.options = kwargs['options']
        else:
            self.options = dict()

    def handleData(self, **kwargs):
        """Function called when new object seen

            When the framework is presented with a new object it is
            given to the NPC in kwargs as 'data', i.e., kwargs['data']
        """
        raise NotImplementedError("NPC Implementation Required")


class BackStoryTemplate:
    """BackStory template to ease backstory creation. Inherit from this class

        This class does some basic high-level common functions required by
        the framework to work
    """
    def __init__(self, **kwargs):
        """BackStoryTemplate __init__ function

            Please ensure you call this class's init function in your BackStory
        """
        if 'console' not in kwargs:
            raise RuntimeError("BackStory Console Interface not passed in "
                               "to init of BackStory")
        self.console = kwargs['console']
        if 'options' in kwargs:
            self.options = kwargs['options']
        else:
            self.options = dict()

    def handleFact(self, **kwargs):
        """Function that is called to handle a 'fact'

            When the framework is presented with a fact that a backstory has
            registered interest in, it is given to the backstory as 'fact'
        """
        raise NotImplementedError("BackStory Implementation Required")


class ScreenTemplate:
    """Parent class for Screens

        This class serves as the parent for any screen class and provides
        some basic setup needed by the framework
    """
    def __init__(self, **kwargs):
        self.objects = None
        self.facts = None
        self.hyps = None
        self.options = dict()

        for (key, value) in kwargs.items():
            if key == 'objects':
                self.objects = value
            if key == 'facts':
                self.facts = value
            if key == 'hyps':
                self.hyps = value
            if key == 'options':
                self.options = value

        if self.objects is None:
            raise RuntimeError("'objects' must be supplied in kwargs")

        if self.facts is None:
            raise RuntimeError("'facts' must be supplied in kwargs")

        if self.hyps is None:
            raise RuntimeError("'hyps' must be supplied in kwargs")

    def filter(self):
        """filter is meant to be used to provide a trimmed down view of data
        based on configuration provided by the user. This function should be
        called the present function.

        Arguments: None

        Returns: gameData (object/dict) - the gameData is opaque and defined
        by the screen but should be predictable in format.
        """
        raise NotImplementedError("This method must be overriden by children")

    def present(self):
        """present is meant to provide a printable string for user consumption.
        By convention it should call the filter function (above) before
        returning anything
        """
        raise NotImplementedError("This method must be overriden by children")
