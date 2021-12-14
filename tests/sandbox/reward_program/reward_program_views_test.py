from tests.sandbox.sandbox_base import SandboxedJusterTestCase
from pytezos.rpc.errors import MichelsonError


class RewardProgramViewsTestCase(SandboxedJusterTestCase):

    def test_reward_program_views(self):
        self._deploy_reward_program(self.client, self.juster.address)
        self.assertFalse(self.reward_program.storage['result']())

        # should fail if position is not found:
        with self.assertRaises(MichelsonError) as cm:
            self.b.contract(self.reward_program.address).provideEvidence([0]).send()
        self.assertTrue('Position is not found' in str(cm.exception))

        # creating event and checking getEventCreatorAddress view:
        self._create_simple_event(self.a)
        self.bake_block()

        # providing liquidity and bet:
        self._provide_liquidity(
            event_id=0,
            user=self.b,
            expected_below=1,
            expected_above_eq=1,
            amount=1_000_000
        )
        self.bake_block()

        # checking that B position get positive result:
        self.b.contract(self.reward_program.address).provideEvidence([0]).send()
        self.bake_block()

        self.assertTrue(self.reward_program.storage['result']())

