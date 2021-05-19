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
        # TODO: already error, fix either test either code

        # A provides liquidity with 0 tez, assert failed:
        self.check_provide_liquidity_fails_with(
            participant=self.a,
            amount=0,
            expected_for=1,
            expected_against=1,
            msg_contains='Zero liquidity provided')

        """ TODO:
        - A tries to bet but there are no liquidity, so assert MichelsonError
        - B provides liquidity
        - A provides liquidity with 0 tez, assert failed again
        - A tries to adding liquidity with rate that very different from internal rate
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