import unittest
from tests.sandbox.sandbox_base import SandboxedJusterTestCase, pkh
from pytezos.rpc.errors import MichelsonError
from tests.test_data import generate_line_params


# TODO: split into SandboxPoolBaseTestCase and others?
class SandboxPoolTestCase(SandboxedJusterTestCase):

    def _add_line(
            self,
            user,
            measure_period=1,
            currency_pair='XTZ-USD',
            target_dynamics=1_000_000,
            max_events=2,
            juster_address=None
        ):

        juster_address = juster_address or self.juster.address
        line_params = generate_line_params(
            bets_period=20,
            measure_period=measure_period,
            max_events=max_events,
            target_dynamics=target_dynamics,
            juster_address=juster_address)

        opg = (user.contract(self.pool.address)
            .addLine(line_params)
            .send()
        )

        return opg


    def _deposit_liquidity(self, user, amount):
        opg = (user.contract(self.pool.address)
            .depositLiquidity()
            .with_amount(amount)
            .send()
        )

        return opg


    def _approve_liquidity(self, user, entry_id):
        opg = (user.contract(self.pool.address)
            .approveLiquidity(entry_id)
            .send()
        )

        return opg


    def _pool_create_event(self, user, line_id=0):
        opg = (user.contract(self.pool.address)
            .createEvent(line_id)
            .send()
        )

        return opg


    def _claim_liquidity(self, user, position_id=0, shares=0):
        opg = (user.contract(self.pool.address)
            .claimLiquidity(positionId=position_id, shares=shares)
            .send()
        )

        return opg


    def _pool_withdraw(self, user, event_id=0, position_id=0):
        claims = [{
            'positionId': position_id,
            'eventId': event_id
        }]

        opg = (user.contract(self.pool.address)
            .withdrawLiquidity(claims)
            .send()
        )

        return opg


    def test_pool(self):
        self._add_line(self.manager)
        self.bake_block()

        # A deposits 10 tez + fees to create two events in line:
        config = self.juster.getConfig().onchain_view()
        event_creation_fee = config['measureStartFee'] + config['expirationFee']
        shares = 10_000_000 + event_creation_fee*2
        self._deposit_liquidity(self.a, shares)
        self.bake_block()

        self._approve_liquidity(self.a, 0)
        self.bake_block()

        # A runs event:
        opg = self._pool_create_event(self.a)
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
        [self.bake_block() for _ in range(30)]
        self._run_measurements()

        # withdrawing for pool (should be 10 tez):
        self._withdraw(participant_address=self.pool.address)
        self.bake_block()

        # withdrawing for claimed position for A, should be 40% of 10 tez:
        opg = self._pool_withdraw(self.a, 0, 0)
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
        self.assertEqual(self.pool.getBalance().storage_view(), 0)


    def test_double_liquidity_provided_the_same_amount(self):

        self._add_line(self.manager)
        self.bake_block()

        # providing first liquidity:
        self._deposit_liquidity(self.a, 10_000_000)
        self.bake_block()

        self._approve_liquidity(self.a, 0)
        self.bake_block()

        shares = self.pool.storage['positions'][0]()['shares']
        self.assertEqual(shares, 10_000_000)

        # providing liquidity second time, nohting else changed:
        self._deposit_liquidity(self.a, 10_000_000)
        self.bake_block()

        self._approve_liquidity(self.a, 1)
        self.bake_block()

        shares = self.pool.storage['positions'][1]()['shares']
        self.assertEqual(shares, 10_000_000)


    @unittest.skip("this test require 2 minutes to complete, so it is skipped now")
    def test_pool_load(self):
        # TODO: really want to split this test into multiple but then I got
        # pytezos.rpc.node.RpcError (node.validator.checkpoint_error)

        # creating multiple lines with three events in each and run for ten providers
        # the real load should be about 9-27 lines the load that really can be onchain
        # hangzhounet tested for 300 lines x 50 providers
        # (about 60% of gas_limit per operation used):
        LINES = 27
        PROVIDERS = 10

        for line in range(LINES):
            self._add_line(
                self.manager,
                target_dynamics=1_000_000 + line,
                measure_period=1,
                max_events=3)

        self.bake_block()
        self.assertEqual(len(self.pool.storage['lines']()), LINES)

        for entry_id in range(PROVIDERS):
            self._deposit_liquidity(self.a, 10_000_000)
        self.bake_block()

        self.assertEqual(
            self.pool.storage['nextEntryId'](), PROVIDERS)

        for entry_id in range(PROVIDERS):
            self._approve_liquidity(self.a, entry_id)
        self.bake_block()

        self.assertEqual(
            self.pool.storage['nextPositionId'](), PROVIDERS)

        # creating events (1):
        for line_id in range(LINES):
            opg = self._pool_create_event(self.a, line_id=line_id)
            if (line_id % 100 == 1):
                self.bake_block()

        self.bake_block()

        # creating events (2):
        for line_id in range(LINES):
            opg = self._pool_create_event(self.a, line_id=line_id)
            if (line_id % 100 == 1):
                self.bake_block()

        self.bake_block()

        # claiming some liquitidy (there should be internal loop for all events):
        # (this is the most gas consuming operation in pool)
        # for 300 lines x2 events gas_limit: 671280 and storage_limit: 48697
        opg = self._claim_liquidity(self.a, 0, 10_000_000)
        opg = self._claim_liquidity(self.a, 1, 5_000_000)
        self.bake_block()

        # running measuerements for (1):
        for event_id in range(LINES):
            self._run_measurements(event_id)
        self.bake_block()

        # withdrawing for (1):
        for event_id in range(LINES):
            self._withdraw(
                event_id=event_id,
                participant_address=self.pool.address
            )

        self.bake_block()

        # withdrawing for participant:
        for event_id in range(LINES):
            opg = self._pool_withdraw(self.a, event_id, 0)
            opg = self._pool_withdraw(self.a, event_id, 1)

        self.bake_block()

        # checking that withdrawal amount for the last event and participant
        # who withdrawn 5/100 shares is calculated properly:
        result = self._find_call_result_by_hash(self.a, opg.hash())
        event_result = self.pool.storage['events'][event_id]()['result']
        self.assertEqual(
            int(result.operations[0]['amount']),
            int(event_result * 5 / 100)
        )

