""" Test how providerProfitFee calculated and how claim retained profits works
    + in this test checking how contracts work with very big numbers """

from pytezos import MichelsonRuntimeError

from tests.interpret.juster.juster_base import ONE_HOUR
from tests.interpret.juster.juster_base import RUN_TIME
from tests.interpret.juster.juster_base import JusterBaseTestCase


class ProfitSplitTest(JusterBaseTestCase):
    def _create_event(self):
        """Creates default event with fee and adds 100k liquidity 1:1"""

        self.current_time = RUN_TIME
        self.id = self.storage['nextEventId']

        # Creating event:
        amount = self.measure_start_fee + self.expiration_fee
        self.new_event(event_params=self.default_event_params, amount=amount)

    def _run_measurement_and_close(self):
        """Runs default measurement + close when bets AboveEq wins"""

        bets_close_time = self.default_event_params['betsCloseTime']
        measure_period = self.default_event_params['measurePeriod']

        # Running measurement:
        self.current_time = bets_close_time

        # Emulating callback:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time,
            'rate': 6_000_000,
        }
        self.start_measurement(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address,
        )

        # Closing event:
        self.current_time = bets_close_time + measure_period

        # Emulating calback with price is increased 25%:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time,
            'rate': 7_500_000,
        }
        self.close(
            callback_values=callback_values,
            source=self.b,
            sender=self.oracle_address,
        )

    def test_profit_split_when_provider_have_profit(self):

        self.default_config.update({'providerProfitFee': 500_000})  # 50%
        self._create_event()

        # Participant A: adding liquidity 50/50 just at start:
        self.provide_liquidity(
            participant=self.a,
            amount=50_000,
            expected_above_eq=1,
            expected_below=1,
        )

        # Participant B: bets below 50_000:
        self.bet(
            participant=self.b, amount=50_000, bet='below', minimal_win=50_000
        )

        self._run_measurement_and_close()
        # Bet aboveEq wins, A in profit, B looses
        net_profit = int(50_000 * 0.5)

        # Withdrawals:
        self.withdraw(self.a, 50_000 + net_profit)
        self.withdraw(self.b, 0)

        # Trying claim profits with not manager assert fails:
        contract_profit = int(50_000 * 0.5)
        self.assertEqual(self.storage['retainedProfits'], contract_profit)
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.claim_retained_profits(
                expected_profit=contract_profit, sender=self.c
            )
        self.assertTrue('Not a contract manager' in str(cm.exception))

        # Claiming profits with manager succeed:
        self.claim_retained_profits(
            expected_profit=contract_profit, sender=self.manager
        )

    def test_profit_split_when_provider_have_losses(self):

        self.default_config.update({'providerProfitFee': 100_000})  # 10%
        self._create_event()

        # Participant A: adding liquidity 50/50 just at start:
        self.provide_liquidity(
            participant=self.a,
            amount=50_000,
            expected_above_eq=1,
            expected_below=1,
        )

        # Participant B: bets aboveEq 50_000:
        self.bet(
            participant=self.b,
            amount=50_000,
            bet='aboveEq',
            minimal_win=75_000,
        )

        self._run_measurement_and_close()
        # Bet aboveEq wins, A losses, B wins
        losses = 25_000

        # Withdrawals:
        self.withdraw(self.a, 50_000 - losses)
        self.withdraw(self.b, 75_000)

        self.assertEqual(self.storage['retainedProfits'], 0)

    def test_profit_split_very_big_numbers(self):

        self.default_config.update({'providerProfitFee': 10_000})  # 1%
        self._create_event()

        tez = 1_000_000
        million = 1_000_000

        # Participant A: adding liquidity 50/50 just at start:
        # 500 tez is less than current supply but almost
        self.provide_liquidity(
            participant=self.a,
            amount=500 * million * tez,
            expected_above_eq=1,
            expected_below=1,
        )

        # Participant B: bets below 500 mln tez (and loses):
        self.bet(
            participant=self.b,
            amount=500 * million * tez,
            bet='below',
            minimal_win=750 * million * tez,
        )

        # current ratio 25:100
        # Participant D: adding liquidity with same share as A (and loose some):
        self.provide_liquidity(
            participant=self.d,
            amount=1_000 * million * tez,
            expected_above_eq=1,
            expected_below=4,
        )

        # current ratio 50:200
        # Participant C: bets aboveEq 300 mln (and wins 750 mln):
        self.bet(
            participant=self.c,
            amount=300 * million * tez,
            bet='aboveEq',
            minimal_win=750 * million * tez,
        )

        # current ratio 80:125
        self._run_measurement_and_close()

        # A takes all that B looses (expect 1% contract fee) and splits with D
        # sum that C wins:
        b_losses = 500 * million * tez
        c_wins = 750 * million * tez
        a_share, d_share = 0.5, 0.5
        a_net_profit = int((b_losses - c_wins * a_share) * 0.99)
        contract_profit = int((b_losses - c_wins * a_share) * 0.01)

        # D got loses from C wins:
        d_net_loss = int(c_wins * a_share)

        # Withdrawals:
        self.withdraw(self.a, 500 * million * tez + a_net_profit)
        self.withdraw(self.b, 0)
        self.withdraw(self.c, 300 * million * tez + c_wins)
        self.withdraw(self.d, 1_000 * million * tez - d_net_loss)

        # Claiming profits with manager succeed:
        self.assertEqual(self.storage['retainedProfits'], contract_profit)

        # Claiming profits with manager succeed:
        self.claim_retained_profits(
            expected_profit=contract_profit, sender=self.manager
        )

    def test_profit_split_when_manager_is_crazy(self):
        """Testing that withdraw failed when manager sets fee more than 100%"""

        # fee is too high:
        self.default_config.update({'providerProfitFee': 4_200_000})
        self._create_event()

        # Participant A: adding liquidity 50/50 just at start:
        self.provide_liquidity(
            participant=self.a,
            amount=50_000,
            expected_above_eq=1,
            expected_below=1,
        )

        # Participant B: bets below 50_000:
        self.bet(
            participant=self.b, amount=50_000, bet='below', minimal_win=75_000
        )

        self._run_measurement_and_close()
        # Bet aboveEq wins, B losses, A wins:
        a_wins = int(50_000 * (1 - 4.20))

        # Withdrawals:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.withdraw(self.a, 100_000 + a_wins)
        msg = 'Fee is more than 100%'
        self.assertTrue(msg in str(cm.exception))
