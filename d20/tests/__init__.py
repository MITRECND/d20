import sys
import io
import contextlib


@contextlib.contextmanager
def wrapOut():
    oout = sys.stdout
    oerr = sys.stderr
    nout = io.StringIO()
    nerr = io.StringIO()

    try:
        sys.stdout = nout
        sys.stderr = nerr
        yield (sys.stdout, sys.stderr)
    finally:
        sys.stdout = oout
        sys.stderr = oerr
