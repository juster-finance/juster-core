""" Test that when pause is setted it is impossible to create new events """

from os.path import dirname
from os.path import join

from pytezos import MichelsonRuntimeError

from tests.interpret.juster.juster_base import ONE_HOUR
from tests.interpret.juster.juster_base import RUN_TIME
from tests.interpret.juster.juster_base import JusterBaseTestCase

TRIGGER_PAUSE_LAMBDA_FN = '../../../build/lambdas/trigger_pause.tz'


class EventPauseTest(JusterBaseTestCase):
    def test_event_pause(self):

        trigger_pause = open(
            join(dirname(__file__), TRIGGER_PAUSE_LAMBDA_FN)
        ).read()

        self.current_time = RUN_TIME
        self.id = self.storage['nextEventId']
        self.assertFalse(self.storage['config']['isEventCreationPaused'])

        # Creating event with no pause:
        self.new_event(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee,
        )

        # Setting pause:
        self.update_config(trigger_pause, self.manager)

        self.assertTrue(self.storage['config']['isEventCreationPaused'])

        # Creating event with pause is not succeed:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.new_event(
                event_params=self.default_event_params,
                amount=self.measure_start_fee + self.expiration_fee,
            )
        msg = 'Event creation is paused'
        self.assertTrue(msg in str(cm.exception))

        # Unsetting pause:
        self.update_config(trigger_pause, self.manager)

        self.assertFalse(self.storage['config']['isEventCreationPaused'])

        # Creating event with pause is not succeed:
        self.new_event(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee,
        )
