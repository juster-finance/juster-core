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
            # TODO: this amount should be zero, fees should be provided by aggregator pool
            .with_amount(300_000)
            .send()
        )

        return opg


    def test_line_aggregator(self):
        self._create_simple_event(self.manager)

        self._add_line(self.manager)
        self.bake_block()

        # A deposits 10 tez:
        self._deposit_liquidity(self.a, 10_000_000)
        self.bake_block()

        # A runs event:
        self._aggregator_create_event(self.a)
        self.bake_block()

        # UNDER DEVELOPMENT: create event fails because there are no view in Juster
        import pdb; pdb.set_trace()

