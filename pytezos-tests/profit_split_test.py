""" Test how providerProfitFee calculated and how claim retained profits works """

from state_transformation_base import StateTransformationBaseTest, RUN_TIME, ONE_HOUR
from pytezos import MichelsonRuntimeError


class ProfitSplitDeterminedTest(StateTransformationBaseTest):

    def _create_event_and_provide_liquidity(self):
        """ Creates default event with fee and adds 100k liquidity 1:1 """

        self.current_time = RUN_TIME
        self.id = self.storage['lastEventId']

        # Creating event:
        amount = self.measure_start_fee + self.expiration_fee
        self.storage = self.check_new_event_succeed(
            event_params=self.default_event_params,
            amount=amount)

        # Participant A: adding liquidity 50/50 just at start:
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.a,
            amount=100_000,
            expected_above_eq=1,
            expected_bellow=1)


    def _run_measurement_and_close(self):
        """ Runs default measurement + close when bets AboveEq wins """

        bets_close_time = self.default_event_params['betsCloseTime']
        measure_period = self.default_event_params['measurePeriod']

        # Running measurement:
        self.current_time = bets_close_time
        self.storage = self.check_start_measurement_succeed(sender=self.a)

        # Emulating callback:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time,
            'rate': 6_000_000
        }
        self.storage = self.check_start_measurement_callback_succeed(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address)
            
        # Closing event:
        self.current_time = bets_close_time + measure_period
        self.storage = self.check_close_succeed(sender=self.b)

        # Emulating calback with price is increased 25%:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time,
            'rate': 7_500_000
        }
        self.storage = self.check_close_callback_succeed(
            callback_values=callback_values,
            source=self.b,
            sender=self.oracle_address)


    def test_profit_split_when_provider_have_profit(self):

        self.default_config.update({'providerProfitFee': 500_000})  # 50%
        self._create_event_and_provide_liquidity()

        # Participant B: bets bellow 50_000:
        self.storage = self.check_bet_succeed(
            participant=self.b,
            amount=50_000,
            bet='bellow',
            minimal_win=50_000)

        self._run_measurement_and_close()
        # Bet aboveEq wins, A in profit, B looses
        net_profit = int(50_000 * 0.5)

        # Withdrawals:
        self.storage = self.check_withdraw_succeed(self.a, 100_000 + net_profit)
        self.storage = self.check_withdraw_succeed(self.b, 0)

        # Trying claim profits with not manager assert fails:
        contract_profit = int(50_000 * 0.5)
        self.assertEqual(self.storage['retainedProfits'], contract_profit)
        self.check_claim_retained_profits_fails_with(
            expected_profit=contract_profit,
            sender=self.c,
            msg_contains="Only contract manager allowed to claim retained profits")

        # Claiming profits with manager succeed:
        self.check_claim_retained_profits_succeed(
            expected_profit=contract_profit,
            sender=self.manager)


    def test_profit_split_when_provider_have_losses(self):

        self.default_config.update({'providerProfitFee': 100_000})  # 10%
        self._create_event_and_provide_liquidity()

        # Participant B: bets aboveEq 50_000:
        self.storage = self.check_bet_succeed(
            participant=self.b,
            amount=50_000,
            bet='aboveEq',
            minimal_win=75_000)

        self._run_measurement_and_close()
        # Bet aboveEq wins, A losses, B wins
        losses = 25_000

        # Withdrawals:
        self.storage = self.check_withdraw_succeed(self.a, 100_000 - losses)
        self.storage = self.check_withdraw_succeed(self.b, 75_000)

        self.assertEqual(self.storage['retainedProfits'], 0)


    def test_profit_split_complex(self):

        self.default_config.update({'providerProfitFee': 10_000})  # 1%
        self._create_event_and_provide_liquidity()

        # Participant B: bets aboveEq 50_000:
        self.storage = self.check_bet_succeed(
            participant=self.b,
            amount=50_000,
            bet='aboveEq',
            minimal_win=75_000)

        # current ratio 100:25
        # Participant C: bets bellow 75_000:
        self.storage = self.check_bet_succeed(
            participant=self.c,
            amount=75_000,
            bet='bellow',
            minimal_win=150_000)

        self._run_measurement_and_close()
        # Bet aboveEq wins, A losses, B wins
        net_profit = int((75_000 - 25_000) * 0.99)

        # Withdrawals:
        self.storage = self.check_withdraw_succeed(self.a, 100_000 + net_profit)
        self.storage = self.check_withdraw_succeed(self.c, 0)
        self.storage = self.check_withdraw_succeed(self.b, 75_000)

        # Claiming profits with manager succeed:
        contract_profit = int((75_000 - 25_000) * 0.01)
        self.assertEqual(self.storage['retainedProfits'], contract_profit)

        # Claiming profits with manager succeed:
        self.check_claim_retained_profits_succeed(
            expected_profit=contract_profit,
            sender=self.manager)

