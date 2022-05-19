from pytezos.michelson.micheline import MichelsonRuntimeError

from tests.sandbox.sandbox_base import SandboxedJusterTestCase


class ViewsSandboxTestCase(SandboxedJusterTestCase):

    def test_views(self):

        # checking that initial nextEventId is 0
        self.assertEqual(self.juster.getNextEventId().storage_view(), 0)

        # checking that a was not participated in 0 event:
        key = (self.a.key.public_key_hash(), 0)
        self.assertFalse(self.juster.isParticipatedInEvent(key).storage_view())

        # creating event and checking getEventCreatorAddress view:
        self._create_simple_event(self.a)
        self.bake_block()

        # trying to get view of not existed event should fail:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            event = self.juster.getEvent(1).storage_view()
        self.assertTrue('Event is not found' in str(cm.exception))

        self.assertEqual(self.juster.getNextEventId().storage_view(), 1)
        event = self.juster.getEvent(0).storage_view()
        self.assertEqual(event['creator'], self.a.key.public_key_hash())

        # creating another event with another address:
        self._create_simple_event(self.b)
        self.bake_block()
        event = self.juster.getEvent(1).storage_view()
        self.assertEqual(event['creator'], self.b.key.public_key_hash())

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

        # checking that b was participated in 0 event and a was not:
        key = (self.b.key.public_key_hash(), 0)
        self.assertTrue(self.juster.isParticipatedInEvent(key).storage_view())
        key = (self.a.key.public_key_hash(), 0)
        self.assertFalse(self.juster.isParticipatedInEvent(key).storage_view())

        # and B was not participated in 1 event:
        key = (self.b.key.public_key_hash(), 1)
        self.assertFalse(self.juster.isParticipatedInEvent(key).storage_view())

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

        # checking event params:
        event = self.juster.getEvent(0).storage_view()
        self.assertEqual(event['poolAboveEq'], 2_000_000)
        self.assertEqual(event['poolBelow'], 500_000)
        self.assertEqual(event['totalLiquidityShares'], 100_000_000)

        # requesting non existed position should fail:
        wrong_key = (self.b.key.public_key_hash(), 1)
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.juster.getPosition(wrong_key).storage_view()
        self.assertTrue('Position is not found' in str(cm.exception))

        wrong_key = (self.c.key.public_key_hash(), 0)
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.juster.getPosition(wrong_key).storage_view()
        self.assertTrue('Position is not found' in str(cm.exception))
