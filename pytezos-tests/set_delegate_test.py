""" Testing that set delegate is works properly """

from state_transformation_base import (
    StateTransformationBaseTest, RUN_TIME, ONE_HOUR)
from pytezos import MichelsonRuntimeError


class SetDelegateDeterminedTest(StateTransformationBaseTest):

    def test_set_delegate(self):

        self.current_time = RUN_TIME
        random_delegate_from_twitter = 'tz3e7LbZvUtoXhpUD1yb6wuFodZpfYRb9nWJ'
        result = self.contract.setDelegate(random_delegate_from_twitter).interpret(
            now=self.current_time, storage=self.storage)

        self.assertTrue(len(result.operations) == 1)

        operation = result.operations[0]
        self.assertEqual(operation['kind'], 'delegation')
        self.assertEqual(operation['delegate'], random_delegate_from_twitter)
