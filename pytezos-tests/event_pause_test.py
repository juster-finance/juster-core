""" Test that when pause is setted it is impossible to create new events """

from state_transformation_base import StateTransformationBaseTest, RUN_TIME, ONE_HOUR
from pytezos import MichelsonRuntimeError
from os.path import join, dirname


TRIGGER_PAUSE_LAMBDA_FN = '../build/tz/lambda_trigger_pause.tz'


class EventPauseDeterminedTest(StateTransformationBaseTest):

    def test_event_pause(self):

        trigger_pause = open(join(dirname(__file__), TRIGGER_PAUSE_LAMBDA_FN)).read()

        self.current_time = RUN_TIME
        self.id = self.storage['lastEventId']
        self.assertFalse(self.storage['config']['isEventCreationPaused'])

        # Creating event with no pause:
        self.check_new_event_succeed(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee)

        # Setting pause:
        self.storage = self.check_update_config_succeed(
            trigger_pause, self.manager)

        self.assertTrue(self.storage['config']['isEventCreationPaused'])

        # Creating event with pause is not succeed:
        self.check_new_event_fails_with(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee,
            msg_contains="Event creation is paused")

        # Unsetting pause:
        self.storage = self.check_update_config_succeed(
            trigger_pause, self.manager)

        self.assertFalse(self.storage['config']['isEventCreationPaused'])

        # Creating event with pause is not succeed:
        self.check_new_event_succeed(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee)

