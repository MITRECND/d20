import pkg_resources
from packaging import version as __version
from collections.abc import Iterable
from d20.Manual.Facts import (isFactGroup,
                              resolveFacts)
from d20.Manual.Options import Arguments


def _test_version_string(version):
    try:
        version_test = pkg_resources.parse_version(version)
        if isinstance(version_test, __version.LegacyVersion):
            raise ValueError("Unparseable version specified")
    except Exception:
        raise ValueError("Unable to parse version information") from None
    else:
        return version_test


class RegistrationForm:
    """Player/NPC metadata helper class

        This class organizes player/npc metadata including what facts a
        player is interested in
    """
    def __init__(self, *args, **kwargs):
        self.name = None
        self.description = None
        self.creator = None
        self.version = None
        self.engine_version = None
        self.options = Arguments()
        self.interests = {'facts': set(),
                          'hyps': set()}
        self.facts_consumed = set()
        self.facts_generated = set()
        self.hyps_consumed = set()
        self.hyps_generated = set()
        self.help = None

        for (key, val) in kwargs.items():
            if key == "name":
                self.name = val
            elif key == "description":
                self.description = val
            elif key == "creator":
                self.creator = val
            elif key == "version":
                self.version = _test_version_string(val)
            elif key == "engine_version":
                self.engine_version = _test_version_string(val)
            elif key == "options":
                if not isinstance(val, Arguments):
                    raise TypeError("'options must be of type 'Arguments'")

                self.options = val
            elif key == "interests":
                try:
                    keys = val.keys()
                    if sorted(keys) != ['facts', 'hyps']:
                        raise ValueError("Unexpected keys in interests dict")
                except AttributeError:
                    # Assume it's a set
                    if not isinstance(val, Iterable):
                        raise TypeError("Expected an interable type") from None
                    self.addFactInterests(val)
                else:
                    self.addInterests(val)

            elif key == "help":
                self.help = val
            elif key == "facts_consumed":
                if not isinstance(val, Iterable):
                    raise TypeError("facts_consumed must be list-like type")
                for fc in val:
                    if isFactGroup(fc):
                        fc = '%s (Group)' % (fc)
                    self.facts_consumed.add(fc)
            elif key == "facts_generated":
                if not isinstance(val, Iterable):
                    raise TypeError("facts_generated must be list-like type")
                for fg in val:
                    if isFactGroup(fg):
                        fg = '%s (Group)' % (fg)
                    self.facts_generated.add(fg)
            else:
                raise TypeError('%s is an invalid keyword argument' % (key))

        if self.name is None:
            raise AttributeError("Player must define name")

        if self.description is None:
            raise AttributeError("Player must define a description")

        if self.creator is None:
            raise AttributeError("Player must define a creator")

        if self.version is None:
            raise AttributeError("Player must define a player version")

        if self.engine_version is None:
            raise AttributeError("Player must define supported engine version")

    def addFactInterests(self, interests):
        for interest in resolveFacts(interests):
            self.interests['facts'].add(interest)
            self.facts_consumed.add(interest)

    def addHypInterests(self, interests):
        for interest in resolveFacts(interests):
            self.interests['hyps'].add(interest)
            self.hyps_consumed.add(interest)

    def addInterests(self, interests):
        self.addFactInterests(interests['facts'])
        self.addHypInterests(interests['hyps'])

    @property
    def factInterests(self):
        return self.interests['facts']

    @property
    def hypInterests(self):
        return self.interests['hyps']

    def save(self):
        # TODO FIXME add options?
        data = {'name': self.name,
                'description': self.description,
                'creator': self.creator,
                'version': str(self.version),
                'engine_version': str(self.engine_version),
                'interests': self.interests,
                'help': self.help}
        return data


class ScreenRegistrationForm:
    """Screen metadata helper class

        Provides organization of screen metadata
    """
    def __init__(self, *args, **kwargs):
        self.name = None
        self.version = _test_version_string("0.1")
        self.engine_version = _test_version_string("0.1")
        self.options = Arguments()

        for (key, val) in kwargs.items():
            if key == "name":
                self.name = val
            elif key == "version":
                self.version = _test_version_string(val)
            elif key == "engine_version":
                self.engine_version = _test_version_string(val)
            elif key == "options":
                if not isinstance(val, Arguments):
                    raise TypeError("'options must be of type 'Arguments'")

                self.options = val
            else:
                raise TypeError("%s is an invalid keyword argument" % (key))

        if self.name is None:
            raise AttributeError("Screen must define name")

        if self.version is None:
            raise AttributeError("Screen must define a version")

        if self.engine_version is None:
            raise AttributeError("Screen must define supported engine version")


class BackStoryRegistrationForm:
    """BackStory metadata helper class

        This class organizes backstory metadata including what type of facts
        it can work with
    """
    def __init__(self, *args, **kwargs):
        self.name = None
        self.description = None
        self.creator = None
        self.version = None
        self.engine_version = None
        self.category = None
        self.default_weight = 1
        self._interests = set()
        self.interests
        self.help = None
        self.options = Arguments()

        for (key, val) in kwargs.items():
            if key == "name":
                self.name = val
            elif key == "description":
                self.description = val
            elif key == "creator":
                self.creator = val
            elif key == "version":
                self.version = _test_version_string(val)
            elif key == "engine_version":
                self.engine_version = _test_version_string(val)
            elif key == "options":
                if not isinstance(val, Arguments):
                    raise TypeError("'options must be of type 'Arguments'")

                self.options = val
            elif key == "interests":
                # Assume it's a set
                if not isinstance(val, Iterable):
                    raise TypeError("Expected an interable type") from None
                self.addFactInterests(val)
            elif key == "category":
                if not isinstance(val, str):
                    raise TypeError("Expected a str type") from None
                self.category = val
            elif key == "default_weight":
                if not isinstance(val, int):
                    raise TypeError("Expected an int type") from None
                self.default_weight = val
            elif key == "help":
                self.help = val
            else:
                raise TypeError('%s is an invalid keyword argument' % (key))

        if self.name is None:
            raise AttributeError("BackStory must define name")

        if self.description is None:
            raise AttributeError("BackStory must define a description")

        if self.creator is None:
            raise AttributeError("BackStory must define a creator")

        if self.version is None:
            raise AttributeError("BackStory must define a backstory version")

        if self.category is None:
            raise AttributeError("BackStory must define a category")

        if self.engine_version is None:
            raise AttributeError(
                "BackStory must define supported engine version")

    def addFactInterests(self, interests):
        for interest in interests:
            self._interests.add(interest)

    @property
    def interests(self):
        return self._interests

    def save(self):
        data = {'name': self.name,
                'description': self.description,
                'creator': self.creator,
                'version': str(self.version),
                'engine_version': str(self.engine_version),
                'interests': self.interests,
                'help': self.help}
        return data
