from typing import Union

import hashlib
import ssdeep

from d20.Manual.BattleMap import FileObject
from d20.Manual.Templates import (NPCTemplate,
                                  registerNPC)
from d20.Manual.Facts import (MD5HashFact, SHA1HashFact,  # type: ignore
                              SHA256HashFact, SSDeepHashFact,  # type: ignore
                              Fact)


# Process basic information to initially populate fact table
# Compute Hashes

@registerNPC(
    name="HashNPC",
    description=("This NPC simply hashes the files and adds"
                 "the values to the fact table"),
    creator="Murad Khan",
    version="0.1",
    engine_version="0.1"
)
class HashNPC(NPCTemplate):
    def __init__(self, **kwargs: str) -> None:
        super().__init__(**kwargs)

    def handleData(self, **kwargs: FileObject) -> None:
        if 'data' not in kwargs:
            raise RuntimeError("Expected 'data' in arguments")

        dataObj: FileObject = kwargs['data']
        data: Union[bytes, bytearray, memoryview] = dataObj.data
        hashFact: Fact = MD5HashFact(value=hashlib.md5(data).hexdigest(),
                                     parentObjects=[dataObj.id])
        self.console.addFact(hashFact)
        hashFact = SHA1HashFact(value=hashlib.sha1(data).hexdigest(),
                                parentObjects=[dataObj.id])
        self.console.addFact(hashFact)
        hashFact = SHA256HashFact(value=hashlib.sha256(data).hexdigest(),
                                  parentObjects=[dataObj.id])
        self.console.addFact(hashFact)
        hashFact = SSDeepHashFact(value=ssdeep.hash(data),
                                  parentObjects=[dataObj.id])
        self.console.addFact(hashFact)
