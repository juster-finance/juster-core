from sandbox_base import SandboxedJusterTestCase
from pytezos.rpc.errors import MichelsonError


class SandboxLineAggregatorTestCase(SandboxedJusterTestCase):

    def _add_line(self, user):
        line_params = {
            'currencyPair': 'XTZ-USD',
            'targetDynamics': 1_000_000,
            'liquidityPercent': 0,
            'rateAboveEq': 1,
            'rateBelow': 1,
            'measurePeriod': 3600,
            'betsPeriod': 3600,
            'lastBetsCloseTime': 0,
            'maxActiveEvents': 2
        }

        opg = (user.contract(self.line_aggregator.address)
            .addLine(line_params)
            .send()
        )

        return opg


    def _deposit_liquidity(self, user, amount):
        opg = (user.contract(self.line_aggregator.address)
            .depositLiquidity()
            .with_amount(amount)
            .send()
        )

        return opg


    def _aggregator_create_event(self, user, lineId=0):
        opg = (user.contract(self.line_aggregator.address)
            .createEvent(lineId)
            .send()
        )

        return opg


    def test_line_aggregator(self):
        self._add_line(self.manager)
        self.bake_block()

        # A deposits 10 tez + fees to create two events in line:
        event_creation_fees = self.line_aggregator.storage['newEventFee']() * 2
        self._deposit_liquidity(self.a, 10_000_000 + event_creation_fees)
        self.bake_block()

        # A runs event:
        opg = self._aggregator_create_event(self.a)
        self.bake_block()
        result = self._find_call_result_by_hash(self.a, opg.hash())

        # as far as two event in line are supposed, amount of provided liquidity
        # should be 5tez:
        event_params = self.juster.storage['events'][0]()
        self.assertEqual(event_params['poolBelow'], 5_000_000)
        self.assertEqual(event_params['poolAboveEq'], 5_000_000)

        # TODO: run event with all measurements and some bets
        # TODO: let provider withdraw

