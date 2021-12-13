from tests.sandbox.sandbox_base import SandboxedJusterTestCase
from pytezos.rpc.errors import MichelsonError
from pytezos.michelson.micheline import MichelsonRuntimeError


class ViewsSandboxTestCase(SandboxedJusterTestCase):

    def test_views(self):

        # checking that initial nextEventId is 0
        self.assertEqual(self.juster.getNextEventId().storage_view(), 0)

        # creating event and checking getEventCreatorAddress view:
        self._create_simple_event(self.a)
        self.bake_block()

        # trying to get view of not existed event should fail:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            creator = self.juster.getEventCreatorAddress(1).storage_view()
        self.assertTrue('Event is not found' in str(cm.exception))

        # TODO: why does this return 0?
        # self.assertEqual(self.juster.getNextEventId().storage_view(), 1)
        creator = self.juster.getEventCreatorAddress(0).storage_view()
        self.assertEqual(creator, self.a.key.public_key_hash())

        # creating another event with another address:
        self._create_simple_event(self.b)
        self.bake_block()
        creator = self.juster.getEventCreatorAddress(1).storage_view()
        self.assertEqual(creator, self.b.key.public_key_hash())

        # providing liquidity and bet:
        self._provide_liquidity(
            event_id=0,
            user=self.b,
            expected_below=1,
            expected_above_eq=1,
            amount=1_000_000
        )
        self.bake_block()

        self._bet(
            event_id=0,
            user=self.b,
            side='aboveEq',
            minimal_win_amount=1_500_000,
            amount=1_000_000
        )
        self.bake_block()

        # checking that B position is expected:
        expected_position = {
            'betsAboveEq': 1_500_000,
            'betsBelow': 0,
            'depositedBets': 1_000_000,
            'depositedLiquidity': 1_000_000,
            'isWithdrawn': False,
            'liquidityShares': 100_000_000,
            'providedLiquidityAboveEq': 1_000_000,
            'providedLiquidityBelow': 1_000_000
        }

        key = (self.b.key.public_key_hash(), 0)
        position = self.juster.getPosition(key).storage_view()
        self.assertEqual(position, expected_position)

