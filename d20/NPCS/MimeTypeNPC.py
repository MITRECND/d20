from d20.Manual.Templates import (NPCTemplate,
                                  registerNPC)
from d20.Manual.Facts import MimeTypeFact  # type: ignore

import magic


# Process basic information to initially populate fact table
@registerNPC(
    name="MimeTypeNPC",
    description=("This NPC provides the mimetype of an object."),
    creator="Mike Goffin",
    version="0.1",
    engine_version="0.1"
)
class MimeTypeNPC(NPCTemplate):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def handleData(self, **kwargs):
        if 'data' not in kwargs:
            raise RuntimeError("Expected 'data' in arguments")

        dataObj = kwargs['data']
        data = dataObj.data
        try:
            mimetype = magic.from_buffer(data, mime=True)
        except Exception:
            mimetype = None
        if mimetype:
            mimetype = mimetype.split(';')[0]
        else:
            mimetype = None
        try:
            filetype = magic.from_buffer(data)
        except Exception:
            filetype = 'Unknown'
        mimetypeFact = MimeTypeFact(
            mimetype=mimetype,
            filetype=filetype,
            parentObjects=[dataObj.id]
        )
        self.console.addFact(mimetypeFact)
