""" EDGECASE 1 test, different zero-cases """

from state_transformation_base import StateTransformationBaseTest, RUN_TIME, ONE_HOUR
from pytezos import MichelsonRuntimeError


class ZeroEdgecasesDeterminedTest(StateTransformationBaseTest):

    def test_zero_edgecases(self):
        self.current_time = RUN_TIME
        self.id = len(self.storage['events'])

        # Creating event, both fees equal to zero:
        self.measure_start_fee = 0
        self.expiration_fee = 0

        self.storage['config'].update({
            'measureStartFee': self.measure_start_fee,
            'expirationFee': self.expiration_fee,
        })

        self.storage = self.check_new_event_succeed(
            event_params=self.default_event_params, amount=0)

        # A provides liquidity with 0 tez, assert failed:
        self.check_provide_liquidity_fails_with(
            participant=self.a,
            amount=0,
            expected_above_eq=1,
            expected_bellow=1,
            msg_contains='Zero liquidity provided')

        # A tries to bet but there are no liquidity, assert failed:
        self.check_bet_fails_with(
            participant=self.a,
            amount=1_000_000,
            bet='aboveEq',
            minimal_win=1_000_000,
            msg_contains="Can't process bet before liquidity added")

        # B provides 10mutez in liquidity with success:
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.b,
            amount=10,
            expected_above_eq=1,
            expected_bellow=1)

        # A provides liquidity with 0 expected aboveEq/bellow, assert failed:
        self.check_provide_liquidity_fails_with(
            participant=self.a,
            amount=1_000_000,
            expected_above_eq=0,
            expected_bellow=1,
            msg_contains='Expected ratio in pool should be more than zero')

        # A tries to adding liquidity with rate that very different from internal rate
        # assert failwith:
        self.check_provide_liquidity_fails_with(
            participant=self.a,
            amount=1_000_000,
            expected_above_eq=10,
            expected_bellow=1,
            msg_contains='Expected ratio very differs from current pool ratio')

        # A provides liquidity with 0 expected aboveEq/bellow (again), assert failed:
        self.check_provide_liquidity_fails_with(
            participant=self.a,
            amount=1_000_000,
            expected_above_eq=1,
            expected_bellow=0,
            msg_contains='Expected ratio in pool should be more than zero')

        # A tries to Bet with winRate a lot more than expected:
        self.check_bet_fails_with(
            participant=self.a,
            amount=1,
            bet='bellow',
            minimal_win=5,
            msg_contains='Wrong minimalWinAmount')

        # In the end: no one bets, starting measure:
        bets_close = self.default_event_params['betsCloseTime']
        period = self.default_event_params['measurePeriod']
        self.current_time = bets_close
        self.storage = self.check_start_measurement_succeed(sender=self.a)

        # Emulating callback:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time,
            'rate': 6_000_000
        }
        self.storage = self.check_start_measurement_callback_succeed(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address)

        # Closing event:
        self.current_time = bets_close + period
        self.storage = self.check_close_succeed(sender=self.a)

        # Emulating calback with price is increased 25%:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time,
            'rate': 7_500_000
        }
        self.storage = self.check_close_callback_succeed(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address)

        # A provides liquidity after event closed is not allowed:
        self.check_provide_liquidity_fails_with(
            participant=self.a,
            amount=10,
            expected_above_eq=1,
            expected_bellow=1,
            msg_contains='Providing Liquidity after betCloseTime is not allowed')

        # B withdraws all:
        self.storage = self.check_withdraw_succeed(self.a, 0)
        self.storage = self.check_withdraw_succeed(self.b, 10)

        # test trying close twice: assert failed:
        self.check_close_callback_fails_with(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address,
            msg_contains="Contract already closed. Can't close contract twice")

        # A tries to Bet after contract is closed and failed:
        self.check_bet_fails_with(
            participant=self.a,
            amount=1,
            bet='bellow',
            minimal_win=5,
            msg_contains='Bets after betCloseTime is not allowed')

        # test trying to call measurement after close is failed:
        self.check_start_measurement_callback_fails_with(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address,
            msg_contains="Measurement period already started")

