from d20.Manual.Templates import (ScreenTemplate,
                                  registerScreen)
from d20.Manual.Logger import logging

import yaml
import binascii
from collections import OrderedDict

LOGGER = logging.getLogger(__name__)


class CustomDumper(yaml.Dumper):
    @staticmethod
    def bytes_representer(dumper, data):
        try:
            outstring = str(data, 'utf-8')
            if not outstring.isprintable():
                raise UnicodeError(
                    'utf-8',
                    "non-printable characters in sequence",
                    data)
        except UnicodeError:
            outstring = "0x%s" % (binascii.hexlify(data).decode('utf8'))
        return dumper.represent_str(outstring)

    @staticmethod
    def ordered_dict_representer(dumper, data):
        out_list = list()
        for (key, value) in data.items():
            out_list.append({key: value})
        return dumper.represent_list(out_list)


@registerScreen(
    name="yaml"
)
class YAMLScreen(ScreenTemplate):
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
        CustomDumper.add_representer(bytes, CustomDumper.bytes_representer)
        CustomDumper.add_representer(
            OrderedDict, CustomDumper.ordered_dict_representer)

        try:
            return yaml.dump(self.filter(), Dumper=CustomDumper)
        except Exception:
            LOGGER.exception("Error attempting to yaml serialize game data")

    def formatData(self, data):
        return {key.strip('_'): value for (key, value) in data.items()}
