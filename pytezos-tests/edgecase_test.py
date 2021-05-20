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

        self.storage['newEventConfig'].update({
            'measureStartFee': self.measure_start_fee,
            'expirationFee': self.expiration_fee,
        })

        self.storage = self.check_new_event_succeed(
            event_params=self.default_event_params, amount=0)

        # A provides liquidity with 0 tez, assert failed:
        self.check_provide_liquidity_fails_with(
            participant=self.a,
            amount=0,
            expected_for=1,
            expected_against=1,
            msg_contains='Zero liquidity provided')

        # A tries to bet but there are no liquidity, assert failed:
        self.check_bet_fails_with(
            participant=self.a,
            amount=1_000_000,
            bet='for',
            minimal_win=1_000_000,
            msg_contains="Can't process bet before liquidity added")

        # B provides 10mutez in liquidity with success:
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.b,
            amount=10,
            expected_for=1,
            expected_against=1)

        # A provides liquidity with 0 expected for/against, assert failed:
        self.check_provide_liquidity_fails_with(
            participant=self.a,
            amount=1_000_000,
            expected_for=0,
            expected_against=1,
            msg_contains='Expected ratio in pool should be more than zero')

        # A tries to adding liquidity with rate that very different from internal rate
        # assert failwith:
        self.check_provide_liquidity_fails_with(
            participant=self.a,
            amount=1_000_000,
            expected_for=10,
            expected_against=1,
            msg_contains='Expected ratio very differs from current pool ratio')

        """ TODO:
        - A tries to adding liquidity one of the rates equal to 0 (betFor or betAgainst)
            [or maybe with ratio > maxRatio]

        - A tries to Bet with winRate a lot more than expected (assert MichelsonError raises)

        - in the end: no one bets, measure
            - assert that len operations in callback is 0 (because fee is zero)

        - TODO: test that adding liquidity after bets time is not allowed

        - close, B withdraws all
            - assert that len operations in closeCallback is 0 (because fee is zero)
            TODO: check contract balance is 0
            TODO: check B withdraws all the sum invested

        - TODO: test trying close twice: assert failed
        - TODO: test trying to bet after close is failed
        - TODO: test trying to call measurement after close is failed
        """