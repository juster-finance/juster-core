""" Manager tests:

    - update config x2
    - reset config
    - TODO: change manager test

"""

from state_transformation_base import StateTransformationBaseTest, RUN_TIME, ONE_HOUR
from pytezos import MichelsonRuntimeError
from os.path import dirname, join

RAISE_LIQ_FEE_LAMBDA_FN = 'lambda_raise_liq_fee.tz'
RESET_CONFIG_LAMBDA_FN = 'NotCompiledYet.tz'


class ManagerDeterminedTest(StateTransformationBaseTest):

    def test_update_config(self):
        
        self.current_time = RUN_TIME
        self.id = len(self.storage['events'])

        raise_liq_code = open(join(dirname(__file__), RAISE_LIQ_FEE_LAMBDA_FN)).read()

        # Creating first event with default params:
        self.storage = self.check_new_event_succeed(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee)

        # Default liquidity percent is zero:
        assert self.storage['newEventConfig']['liquidityPercent'] == 0
        assert self.storage['events'][self.id]['liquidityPercent'] == 0

        # raise_liq_code lambda should raise liquidityPercent to 10_000:
        self.storage = self.check_update_config_succeed(raise_liq_code, self.manager)
        assert self.storage['newEventConfig']['liquidityPercent'] == 10_000

        # Creating next event with default params:
        next_event_id = len(self.storage['events'])
        self.id = next_event_id
        self.storage = self.check_new_event_succeed(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee)

        assert self.storage['events'][next_event_id]['liquidityPercent'] == 10_000

        # Testing that updateConfig from address =/= manager is failed:
        self.check_update_config_fails_with(raise_liq_code, self.c)

        # Testing that second time lambda applied:
        self.storage = self.check_update_config_succeed(raise_liq_code, self.manager)
        assert self.storage['newEventConfig']['liquidityPercent'] == 10_000 * 2

        # TODO: Test reset config

