""" This is simple determined test that interacts with the contract in different
    ways using pytezos intepret method. All interactions splitted into separate blocks.
    After each contract call, new state saved into self.storage and then used in another
    blocks, so block execution order is important. Actually this is one big test.

    Event: XTZ-USD dynamics would be > 1 in 12 hours after betting period of 24 hours.
    Liquidity pool 1%

    Three participants: a, b and c making next interactions:
        (1) participant A adds initial liquidity at the beginning (0 hours from start): 100k with ratio 1:1
        (2) participant B bets For with 50k (1 hour from start)
            rate before bet 50:50
            rate at bet     50:100, if S: win amount +25k*L, if ~S: loose amount -50k
            rate after bet  25:100 == 1:4 (a:f)
        (3) participant A adds more liquidity (12 hours from start): 50k with ratio 4:1 (f:a)
            NOTE: A whould probably have Ev =/= 0 after this operation
        (4) participant D adds more liquidity (12 hours from start): 450k with ratio 4:1 (f:a)
            NOTE: A whould probably have Ev =/= 0 after this operation
        (5) participant D bets Against with 125k (14 hours from start)
            rate before bet 500:125
            rate at bet     500:250 (f:a), if ~S: win amount +250k*L, if S: loose amount 125k
            rate after bet  250:250
        (6) participant C adds more liquidity at the very end (24 hours from start): 100k with ratio 1:1 (f:a)
            NOTE: C whould probably have Ev =/= 0 after this operation
        (7) particiapnt A calls running_measurement 26 hours from the start
        (8) oracle returns that price at the measurement start is 6.0$ per xtz. Oracle measurement time is behind one hour
        (9) participant B cals close_call at 38 hours from the start
        (10) oracle returns that price at the close is 7.5$ per xtz. Oracle measurement time is behind one hour

    Closed dynamics is +25%, betsFor pool is wins
                                      (1)      (2)      (3)      (4)      (5)       (6)
    Total event pool:               100_000 + 25_000 + 50_000 + 450_000 + 125_000 + 100_000 = 850_000
    betForLiquidityPool:             50_000 + 50_000 + 40_000 + 360_000 - 250_000 +  50_000 = 300_000
    betAgainstLiquidityPool:         50_000 - 25_000 + 10_000 +  90_000 + 125_000 +  50_000 = 300_000
            (liquidity rate is not included in the pools)

    if S:
        participant B wins and get 50_000 + 25_000 * 96% = 74_000 (this value should be saved in winning amounts ledger)
        participant D loose his bet 35_000 + provided liquidity 75_000
    if ~S:
        participant B loose his bet 50_000
        participant D wins and get 35_000 + 70_000 * 96% + provided liquidity 75_000 = 177_200

    Total win S  LP profit / loss:        0 - 24_000 +      0 +       0 + 125_000 +       0 = 101_000
    Total win ~S LP profit / loss:        0 + 50_000 +      0 +       0 - 120_000 +       0 = -70_000
            (liquidity rate is included in profit/loss pools)

    Total liquidity For bonuses:     50_000 +      0 + 20_000 + 180_000 +       0 +       0 = 250_000
    Total liquidity Against bonuses: 50_000 +      0 +  5_000 +  45_000 +       0 +       0 = 100_000
    Total provided Liquidity:       100_000 +      0 + 50_000 + 450_000 +       0 + 100_000 = 325_000

    Selected liquidity pool to distribute profits: liquidity Against (because For wins)

    liquidity For shares:
        A: 55_000 / 100_000 = 55%
        D: 45_000 / 100_000 = 45% 
        C:      0 / 100_000 = 0%

    LP withdraw = Profit/Loss * LP_share + ProvidedL
    A withdraws: 101_000 * 0.55 + 100_000 + 50_000 = 205_550
    B withdraws: 50_000 + 24_000 = 74_000
    C withdraws: 100_000
    D withdraws: 101_000 * 0.45 + 450_000 = 495_450

    Changes:
        A: 205_550 / 150_000 = 1.370
        B:  74_000 /  50_000 = 1.480
        C: 100_000 / 100_000 = 1.000
        D: 495_450 / 575_000 = 0.862
"""

