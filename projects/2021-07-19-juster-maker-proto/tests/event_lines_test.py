from unittest import TestCase
import os

from event_lines import EventLines
from unittest.mock import patch
import tests.config as config


TEST_FILENAME = 'tests/__event_lines.json'


class EventLinesTest(TestCase):

    def test_should_be_able_save_and_load_without_changes(self):

        source_event_lines = EventLines(config)
        source_event_lines.generate_new()
        source_event_lines.save(TEST_FILENAME)

        loaded_event_lines = EventLines.load(TEST_FILENAME)

        source_event_list = source_event_lines.get()
        loaded_event_list = loaded_event_lines.get()

        for source, loaded in zip(source_event_list, loaded_event_list):
            self.assertDictEqual(source, loaded)


    def tearDown(self):
        os.remove(TEST_FILENAME)

