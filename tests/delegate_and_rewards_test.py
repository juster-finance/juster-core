""" Testing that set delegate is works properly """

from juster_base import (
    JusterBaseTestCase, RUN_TIME, ONE_HOUR)
from pytezos import MichelsonRuntimeError


class DelegateAndBakingRewardsTest(JusterBaseTestCase):

    def test_delegate_and_baking_rewards(self):

        self.current_time = RUN_TIME
        random_delegate_from_twitter = 'tz3e7LbZvUtoXhpUD1yb6wuFodZpfYRb9nWJ'

        # Only manager can set delegate:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.contract.setDelegate(random_delegate_from_twitter).interpret(
                now=self.current_time, storage=self.storage, sender=self.d)
        self.assertTrue("Not a contract manager" in str(cm.exception))

        result = self.contract.setDelegate(random_delegate_from_twitter).interpret(
            now=self.current_time, storage=self.storage, sender=self.manager)

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
        self.check_claim_baking_rewards_fails_with(
            expected_reward=200_000,
            sender=self.c,
            msg_contains='Not a contract manager')

        # Withdrawing with manager:
        self.storage = self.check_claim_baking_rewards_succeed(
            expected_reward=200_000, sender=self.manager)

        # Sending another 500_000 mutez to contract:
        result = self.contract.default().with_amount(500_000).interpret(
            now=self.current_time,
            storage=self.storage,
            sender=random_delegate_from_twitter)
        self.storage = result.storage

        # Withdrawing with manager again:
        self.storage = self.check_claim_baking_rewards_succeed(
            expected_reward=500_000, sender=self.manager)