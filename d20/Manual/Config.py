import yaml
import cerberus
from d20.Manual.Logger import logging

LOGGER = logging.getLogger(__name__)


d20_schema = {
    'extra-players': {'rename': 'extra_players'},
    'extra_players': {
        'type': ['string', 'list'],
        'schema': {'type': 'string'}
    },

    'extra-npcs': {'rename': 'extra_npcs'},
    'extra_npcs': {
        'type': ['string', 'list'],
        'schema': {'type': 'string'}
    },
    'extra-actions': {'rename': 'extra_actions'},
    'extra_actions': {
        'type': ['string', 'list'],
        'schema': {'type': 'string'}
    },
    'extra-screens': {'rename': 'extra_screens'},
    'extra_screens': {
        'type': ['string', 'list'],
        'schema': {'type': 'string'}
    },
    'extra-backstories': {'rename': 'extra_backstories'},
    'extra_backstories': {
        'type': ['string', 'list'],
        'schema': {'type': 'string'}
    },
    'extra-facts': {'rename': 'extra_facts'},
    'extra_facts': {
        'type': ['string', 'list'],
        'schema': {'type': 'string'}
    },
    'temporary': {
        'type': 'string'
    },
    'graceTime': {
        'type': 'integer'
    },
    'maxGameTime': {
        'type': 'integer'
    },
    'maxTurnTime': {
        'type': 'integer'
    }
}

common_schema = {
    'http_proxy': {
        'type': 'string'
    },
    'https_proxy': {
        'type': 'string'
    }

}

d20_config_example = """
d20:
#     Path to extra players
#     extra-players:  # string or list
#     Path to extra npcs
#     extra-npcs:  # string or list
#     Path to extra facts
#     extra-facts: # string or list
#     Path to extra actions
#     extra-actions: # string or list
#     Path to extra screens
#     extra-screens: # string or list
#     # Number of seconds Game Master will wait on a deadlock
#     graceTime: 1 # integer
#     # Number of seconds Game Master will run the entire game
#     maxGameTime: 10 # integer
#     # Directory to write temporary files
#     temporary: # string

"""


class EntityConfiguration:
    def __init__(self, myconfig, common):
        if not isinstance(myconfig, dict):
            raise TypeError("Expected 'myconfig' to be a dict")
        if not isinstance(common, dict):
            raise TypeError("Expected 'common' to be a dict")
        self.options = myconfig
        self.common = common


class Configuration:
    """Configuration helper class

        This class takes care of parsing the config for d20 by either parsing
        a raw file or using a loaded dictionary. It then provides easy access
        to expected sections with sane defaults. This class also takes an
        instance (assumed to be a Namespace instance) and injects/augments
        certain fields
    """
    def __init__(self, configFile=None, config=None, args=None):
        self._config_ = dict()

        if configFile is not None:
            try:
                with open(configFile, 'r') as f:
                    rawConfig = f.read()
            except FileNotFoundError:
                LOGGER.exception("Unable to find configuration file")
                raise
            except Exception:
                LOGGER.exception(("Unexpected exception attempting to "
                                 "parse configuration file"))
                raise

            try:
                config = yaml.safe_load(rawConfig)
            except Exception:
                LOGGER.exception(("Unable to parse yaml data from "
                                 "configuration file"))
                raise

        if config is not None:
            if not isinstance(config, dict):
                raise TypeError("config must be dict type")

            self._config_ = config

            # Inject common config into every element
            for (section, sconfig) in self._config_.items():
                if section not in ['Players',
                                   'NPCS',
                                   'Screens',
                                   'Actions',
                                   'BackStories']:
                    continue

                for (element, econfig) in sconfig.items():
                    if (not isinstance(econfig, dict)):
                        raise TypeError("Expected a dictionary for %s"
                                        % (element))
                    if 'common' in econfig.keys():
                        raise ValueError("The 'common' key is reserved")

        # Check types of d20 sections and inject into
        # args if applicable
        if 'd20' in self._config_:
            d20_validator = cerberus.Validator(d20_schema)
            valid = d20_validator.validate(self._config_['d20'])
            if not valid:
                raise ValueError(
                    "Unable to verify d20 config: %s"
                    % (d20_validator.errors))

            self._config_['d20'] = d20_validator.normalized(
                self._config_['d20'])

            for (key, value) in self._config_['d20'].items():
                if key.startswith('extra_'):
                    if isinstance(value, str):
                        value = [value]
                    if args is not None:
                        try:
                            getattr(args, key).extend(value)
                        except AttributeError:
                            setattr(args, key, value)
                else:
                    if args is not None:
                        setattr(args, key, value)

    @property
    def players(self):
        return self._config_.get('Players', dict())

    def playerConfig(self, playerName):
        config = self.players.get(playerName, dict())
        return EntityConfiguration(config, self.common)

    @property
    def npcs(self):
        return self._config_.get('NPCS', dict())

    def npcConfig(self, NPCName):
        config = self.npcs.get(NPCName, dict())
        return EntityConfiguration(config, self.common)

    @property
    def backStories(self):
        return self._config_.get('BackStories', dict())

    def backStoryConfig(self, BackStoryName):
        config = self.backStories.get(BackStoryName, dict())
        return EntityConfiguration(config, self.common)

    @property
    def screens(self):
        return self._config_.get('Screens', dict())

    def screenConfig(self, screenName):
        config = self.screens.get(screenName, dict())
        return EntityConfiguration(config, self.common)

    @property
    def actions(self):
        return self._config_.get('Actions', dict())

    def actionConfig(self, actionName):
        config = self.actions.get(actionName, dict())
        return EntityConfiguration(config, self.common)

    @property
    def d20(self):
        return self._config_.get('d20', dict())

    @property
    def common(self):
        return self._config_.get('common', dict())
