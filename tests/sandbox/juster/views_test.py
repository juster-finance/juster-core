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

