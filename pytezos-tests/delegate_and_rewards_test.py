""" Testing that set delegate is works properly """

from state_transformation_base import (
    StateTransformationBaseTest, RUN_TIME, ONE_HOUR)
from pytezos import MichelsonRuntimeError


class DelegateAndBakingRewardsDeterminedTest(StateTransformationBaseTest):

    def test_delegate_and_baking_rewards(self):

        self.current_time = RUN_TIME
        random_delegate_from_twitter = 'tz3e7LbZvUtoXhpUD1yb6wuFodZpfYRb9nWJ'
        result = self.contract.setDelegate(random_delegate_from_twitter).interpret(
            now=self.current_time, storage=self.storage)

        self.assertTrue(len(result.operations) == 1)

        operation = result.operations[0]
        self.assertEqual(operation['kind'], 'delegation')
        self.assertEqual(operation['delegate'], random_delegate_from_twitter)
        self.storage = result.storage

        # Sending 200_000 mutez to contract:
        result = self.contract.default().with_amount(200_000).interpret(
            now=self.current_time,
            storage=self.storage,
            sender=random_delegate_from_twitter)
        self.storage = result.storage

        # Trying to withdraw with address different from manager:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            result = self.contract.claimBakingRewards().interpret(
                now=self.current_time,
                storage=self.storage,
                sender=self.c)
        msg = 'Only contract manager allowed to claim baking rewards'
        self.assertTrue(msg in str(cm.exception))

        # Withdrawing with manager:
        result = self.contract.claimBakingRewards().interpret(
            now=self.current_time,
            storage=self.storage,
            sender=self.manager)
        self.storage = result.storage
        self.assertEqual(len(result.operations), 1)

        operation = result.operations[0]
        self.assertEqual(operation['destination'], self.manager)
        self.assertAmountEqual(operation, 200_000)

        # Sending another 500_000 mutez to contract:
        result = self.contract.default().with_amount(500_000).interpret(
            now=self.current_time,
            storage=self.storage,
            sender=random_delegate_from_twitter)
        self.storage = result.storage

        # Withdrawing with manager again:
        result = self.contract.claimBakingRewards().interpret(
            now=self.current_time,
            storage=self.storage,
            sender=self.manager)
        self.storage = result.storage
        self.assertEqual(len(result.operations), 1)

        operation = result.operations[0]
        self.assertEqual(operation['destination'], self.manager)
        self.assertAmountEqual(operation, 500_000)
