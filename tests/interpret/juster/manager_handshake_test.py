from pytezos import MichelsonRuntimeError

from tests.interpret.juster.juster_base import JusterBaseTestCase


class ManagerHandshakeTestCase(JusterBaseTestCase):

    def test_should_allow_to_propose_new_manager_by_manager(self):
        self.change_manager(sender=self.manager, new_manager=self.c)


    def test_should_allow_to_accept_manager_if_proposed(self):
        self.storage['proposedManager'] = self.c
        self.accept_ownership(sender=self.c)


    def test_should_fail_if_propose_new_manager_by_not_manager(self):
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.change_manager(sender=self.c, new_manager=self.c)
        self.assertTrue("Not a contract manager" in str(cm.exception))


    def test_should_fail_if_accept_manager_if_not_proposed(self):
        self.storage['proposedManager'] = None
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.accept_ownership(sender=self.c)
        self.assertTrue("Not allowed to accept ownership" in str(cm.exception))


    def test_should_fail_if_accept_manager_if_proposed_another(self):
        self.storage['proposedManager'] = self.c
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.accept_ownership(sender=self.b)
        self.assertTrue("Not allowed to accept ownership" in str(cm.exception))


    def test_should_allow_to_change_manager_and_return_rights_back(self):
        self.change_manager(sender=self.manager, new_manager=self.c)
        self.accept_ownership(sender=self.c)

        self.change_manager(sender=self.c, new_manager=self.manager)
        self.accept_ownership(sender=self.manager)

