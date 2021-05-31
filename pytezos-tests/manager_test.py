""" Manager tests:

    - update config x2
    - reset config
    - TODO: change manager test

"""

from state_transformation_base import StateTransformationBaseTest, RUN_TIME, ONE_HOUR
from pytezos import MichelsonRuntimeError
from os.path import dirname, join

RAISE_LIQ_FEE_LAMBDA_FN = '../build/tz/lambda_raise_liq_fee.tz'
RESET_CONFIG_LAMBDA_FN = '../build/tz/lambda_reset_new_event_config.tz'


class ManagerDeterminedTest(StateTransformationBaseTest):

    def test_update_config(self):
        
        self.current_time = RUN_TIME
        self.id = len(self.storage['events'])

        raise_liq_code = open(join(dirname(__file__), RAISE_LIQ_FEE_LAMBDA_FN)).read()
        reset_config_code = open(join(dirname(__file__), RESET_CONFIG_LAMBDA_FN)).read()

        # Creating first event with default params:
        self.storage = self.check_new_event_succeed(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee)

        # Default max liquidity percent is 30%:
        assert self.storage['config']['maxLiquidityPercent'] == 300_000

        # raise_liq_code lambda should raise maxLiquidityPercent to 310_000:
        self.storage = self.check_update_config_succeed(raise_liq_code, self.manager)
        assert self.storage['config']['maxLiquidityPercent'] == 310_000

        # Creating next event with default params:
        next_event_id = len(self.storage['events'])
        new_params = self.default_event_params.copy()
        new_params['liquidityPercent'] = 310_000
        self.id = next_event_id
        self.storage = self.check_new_event_succeed(
            event_params=new_params,
            amount=self.measure_start_fee + self.expiration_fee)

        assert self.storage['events'][next_event_id]['liquidityPercent'] == 310_000

        # Testing that updateConfig from address =/= manager is failed:
        self.check_update_config_fails_with(raise_liq_code, self.c)

        # Testing that second time lambda applied:
        self.storage = self.check_update_config_succeed(raise_liq_code, self.manager)
        assert self.storage['config']['maxLiquidityPercent'] == 320_000

        # Testing reset config lambda applied:
        self.storage = self.check_update_config_succeed(reset_config_code, self.manager)
        assert self.storage['config']['maxLiquidityPercent'] == 300_000
