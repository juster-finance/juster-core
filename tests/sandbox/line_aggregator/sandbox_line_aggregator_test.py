from tests.sandbox.sandbox_base import SandboxedJusterTestCase, pkh
from pytezos.rpc.errors import MichelsonError
from tests.test_data import generate_line_params


class SandboxLineAggregatorTestCase(SandboxedJusterTestCase):

    def _add_line(self, user):
        line_params = generate_line_params(bets_period=5, measure_period=1)

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


    def _claim_liquidity(self, user, position_id=0, shares=0):
        opg = (user.contract(self.line_aggregator.address)
            .claimLiquidity(positionId=position_id, shares=shares)
            .send()
        )

        return opg


    def _aggregator_withdraw(self, user, event_id=0, position_id=0):
        claims = [{
            'positionId': position_id,
            'eventId': event_id
        }]

        opg = (user.contract(self.line_aggregator.address)
            .withdrawLiquidity(claims)
            .send()
        )

        return opg


    def test_line_aggregator(self):
        self._add_line(self.manager)
        self.bake_block()

        # A deposits 10 tez + fees to create two events in line:
        event_creation_fee = self.line_aggregator.storage['newEventFee']()
        shares = 10_000_000 + event_creation_fee*2
        self._deposit_liquidity(self.a, shares)
        self.bake_block()

        # A runs event:
        opg = self._aggregator_create_event(self.a)
        self.bake_block()

        # as far as two event in line are supposed, amount of provided liquidity
        # should be 5tez:
        event_params = self.juster.storage['events'][0]()
        self.assertEqual(event_params['poolBelow'], 5_000_000)
        self.assertEqual(event_params['poolAboveEq'], 5_000_000)

        # A claims 40% of his liquidity (10tez + fees/2 - 5tez) * 0.4 = :
        opg = self._claim_liquidity(self.a, 0, int(0.4*shares))
        self.bake_block()
        result = self._find_call_result_by_hash(self.a, opg.hash())
        self.assertEqual(len(result.operations), 1)
        op = result.operations[0]
        self.assertEqual(op['destination'], pkh(self.a))
        self.assertEqual(int(op['amount']), 0.4*shares/2)

        # B bets in below:
        bet_res = self._bet(
            event_id=0,
            user=self.b,
            side='below',
            minimal_win_amount=7_500_000,
            amount=5_000_000
        )

        # waiting for the end of the betting period:
        [self.bake_block() for _ in range(5)]
        self._run_measurements()

        # withdrawing for line aggregator (should be 10 tez):
        self._withdraw(participant_address=self.line_aggregator.address)
        self.bake_block()

        # withdrawing for claimed position for A, should be 40% of 10 tez:
        opg = self._aggregator_withdraw(self.a, 0, 0)
        self.bake_block()
        result = self._find_call_result_by_hash(self.a, opg.hash())
        op = result.operations[0]
        self.assertEqual(int(op['amount']), 4_000_000)

        # provider withdraw the rest 60% of the liquidity
        opg = self._claim_liquidity(self.a, 0, int(0.6*shares))
        self.bake_block()
        result = self._find_call_result_by_hash(self.a, opg.hash())
        self.assertEqual(len(result.operations), 1)
        op = result.operations[0]
        self.assertEqual(op['destination'], pkh(self.a))

        # provider returns his 60% of unused liquidity + 6xtz that was earned
        # from the first event (using provider liquidity)
        self.assertEqual(int(op['amount']), 0.6*shares/2 + 6_000_000)

        # nothing should be left on the contract:
        self.assertEqual(self.line_aggregator.getBalance().storage_view(), 0)


    '''
    def test_line_aggregator_load(self):
        pass
        # TODO: create 27 lines with two events in each and ten providers
    '''

