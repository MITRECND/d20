import unittest
import os
import io
import tempfile

from d20.Manual.Temporary import (TemporaryHandler,
                                  TemporaryObjectStream,
                                  TemporaryObjectOnDisk,
                                  PlayerDirectoryHandler)
from d20.Manual.Exceptions import TemporaryDirectoryError


class TestTemporary(unittest.TestCase):
    TEMP_PATH = '/tmp/d20test'

    @classmethod
    def setUpClass(cls):
        cls.tempHandler = TemporaryHandler(cls.TEMP_PATH)

    def setUp(self):
        self.data = b'foo'

    def testObjectStream(self):
        ts = TemporaryObjectStream(1, self.data)
        self.assertTrue(isinstance(ts.stream, io.BytesIO))
        self.assertEqual(ts.stream.getvalue(), self.data)

    def testObjectFile(self):
        ond = TemporaryObjectOnDisk(1, self.data)
        path = ond.path
        self.assertTrue(os.path.isfile(path))

        with open(path, 'rb') as f:
            data = f.read()

        self.assertEqual(data, self.data)

    def testPlayerDirectory(self):
        pd = PlayerDirectoryHandler(1, True)
        md = pd.myDir

        self.assertEqual(md,
                         os.path.join(self.TEMP_PATH, 'players', 'p-1', 'tmp'))
        self.assertTrue(os.path.isdir(md))

    @classmethod
    def tearDownClass(cls):
        cls.tempHandler.cleanup()


class TestTemporaryErrors(unittest.TestCase):
    def testNonDirectory(self):
        tf = tempfile.NamedTemporaryFile(delete=False)
        tf.close()
        with self.assertRaises(TemporaryDirectoryError):
            TemporaryHandler(tf.name)