from state_transformation_base import StateTransformationBaseTest, RUN_TIME, ONE_HOUR
from pytezos import MichelsonRuntimeError


class DeterminedTest(StateTransformationBaseTest):

    def _assert_wrong_ratio_bet(self):
        """ Checking that transaction is fails if amount is not equal to sum
            of the bets / provided liquidity
        """

        # ratio at the call moment 1:1, trying to make a bet with 10:1 ratio:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            transaction = self.contract.bet(
                eventId=self.id, bet='for', minimalWinAmount=1_000_000).with_amount(100_000)
            res = transaction.interpret(
                storage=self.storage, sender=self.a, now=RUN_TIME)

        self.assertTrue('Wrong minimalWinAmount' in str(cm.exception))


    def _assert_closing_before_measurement(self):
        """ Testing that closing before measurement fails """

        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': RUN_TIME + 24*ONE_HOUR,
            'rate': 6_000_000
        }

        result = self.contract.close(self.id).interpret(
            storage=self.storage, sender=self.a, now=RUN_TIME + 24*ONE_HOUR)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.closeCallback(callback_values).interpret(
                storage=result.storage, sender=self.oracle_address, now=RUN_TIME + 24*ONE_HOUR)

        self.assertTrue("Can't close contract before measurement period started" in str(cm.exception))


    def _assert_wrong_currency_pair_return_from_oracle(self):
        """ Testing that wrong currency_pair returned from oracle during measurement is fails """

        callback_values = {
            'currencyPair': 'WRONG_PAIR',
            'lastUpdate': RUN_TIME + 26*ONE_HOUR,
            'rate': 6_000_000
        }

        result = self.contract.startMeasurement(self.id).interpret(
            storage=self.storage, sender=self.a, now=RUN_TIME + 24*ONE_HOUR)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.startMeasurementCallback(callback_values).interpret(
                storage=result.storage, sender=self.oracle_address, now=RUN_TIME + 26*ONE_HOUR)

        self.assertTrue("Unexpected currency pair" in str(cm.exception))


    def _assert_measurement_during_bets_time(self):
        """ Test that startMeasurement call during bets period is falls """

        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': RUN_TIME + 12*ONE_HOUR,
            'rate': 6_000_000
        }

        result = self.contract.startMeasurement(self.id).interpret(
            storage=self.storage, sender=self.a, now=RUN_TIME + 24*ONE_HOUR)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.startMeasurementCallback(callback_values).interpret(
                storage=result.storage, sender=self.oracle_address, now=RUN_TIME + 12*ONE_HOUR)

        self.assertTrue("Can't start measurement untill betsCloseTime" in str(cm.exception))


    def _assert_callback_from_unknown_address(self):
        """ Assert that callback from unknown address is failed """

        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': RUN_TIME + 26*ONE_HOUR,
            'rate': 6_000_000
        }

        result = self.contract.startMeasurement(self.id).interpret(
            storage=self.storage, sender=self.a, now=RUN_TIME + 24*ONE_HOUR)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.startMeasurementCallback(callback_values).interpret(
                storage=result.storage, sender=self.c, now=RUN_TIME + 12*ONE_HOUR)

        self.assertTrue('Unknown sender' in str(cm.exception))


    def _assert_betting_in_measurement_period(self):
        """ Test that betting during measurement period is fails """

        with self.assertRaises(MichelsonRuntimeError) as cm:
            transaction = self.contract.bet(
                eventId=self.id, bet='against', minimalWinAmount=100_000).with_amount(100_000)

            res = transaction.interpret(
                storage=self.storage, sender=self.a, now=RUN_TIME + 28*ONE_HOUR)

        self.assertTrue('Bets after betCloseTime is not allowed' in str(cm.exception))


    def _assert_double_measurement(self):
        """ Test that calling measurement after it was called is fails """

        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': RUN_TIME + 30*ONE_HOUR,
            'rate': 7_000_000
        }

        result = self.contract.startMeasurement(self.id).interpret(
            storage=self.storage, sender=self.a, now=RUN_TIME + 24*ONE_HOUR)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.startMeasurementCallback(callback_values).interpret(
                storage=result.storage, sender=self.oracle_address, now=RUN_TIME + 30*ONE_HOUR)

        self.assertTrue('Measurement period already started' in str(cm.exception))


    def _assert_withdraw_before_close(self):
        """ Test that withdraw before close raises error """

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.withdraw(self.id).interpret(
                storage=self.storage, sender=self.a, now=RUN_TIME + 30*ONE_HOUR)

        self.assertTrue('Withdraw is not allowed until contract is closed' in str(cm.exception))


    def test_with_three_participants(self):
        """ Test for 3 participants """

        self.current_time = RUN_TIME
        self.id = len(self.storage['events'])

        # Creating event:
        amount = self.measure_start_fee + self.expiration_fee
        self.storage = self.check_event_successfully_created(
            event_params=self.default_event_params, amount=amount)

        # TODO: create_evet_with_conflict_fees
        # TODO: create_more_events()

        # Participant A: adding liquidity 50/50 just at start:
        self.storage = self.check_participant_successfully_adds_more_liquidity(
            participant=self.a, amount=100_000, expected_for=1, expected_against=1)

        self._assert_wrong_ratio_bet()

        # Participant B: bets for 50_000 after 1 hour:
        self.current_time = RUN_TIME + ONE_HOUR
        self.storage = self.check_participant_successfully_bets(
            participant=self.b, amount=50_000, bet='for', minimal_win=50_000)

        # Participant A: adding more liquidity after 12 hours (1/2 of the bets period):
        self.current_time = RUN_TIME + 12*ONE_HOUR
        self.storage = self.check_participant_successfully_adds_more_liquidity(
            participant=self.a, amount=50_000, expected_for=2, expected_against=1)

        # Participant C: adding more liquidity at the very end:
        self.current_time = RUN_TIME + 24*ONE_HOUR
        self.storage = self.check_participant_successfully_adds_more_liquidity(
            participant=self.c, amount=100_000, expected_for=1, expected_against=1)

        self._assert_closing_before_measurement()
        self._assert_wrong_currency_pair_return_from_oracle()
        self._assert_measurement_during_bets_time()
        self._assert_callback_from_unknown_address()

        # Running measurement:
        self.current_time = RUN_TIME + 26*ONE_HOUR
        self.storage = self.check_measurement_start_succesfully_runned(sender=self.a)

        # Emulating callback:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time - 1*ONE_HOUR,
            'rate': 6_000_000
        }
        self.storage = self.check_measurement_start_callback_succesfully_executed(
            callback_values=callback_values, source=self.a)

        self._assert_betting_in_measurement_period()
        self._assert_double_measurement()
        self._assert_withdraw_before_close()

        # Closing event:
        self.current_time = RUN_TIME + 38*ONE_HOUR
        self.storage = self.check_close_succesfully_runned(sender=self.b)

        # Emulating calback with price is increased 25%:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time - 1*ONE_HOUR,
            'rate': 7_500_000
        }
        self.storage = self.check_close_callback_succesfully_executed(
            callback_values=callback_values, source=self.b)

        # Withdrawals:
        self.current_time = RUN_TIME + 64*ONE_HOUR
        self.storage = self.check_participant_succesfully_withdraws(self.a, 126_000)
        self.storage = self.check_participant_succesfully_withdraws(self.b, 74_000)
        self.storage = self.check_participant_succesfully_withdraws(self.c, 100_000)


    def test_with_four_participants(self):
        """ Test for 4 participants """

        self.current_time = RUN_TIME
        self.id = len(self.storage['events'])

        # Creating event:
        amount = self.measure_start_fee + self.expiration_fee
        self.storage = self.check_event_successfully_created(
            event_params=self.default_event_params, amount=amount)

        # Participant A: adding liquidity 50/50 just at start:
        self.storage = self.check_participant_successfully_adds_more_liquidity(
            participant=self.a, amount=100_000, expected_for=1, expected_against=1)

        # Participant B: bets for 50_000 after 1 hour:
        self.current_time = RUN_TIME + ONE_HOUR
        self.storage = self.check_participant_successfully_bets(
            participant=self.b, amount=50_000, bet='for', minimal_win=50_000)

        # Participant A: adding more liquidity after 12 hours (1/2 of the bets period):
        self.current_time = RUN_TIME + 12*ONE_HOUR
        self.storage = self.check_participant_successfully_adds_more_liquidity(
            participant=self.a, amount=50_000, expected_for=2, expected_against=1)

        # Participant D: adding more liquidity after 12 hours:
        self.storage = self.check_participant_successfully_adds_more_liquidity(
            participant=self.d, amount=450_000, expected_for=4, expected_against=1)

        # Participant D: bets against 125_000 after 12 hours:
        self.storage = self.check_participant_successfully_bets(
            participant=self.d, amount=125_000, bet='against', minimal_win=125_000)

        # Participant C: adding more liquidity at the very end:
        self.current_time = RUN_TIME + 24*ONE_HOUR
        self.storage = self.check_participant_successfully_adds_more_liquidity(
            participant=self.c, amount=100_000, expected_for=1, expected_against=1)

        # Running measurement:
        self.current_time = RUN_TIME + 26*ONE_HOUR
        self.storage = self.check_measurement_start_succesfully_runned(sender=self.a)

        # Emulating callback:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time - 1*ONE_HOUR,
            'rate': 6_000_000
        }
        self.storage = self.check_measurement_start_callback_succesfully_executed(
            callback_values=callback_values, source=self.a)
            
        # Closing event:
        self.current_time = RUN_TIME + 38*ONE_HOUR
        self.storage = self.check_close_succesfully_runned(sender=self.b)

        # Emulating calback with price is increased 25%:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time - 1*ONE_HOUR,
            'rate': 7_500_000
        }
        self.storage = self.check_close_callback_succesfully_executed(
            callback_values=callback_values, source=self.b)

        # Withdrawals:
        self.current_time = RUN_TIME + 64*ONE_HOUR
        self.storage = self.check_participant_succesfully_withdraws(self.a, 205_550)
        self.storage = self.check_participant_succesfully_withdraws(self.b, 74_000)
        self.storage = self.check_participant_succesfully_withdraws(self.c, 100_000)
        self.storage = self.check_participant_succesfully_withdraws(self.d, 495_450)


    def _TODO(self):
        pass

        # TODO: make more simple / edge scenarios from this pieces:
        #     - no LP no bets (but try to make bets, should fail)
        #     - one LP no bets at all
        #     - one LP and one bet

        # TODO: make next tests inside some / all scenarios:
        # -- (!) two participants distribute some liquidity (
        #      maybe replace participant A in second liquidity addition
        #      with D and create different scenario?)

        # test trying to close twice?
        # test that it is not possible to bet after close?
        # test that it is not possible to call measurement after close
        #    (btw it is tested in double_measurement)
        # TODO: check that after event no records are left and all cleaned up

        # TODO: make this tests for two - three ids in cycle?
        # TODO: provide liquidity tests:
        # -- (1) adding liquidity with expected rate
        # -- (2) adding liquidity with rate that different from internal rate
        # TODO: test Bet with winRate less than expected (assert MichelsonError raises)
        # TODO: test that adding liquidity after bets time is not allowed
        # TODO: test where one of the participants is LP at the same time
        # TODO: test that LP can withdraw instead of participant after some time
        #    -- test that LP can't withdraw instead of participant before this time
        # TODO: test scenario when LP have profits (current scenario: LP have losses)
        # TODO: test that LP can't withdraw while there are some participants
        # TODO: test that it is not possible to make a bet, that would overflow
        #    some of the pools (For or Against) (so they exceed total liquidity provided)

        # TODO: make this test inside sandbox

        # TODO: test that first LP succesfully adds liquidity in not equal rate
        # TODO: scenario where target dynamics is negative
