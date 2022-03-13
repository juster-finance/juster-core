from tests.interpret.line_aggregator.line_aggregator_base import LineAggregatorBaseTestCase
from pytezos import MichelsonRuntimeError


class AddLineTestCase(LineAggregatorBaseTestCase):

    def test_should_allow_admin_to_add_new_lines(self):
        self.add_line(sender=self.manager)

    def test_should_fail_if_not_admin_adds_new_line(self):
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.add_line(self.c)
        self.assertTrue('Not a contract manager' in str(cm.exception))

