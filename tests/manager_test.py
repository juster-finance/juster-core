""" Manager tests:

    - update config x2
    - reset config
    - change manager

"""

from juster_base import JusterBaseTestCase, RUN_TIME, ONE_HOUR
from pytezos import MichelsonRuntimeError
from os.path import dirname, join

RAISE_LIQ_FEE_LAMBDA_FN = '../build/tz/lambda_raise_liq_fee.tz'
RESET_CONFIG_LAMBDA_FN = '../build/tz/lambda_reset_new_event_config.tz'


class ManagerTest(JusterBaseTestCase):

    def test_update_config(self):

        self.current_time = RUN_TIME
        self.id = self.storage['nextEventId']

        raise_liq_code = open(join(dirname(__file__), RAISE_LIQ_FEE_LAMBDA_FN)).read()
        reset_config_code = open(join(dirname(__file__), RESET_CONFIG_LAMBDA_FN)).read()

        # Creating first event with default params:
        self.storage = self.new_event(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee)

        # Default max liquidity percent is 30%:
        assert self.storage['config']['maxLiquidityPercent'] == 300_000

        # raise_liq_code lambda should raise maxLiquidityPercent to 310_000:
        self.storage = self.update_config(raise_liq_code, self.manager)
        assert self.storage['config']['maxLiquidityPercent'] == 310_000

        # Creating next event with default params:
        new_params = self.default_event_params.copy()
        new_params['liquidityPercent'] = 310_000
        self.id = self.storage['nextEventId']
        self.storage = self.new_event(
            event_params=new_params,
            amount=self.measure_start_fee + self.expiration_fee)

        assert self.storage['events'][self.id]['liquidityPercent'] == 310_000

        # Testing that updateConfig from address =/= manager is failed:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.update_config(raise_liq_code, self.c)

        # Testing that second time lambda applied:
        self.storage = self.update_config(raise_liq_code, self.manager)
        assert self.storage['config']['maxLiquidityPercent'] == 320_000

        # Testing reset config lambda applied:
        self.storage = self.update_config(reset_config_code, self.manager)
        assert self.storage['config']['maxLiquidityPercent'] == 300_000


    def test_change_manager(self):

        # C tries to run acceptOwnership rights with no success:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.contract.acceptOwnership().interpret(
                storage=self.storage,
                sender=self.c)
        self.assertTrue("Not allowed to accept ownership" in str(cm.exception))

        # manager A call transfer rights to another address B:
        result = self.contract.changeManager(self.b).interpret(
                storage=self.storage,
                sender=self.manager)
        assert result.storage['proposedManager'] == self.b
        self.storage = result.storage

        # Checking that another address C can't claim baking rewards:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.contract.claimBakingRewards().interpret(
                    storage=self.storage,
                    sender=self.c)
        self.assertTrue("Not a contract manager" in str(cm.exception))

        # Checking that proposed manager can't claim retained profits:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.contract.claimRetainedProfits().interpret(
                    storage=self.storage,
                    sender=self.b)
        self.assertTrue("Not a contract manager" in str(cm.exception))

        # And checking that current manager still can run claim:
        self.contract.claimBakingRewards().interpret(
                storage=self.storage,
                sender=self.manager)

        # Checking that the same old manager A can change rights
        # again to another address C:
        result = self.contract.changeManager(self.c).interpret(
                storage=self.storage,
                sender=self.manager)
        assert result.storage['proposedManager'] == self.c
        self.storage = result.storage

        # Checking that another address D can't accpept rights:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.contract.acceptOwnership().interpret(
                storage=self.storage,
                sender=self.d)
        self.assertTrue("Not allowed to accept ownership" in str(cm.exception))

        # Check that another address B can't accpept rights too:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.contract.acceptOwnership().interpret(
                storage=self.storage,
                sender=self.b)
        self.assertTrue("Not allowed to accept ownership" in str(cm.exception))

        # check that another address C can accpept rights:
        result = self.contract.acceptOwnership().interpret(
            storage=self.storage,
            sender=self.c)
        assert result.storage['manager'] == self.c
        assert result.storage['proposedManager'] == None
        self.storage = result.storage

        # Check that another address C can run now withdraw both
        # baking rewards and retained profits:

        result = self.contract.claimRetainedProfits().interpret(
                storage=self.storage,
                sender=self.c)
        self.storage = result.storage

        result = self.contract.claimBakingRewards().interpret(
                storage=self.storage,
                sender=self.c)
        self.storage = result.storage
