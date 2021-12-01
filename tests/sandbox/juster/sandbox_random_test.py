""" Testing random bets/provideLiuqidity actions to make sure withdrawals are
    the same as deposited value
"""

import unittest
from tests.sandbox.sandbox_base import SandboxedJusterTestCase
from pytezos.rpc.errors import MichelsonError
from random import choice
from tqdm import tqdm


ITERATIONS = 1


class SandboxRandomTestCase(SandboxedJusterTestCase):

    def random_provide_liquidity(self, event_id, user):

        random_amount = choice([1_000_000, 3_000_000, 5_000_000, 10_000_000])
        self._provide_liquidity(
            event_id=event_id,
            user=user,
            amount=random_amount
        )

        return random_amount


    def random_bet(self, event_id, user):

        random_amount = choice([100_000, 300_000, 500_000, 1_000_000])
        self._provide_liquidity(
            event_id=event_id,
            user=user,
            amount=random_amount
        )

        return random_amount


    def withdraw_and_get_balance(self, event_id, user):

        opg = self._withdraw(event_id, user)
        self.bake_block()

        # getting info aobut withdrawal amount:
        opg = user.shell.blocks['head':].find_operation(opg.hash())
        self.assertEqual(len(opg['contents']), 1)
        op = opg['contents'][0]
        self.assertEqual(len(op['metadata']['internal_operation_results']), 1)
        internal_op = op['metadata']['internal_operation_results'][0]

        return int(internal_op['amount'])


    @unittest.skip("this test fails with RpcError 404, need to find out why")
    # This test working if it is runned alone but fails if it is runned by pytest
    def test_withdrawals_should_be_the_same_as_deposits(self):
        """ This test takes a lot of time, about 2 minute
            for 50 bets and 2 iterations
        """

        def iterate_users():
            while True:
                yield self.a
                yield self.b
                yield self.c
        user_iterator = iterate_users()

        for event_id in tqdm(range(ITERATIONS)):
            print(f'creating event {event_id}')

            bets_time = 25
            self._create_simple_event(self.manager, bets_time=bets_time)

            self._provide_liquidity(
                event_id=event_id,
                expected_above_eq=1,
                expected_below=1
            )
            self.bake_block()

            deposited = 0

            for number in range(bets_time - 1):
                action = choice([
                    # self.random_provide_liquidity,
                    self.random_bet
                ])

                user = next(user_iterator)
                deposited += action(event_id, user)
                self.bake_block()
                # TODO: decide if this bake_block() should be inside action in sandbox base?
                # this would simplify testing and checking that state is correct for universal cases

            # is_failing = choice([True, False])
            is_failing = False

            if is_failing:
                [self.bake_block() for _ in range(11)]
                self._run_force_majeure(event_id)
                print(f'{event_id} event failed')
            else:
                self._run_measurements(event_id)
                print(f'{event_id} event succeeded')

            withdrawals = (
                self.withdraw_and_get_balance(event_id, self.a)
                + self.withdraw_and_get_balance(event_id, self.b)
                + self.withdraw_and_get_balance(event_id, self.c)
            )

            # TODO: withdraw claimRewards?
            self.assertEqual(withdrawals, deposited)

