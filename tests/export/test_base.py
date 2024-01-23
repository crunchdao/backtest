import datetime
import unittest
import unittest.mock

from bktest.export import Exporter, ExporterCollection


class ExporterCollectionTest(unittest.TestCase):

    def test_init(self):
        self.assertIsNotNone(ExporterCollection(None).elements)

    def test_fire_initialize(self):
        noop = Exporter()
        noop.initialize = unittest.mock.MagicMock()

        ExporterCollection([noop]).fire_initialize()

        noop.initialize.assert_called_once()

    def test_fire_skip(self):
        noop = Exporter()
        noop.on_skip = unittest.mock.MagicMock()

        date = datetime.date.today()
        reason = "holiday"
        ordered = True

        ExporterCollection([noop]).fire_skip(date, reason, ordered)

        noop.on_skip.assert_called_once_with(date, reason, ordered)

    def test_fire_finalize(self):
        noop = Exporter()
        noop.finalize = unittest.mock.MagicMock()

        ExporterCollection([noop]).fire_finalize()

        noop.finalize.assert_called_once()
