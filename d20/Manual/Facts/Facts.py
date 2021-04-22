from d20.Manual.Facts import (Fact,
                              registerFact)

from d20.Manual.Facts.Fields import StringField


@registerFact('hash')
class MD5HashFact(Fact):
    _type_ = 'md5'
    value = StringField()


@registerFact('hash')
class SHA1HashFact(Fact):
    _type_ = 'sha1'
    value = StringField()


@registerFact('hash')
class SHA256HashFact(Fact):
    _type_ = 'sha256'
    value = StringField()


@registerFact('hash')
class SSDeepHashFact(Fact):
    _type_ = 'ssdeep'
    value = StringField()


@registerFact()
class MimeTypeFact(Fact):
    _type_ = 'mimetype'
    mimetype = StringField()
    filetype = StringField()
