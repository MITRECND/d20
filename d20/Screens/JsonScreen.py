from d20.Manual.Options import Arguments
from d20.Manual.Templates import (ScreenTemplate,
                                  registerScreen)
from d20.Manual.Logger import logging

import json
import binascii

LOGGER = logging.getLogger(__name__)


class BytesEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            try:
                outstring = str(obj, 'utf-8')
                if not outstring.isprintable():
                    raise UnicodeError(
                        'utf-8',
                        "non-printable characters in sequence",
                        obj)
            except UnicodeError:
                outstring = "0x%s" % (binascii.hexlify(obj).decode('utf8'))
            return outstring

        return json.JSONEncoder.default(self, obj)


@registerScreen(
    name="json",
    options=Arguments(
        ("exclude", {'type': list}),
        ("exclude_objects", {'type': bool, 'default': False}),
        ("convert_bytes", {'type': bool, 'default': True}),
        ("include_core_facts", {'type': bool, 'default': False}),
    )
)
class JSONScreen(ScreenTemplate):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.exclusions = self.options.get("exclude", [])
        # Parent object inits
        # facts - dictionary of game facts
        # hyps - dictionary of game hypotheses
        # objects - list of objects
        # options - any options passed from config

    def filter(self):
        gameData = {'facts': dict(),
                    'hyps': dict()}

        if not self.options.get('exclude_objects', False):
            gameData['objects'] = list()
            for obj in self.objects:
                objdata = obj._coreInfo
                objdata.update(self.formatData(obj._creationInfo))
                gameData['objects'].append(objdata)

        for (_type, column) in self.facts.items():
            if any(e in _type for e in self.exclusions):
                continue
            gameData['facts'][_type] = list()
            for fact in column:
                fact_info = fact._nonCoreFacts
                if self.options.get('include_core_facts', False):
                    fact_info.update(self.formatData(fact._coreFacts))
                gameData['facts'][_type].append(fact_info)

        for (_type, column) in self.hyps.items():
            if any(e in _type for e in self.exclusions):
                continue
            gameData['hyps'][_type] = list()
            for hyp in column:
                hyp_info = hyp._nonCoreFacts
                if self.options.get('include_core_facts', False):
                    hyp_info.update(self.formatData(hyp._coreFacts))
                gameData['hyps'][_type].append(hyp_info)

        return gameData

    def present(self):
        cls = BytesEncoder
        if not self.options.get('convert_bytes', True):
            cls = None

        try:
            return json.dumps(self.filter(), cls=cls)
        except Exception:
            LOGGER.exception("Error attempting to JSON serialize game data")

    def formatData(self, data):
        return {key.strip('_'): value for (key, value) in data.items()}
