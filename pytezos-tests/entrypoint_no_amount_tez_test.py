""" Checking that some of the entrypoints disallow including tez """

from state_transformation_base import StateTransformationBaseTest, RUN_TIME, ONE_HOUR
from pytezos import MichelsonRuntimeError


class ForceMajeureDeterminedTest(StateTransformationBaseTest):

    def test_entrypoints_no_amount(self):

        self.current_time = RUN_TIME
        self.id = len(self.storage['events'])

        # Creating default event:
        self.storage = self.check_new_event_succeed(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee)

        bets_close_time = self.default_event_params['betsCloseTime']
        max_lag = self.default_config['maxAllowedMeasureLag']
        measure_period = self.default_event_params['measurePeriod']

        self.storage = self.check_provide_liquidity_succeed(
            participant=self.a,
            amount=10,
            expected_above_eq=1,
            expected_bellow=1)

        self.current_time = bets_close_time + max_lag // 2
        self.storage = self.check_start_measurement_succeed(sender=self.a)

        ERROR_MSG = 'Including tez using this entrypoint call is not allowed'

        # Running measurement with amount > 0 shold not be allowed:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time - int(0.5*ONE_HOUR),
            'rate': 8_000_000
        }

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.contract.startMeasurement(self.id).with_amount(10).interpret(
                storage=self.storage, sender=self.a, now=self.current_time)
        self.assertTrue(ERROR_MSG in str(cm.exception))

        with self.assertRaises(MichelsonRuntimeError) as cm:
            call = self.contract.startMeasurementCallback(callback_values)
            call.with_amount(10).interpret(
                storage=self.storage,
                sender=self.oracle_address,
                now=self.current_time)
        self.assertTrue(ERROR_MSG in str(cm.exception))


        # Triggering force-majeure with amount > 0 should not be allowed:
        self.current_time = bets_close_time + measure_period + max_lag * 2

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.contract.triggerForceMajeure(self.id).with_amount(10).interpret(
                storage=self.storage, sender=self.a, now=self.current_time)

            self.contract.close(self.id).with_amount(10).interpret(
                storage=self.storage, sender=self.a, now=self.current_time)
        self.assertTrue(ERROR_MSG in str(cm.exception))


        # Running close with amount > 0 shold not be allowed:

        callback_values.update({'lastUpdate': self.current_time - 1*ONE_HOUR})
        self.storage['events'][self.id]['isMeasurementStarted'] = True

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.contract.close(self.id).with_amount(10).interpret(
                storage=self.storage, sender=self.a, now=self.current_time)
        self.assertTrue(ERROR_MSG in str(cm.exception))

        with self.assertRaises(MichelsonRuntimeError) as cm:
            call = self.contract.closeCallback(callback_values)
            call.with_amount(10).interpret(
                storage=self.storage,
                sender=self.oracle_address,
                now=self.current_time)
        self.assertTrue(ERROR_MSG in str(cm.exception))


        # Withdrawing with amount > 0 should not be allowed:
        self.storage['events'][self.id]['isClosed'] = True

        with self.assertRaises(MichelsonRuntimeError) as cm:
            params = {'eventId': self.id, 'participantAddress': self.a}
            call = self.contract.withdraw(params)
            call.with_amount(10).interpret(
                storage=self.storage,
                sender=self.a,
                now=self.current_time)
        self.assertTrue(ERROR_MSG in str(cm.exception))

        # Set delegate with amount > 0 should not be allowed too:
        random_delegate_from_twitter = 'tz3e7LbZvUtoXhpUD1yb6wuFodZpfYRb9nWJ'
        with self.assertRaises(MichelsonRuntimeError) as cm:
            call = self.contract.setDelegate(random_delegate_from_twitter)
            call.with_amount(10).interpret(
                storage=self.storage,
                sender=self.a,
                now=self.current_time)
        self.assertTrue(ERROR_MSG in str(cm.exception))
