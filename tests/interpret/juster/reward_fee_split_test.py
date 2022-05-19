""" Testing how reward fee splitted between sender and participant """

from tests.interpret.juster.juster_base import JusterBaseTestCase, RUN_TIME, ONE_HOUR
from pytezos import MichelsonRuntimeError


class RewardFeeSplitTest(JusterBaseTestCase):

    def _prepare_to_test(self):

        self.current_time = RUN_TIME
        self.id = self.storage['nextEventId']

        fees = self.measure_start_fee + self.expiration_fee
        self.new_event(
            event_params=self.default_event_params, amount=fees)

        # D provides 1tez liquidity:
        self.provide_liquidity(
            participant=self.d,
            amount=1_000_000,
            expected_above_eq=1,
            expected_below=1)

        # A bets above 1tez and wins:
        self.bet(
            participant=self.a,
            amount=1_000_000,
            bet='aboveEq',
            minimal_win=1_500_000)

        # B bets below 1tez and looses:
        self.bet(
            participant=self.b,
            amount=500_000,
            bet='below',
            minimal_win=1_500_000)

        # C provides 10mutez liquidity (to test transaction less than reward fee):
        self.provide_liquidity(
            participant=self.c,
            amount=10,
            expected_above_eq=1,
            expected_below=1)

        # In the end: no one bets, starting measure:
        bets_close = self.default_event_params['betsCloseTime']
        period = self.default_event_params['measurePeriod']
        self.current_time = bets_close

        # Emulating callback:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time,
            'rate': 3_500_000
        }
        self.start_measurement(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address)

        # Closing event:
        self.current_time = bets_close + period
        callback_values.update({'lastUpdate': self.current_time})

        self.close(
            callback_values=callback_values,
            source=self.b,
            sender=self.oracle_address)


    def test_reward_fee_split_different_sender(self):
        self._prepare_to_test()

        # withdrawing with different sender just after close
        # should be the same as if it was called by participant:
        self.withdraw(self.a, 1_500_000, sender=self.d)
        self.withdraw(self.b, 0, sender=self.c)
        self.withdraw(self.c, 10, sender=self.b)
        self.withdraw(self.d, 1_000_000, sender=self.a)


    def test_reward_fee_split_sender_participant(self):
        self._prepare_to_test()

        # withdrawing after reward fee with sender === participant should not
        # be different:
        reward_fee_after = self.default_config['rewardFeeSplitAfter']
        self.current_time = self.current_time + reward_fee_after

        self.withdraw(self.a, 1_500_000, sender=self.a)
        self.withdraw(self.b, 0, sender=self.b)
        self.withdraw(self.c, 10, sender=self.c)
        self.withdraw(self.d, 1_000_000, sender=self.d)


    def test_reward_fee_split_extra_transactions(self):
        self._prepare_to_test()

        # withdrawing after reward fee with sender =/= participant should
        # make additional transactions to sender:
        reward_fee_after = self.default_config['rewardFeeSplitAfter']
        self.current_time = self.current_time + reward_fee_after

        self.withdraw(self.a, 1_500_000, sender=self.d)
        self.withdraw(self.b, 0, sender=self.c)
        self.withdraw(self.c, 10, sender=self.b)
        self.withdraw(self.d, 1_000_000, sender=self.a)


    def test_reward_fee_split_explicit_test(self):
        self._prepare_to_test()

        # implicit test with participant D:
        reward_fee_after = self.default_config['rewardFeeSplitAfter']
        self.current_time = self.current_time + reward_fee_after

        params = {'eventId': self.id, 'participantAddress': self.d}
        result = self.contract.withdraw(params).interpret(
            storage=self.storage, sender=self.a, now=self.current_time)
        self.assertEqual(len(result.operations), 2)

        amounts = {
                operation['destination']: int(operation['amount'])
                for operation in result.operations}
        reward_fee = self.default_config['rewardCallFee']

        self.assertEqual(amounts[self.a], reward_fee)
        self.assertEqual(amounts[self.d], 1_000_000 - reward_fee)

        # implicit test that all all withdraw amount for C is goes to sender:
        params = {'eventId': self.id, 'participantAddress': self.c}
        result = self.contract.withdraw(params).interpret(
            storage=self.storage, sender=self.d, now=self.current_time)
        self.assertEqual(len(result.operations), 1)
        result.operations[0]['amount'] == '10'
        result.operations[0]['destination'] == self.d

        # test that in force majeure no reward are excluded:
        self.storage['events'][self.id].update({'isForceMajeure': True})
        self.withdraw(self.a, 1_000_000, sender=self.d)
        self.withdraw(self.b, 500_000, sender=self.c)
        self.withdraw(self.c, 10, sender=self.b)
        self.withdraw(self.d, 1_000_000, sender=self.a)


    def test_reward_fee_split_explicit_test_b(self):
        self._prepare_to_test()

        # implicit test with participant C:
        reward_fee_after = self.default_config['rewardFeeSplitAfter']
        self.current_time = self.current_time + reward_fee_after

        params = {'eventId': self.id, 'participantAddress': self.c}
        result = self.contract.withdraw(params).interpret(
            storage=self.storage, sender=self.d, now=self.current_time)
        self.assertEqual(len(result.operations), 1)
        result.operations[0]['amount'] == '10'
        result.operations[0]['destination'] == self.c
