import sys
import os
from typing import Dict

from d20.Manual.Options import Arguments
from d20.Manual.Logger import logging

LOGGER = logging.getLogger(__name__)

ACTION_INVENTORY: Dict = dict()


def registerAction(*args, **kwargs):
    """A decorator for registering an action

    """
    def _registerAction(cls):
        LOGGER.debug("Registering Action %s"
                     % (cls.__qualname__))
        reg = ActionRegistrationForm(**kwargs)
        global ACTION_INVENTORY
        if reg.name not in ACTION_INVENTORY.keys():
            ACTION_INVENTORY[reg.name] = type(
                'actionstub', tuple(), {'registration': reg})
            cls.options = Config._for(reg.name)
        return cls
    return _registerAction


class ActionRegistrationForm:
    """Action metadata helper class
    """
    def __init__(self, *args, **kwargs):
        self.name = None
        self.description = None
        self.options = Arguments()

        for (key, val) in kwargs.items():
            if key == 'name':
                self.name = val
            elif key == 'description':
                self.description = val
            elif key == 'options':
                if not isinstance(val, Arguments):
                    raise TypeError("'options must be of type 'Arguments'")

                self.options = val
            else:
                raise TypeError('%s is an invalid keyword argument' % (key))

        if self.name is None:
            raise AttributeError("Action must define name")


class _Config_:
    """Real object that stores/tracks config.

        Public 'Config' needs to exist at code creation so it can be
        imported into other code, but since config might not be available
        that is abstracted
    """
    def __init__(self, config):
        self._config_ = config

    def _for(self, name):
        action_config = self._config_.actionConfig(name)
        out_config = dict()
        if name not in ACTION_INVENTORY:
            LOGGER.warning("Config for unregistered action requested")
            out_config = action_config.options
            out_config['common'] = action_config.common
        else:
            parser = ACTION_INVENTORY[name].registration.options
            out_config = parser.parse(
                action_config.options, action_config.common)

        return out_config


class Config:
    """Convenience object to access action config

        This class is setup globally and provides access for
        action configs by using the '_for' function. E.g.,
        Config._for('foo') will attempt to return the config for 'foo'
        from the Actions section of the config
    """
    _config_obj_ = None

    @classmethod
    def _for(cls, name):
        if cls._config_obj_ is None:
            LOGGER.warning("Config._for called before action loader setup")
            return dict()
        else:
            return cls._config_obj_._for(name)


def setupActionLoader(extra_actions, config):
    """Init sequence for 'Actions'

        This function injects the different action paths found
        into the python interpreter's search location list, effectively
        extending the list globally. It also setups the module-scoped
        'Config' object which is a convenience class for getting a
        config section for something
    """

    global Config
    Config._config_obj_ = _Config_(config)

    # Get the absolute paths in case relative paths were passed in
    try:
        abspaths = [os.path.abspath(path) for path in extra_actions]
    except Exception:
        print("Unable to resolve action paths")
        exit(1)

    try:
        sys.modules['d20.Actions'].__spec__.\
            submodule_search_locations.extend(abspaths)
    except Exception:
        print("Unable to setup Actions")
        exit(1)


__all__ = ["setupActionLoader",
           "Config"]
