import os
import tempfile
import io
import shutil

from d20.Manual.Logger import logging
from d20.Manual.Exceptions import TemporaryDirectoryError

TEMPORARY_DEFAULT = "/tmp/d20"
LOGGER = logging.getLogger(__name__)


class TemporaryHandler:
    temporary_base = TEMPORARY_DEFAULT

    def __init__(self, temporary=None):
        self.base_exists = False

        if temporary is not None:
            TemporaryHandler.temporary_base = temporary
            self.temporary_base = TemporaryHandler.temporary_base

        self.objects_path = os.path.join(self.temporary_base, 'objects')
        self.players_path = os.path.join(self.temporary_base, 'players')

        if os.path.exists(self.temporary_base):
            if not os.path.isdir(self.temporary_base):
                raise TemporaryDirectoryError(
                    "Path %s already exists but is not a directory"
                    % (self.temporary_base))
            else:
                self.base_exists = True
                LOGGER.warning(
                    "Temporary directory %s already exists"
                    % (self.temporary_base))
        else:
            try:
                os.makedirs(self.temporary_base, exist_ok=True)
            except Exception:
                raise TemporaryDirectoryError(
                    "Unable to create temporary directory %s"
                    % (self.temporary_base))

        # Create objects directory
        try:
            os.makedirs(self.objects_path, exist_ok=True)
        except Exception:
            raise TemporaryDirectoryError(
                ("Unable to create temporary objects "
                    "directory"))

        # Create players directory
        try:
            os.makedirs(self.players_path, exist_ok=True)
        except Exception:
            raise TemporaryDirectoryError(
                ("Unable to create temporary players "
                    "directory"))

    def cleanup(self):
        # Delete objects directory
        try:
            if (os.path.exists(self.objects_path)
                    and os.path.isdir(self.objects_path)):
                shutil.rmtree(self.objects_path)
        except Exception:
            raise TemporaryDirectoryError(
                "Unable to delete temporary directory %s"
                % (self.objects_path))

        # Delete players directory
        try:
            if (os.path.exists(self.players_path)
                    and os.path.isdir(self.players_path)):
                shutil.rmtree(self.players_path)
        except Exception:
            raise TemporaryDirectoryError(
                "Unable to delete temporary directory %s"
                % (self.players_path))

        if not self.base_exists:
            try:
                if (os.path.exists(self.temporary_base)
                        and os.path.isdir(self.temporary_base)):
                    shutil.rmtree(self.temporary_base)
            except Exception:
                raise TemporaryDirectoryError(
                    "Unable to delete temporary directory %s"
                    % (self.temporary_base))

    @staticmethod
    def genPath(*args):
        return os.path.join(TemporaryHandler.temporary_base, *args)


class TemporaryObjectOnDisk:
    """Object on disk management class

        This class provides the cability of writing objects to disk for
        any utilities that require such access. This provides a unified
        consistent location of the files to prevent duplication of effort
        and requiring individual players managing it themselves
    """
    def __init__(self, id, data, **kwargs):
        self.base = TemporaryHandler.genPath('objects')
        (handle, self._path) = \
            tempfile.mkstemp(prefix='object-%d.' % (id), dir=self.base)

        os.close(handle)

        with open(self._path, 'wb') as f:
            if isinstance(data, str):
                wdata = bytes(data, 'utf-8')
            else:
                wdata = data
            f.write(wdata)

    @property
    def path(self):
        return self._path


class TemporaryObjectStream:
    """Object stream management class

        This class returns an instance of io.BytesIO of the object
    """
    def __init__(self, id, data, **kwargs):
        self.data = data
        self.id = id

    @property
    def stream(self):
        return io.BytesIO(self.data)


class PlayerDirectoryHandler:
    """Directory handler for players

        This class provides an abstraction of directory setups for players
        so they don't have to guess or set it up themselves
    """
    def __init__(self, id, isPlayer, **kwargs):
        self.id = id
        self.isPlayer = isPlayer
        player = 'p' if isPlayer else 'n'
        self.base = TemporaryHandler.genPath('players', '%s-%d' % (player, id))
        self._myDir = None

        # Create players directory
        try:
            os.mkdir(self.base)
        except FileExistsError:
            pass
        except Exception:
            raise TemporaryDirectoryError(
                ("Unable to create temporary player "
                 "directory"))

    @property
    def myDir(self):
        if self._myDir is None:
            p = os.path.join(self.base, 'tmp')
            try:
                os.mkdir(p)
            except FileExistsError:
                pass
            except Exception:
                raise TemporaryDirectoryError(
                    ("Unable to create temporary player "
                     "directory"))

            self._myDir = p

        return self._myDir

    def tempdir(self):
        newdir = tempfile.mkdtemp(dir=self.base)
        return newdir
