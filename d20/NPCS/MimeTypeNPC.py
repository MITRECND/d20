from typing import Union, Optional

import magic

from d20.Manual.BattleMap import FileObject
from d20.Manual.Templates import (NPCTemplate,
                                  registerNPC)
from d20.Manual.Facts import (MimeTypeFact,  # type: ignore
                              Fact)


# Process basic information to initially populate fact table
@registerNPC(
    name="MimeTypeNPC",
    description=("This NPC provides the mimetype of an object."),
    creator="Mike Goffin",
    version="0.1",
    engine_version="0.1"
)
class MimeTypeNPC(NPCTemplate):
    def __init__(self, **kwargs: str) -> None:
        super().__init__(**kwargs)

    def handleData(self, **kwargs: FileObject) -> None:
        if 'data' not in kwargs:
            raise RuntimeError("Expected 'data' in arguments")

        dataObj: FileObject = kwargs['data']
        data: Union[bytes, bytearray, memoryview] = dataObj.data
        try:
            mimetype: Optional[str] = magic.from_buffer(data, mime=True)
        except Exception:
            mimetype = None
        if mimetype:
            mimetype = mimetype.split(';')[0]
        else:
            mimetype = None
        try:
            filetype: Optional[str] = magic.from_buffer(data)
        except Exception:
            filetype = 'Unknown'
        mimetypeFact: Fact = MimeTypeFact(
            mimetype=mimetype,
            filetype=filetype,
            parentObjects=[dataObj.id]
        )
        self.console.addFact(mimetypeFact)
