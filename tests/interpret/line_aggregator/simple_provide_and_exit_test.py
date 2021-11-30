from tests.interpret.line_aggregator.line_aggregator_base import LineAggregatorBaseTestCase


class SimpleProvideAndExitTest(LineAggregatorBaseTestCase):
    def test_simple_provide_and_exit(self):

        # creating default event:
        self.add_line()

        '''
        import pdb; pdb.set_trace()

        # providing liquidity:
        self.provide_liquidity(self.a)

        # removing liquidity:
        self.lock_liquidity(self.a, position_id=0)

        # TODO: assert that a.balance is not changed
        # TODO: assert that line_aggregator contract balance not changed
        '''

