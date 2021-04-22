from d20.Actions import registerAction
from d20.Manual.Options import Arguments


@registerAction(
    name="TestAction",
    options=Arguments(
        ("option1", {'type': bool, 'default': True})
    )
)
class TestAction(object):
    def __init__(self):
        pass
