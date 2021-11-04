# Idea where against pool is merged with providers
# Each provider decides what ratio he provides, participants communicate with
# aggregated pools:

# So then resultat of event line is always one:
# - either ones who insured wins and then they withdraws their deltas and providers split 'for' pool
# - either no insurance case when provider withdraws, so he splits 'against' pool
# it is impossible to win during event, only one point where all insurance wins and all providers loose is the end
# when provider get into, he adds some shares based on max pool (?)
# when provider leaves he splits based on 'against' pool if no insurance claimed and 'for' if there was claim

# pool ratio used to calculate insurance deltas, pool works the same way it works in Juster

import pytest
from pools import Pools
from juster_c import JusterC


def test_model_with_providers_merged_with_against_pool():
    jc = JusterC(duration=100)

    # Three providers are participated in the event:
    jc.provide('A', amount_for=10, amount_against=100)  # ratio 0.10
    jc.provide('B', amount_for=20, amount_against=140)  # ratio 0.14
    jc.provide('C', amount_for=10, amount_against=120)  # ratio 0.08

    # Provider B supposes that insurance claim chances are higher than provider C
    # so if claim occurs, provider C should have less loss impact
    # and if it is not, provider C should have less profit

    insurance = jc.insure('D', 4)
    jc.wait(100)
    jc.dissolve(insurance)

    insurance = jc.insure('E', 10)
    jc.wait(25)
    jc.claim_insurance_case()
    jc.reward(insurance)

    # TODO: should unproportional withdrawals be allowed?
    # for example: lock_a = jc.lock('A', 10, 30) ?

    lock_a = jc.lock('A', 10, 100)
    lock_b = jc.lock('B', 20, 140)
    lock_c = jc.lock('C', 10, 120)
    jc.withdraw(lock_a)
    jc.withdraw(lock_b)
    jc.withdraw(lock_c)

    jc.assert_empty()


def test_when_provider_get_into_and_get_out_during_event():
    jc = JusterC(duration=100)
    jc.provide('A', amount_for=10, amount_against=90)

    # D aggreed for insurance and no claim raised during his agreement:
    insurance = jc.insure('D', 10)
    jc.wait(100)
    jc.dissolve(insurance)

    # B decided to add liquidity too:
    jc.provide('B', amount_for=20, amount_against=150)

    # A removes some liquidity but keeping FOR pool (non symetrical case):
    lock_a_1 = jc.lock('A', 0, 30)

    # E get insurance and no claim raised:
    insurance = jc.insure('E', 10)
    jc.wait(100)
    jc.dissolve(insurance)

    # A withdraws locked liquidity after `duration` period:
    jc.withdraw(lock_a_1)

    # C decided to add liquidity too:
    jc.provide('C', amount_for=10, amount_against=120)

    # A locks the rest of the liquidity:
    lock_a_2 = jc.lock('A', 10, 60)

    # E applies for insurance and claim arised:
    insurance = jc.insure('E', 10)
    jc.wait(25)
    jc.claim_insurance_case()

    # A withdraws his 10:60 using LOSE PROVIDER scenario:
    jc.withdraw(lock_a_2)

    # C get reward for the claimed insurance:
    jc.reward(insurance)

    # Other providers withdraw their liquidity too:
    lock_b = jc.lock('B', 20, 150)
    lock_c = jc.lock('C', 10, 120)
    jc.withdraw(lock_b)
    jc.withdraw(lock_c)

    jc.assert_empty()


def test_where_providers_have_very_different_ratios_win_case():
    jc = JusterC(duration=100)

    # Three providers are participated in the event:
    jc.provide('A', amount_for=4,  amount_against=48)  # ratio  0.083
    jc.provide('B', amount_for=48, amount_against=48)  # ratio  1.000
    jc.provide('C', amount_for=48, amount_against=4)   # ratio 12.000
    assert jc.pools == Pools(100, 100)

    # D insures for really big amount and moved pools 100:50
    insurance = jc.insure('D', 100)
    assert jc.pools == Pools(100, 50)

    jc.wait(100)
    jc.dissolve(insurance)

    # Providers win case:
    lock_a = jc.lock('A',  4, 48)
    lock_b = jc.lock('B', 48, 48)
    lock_c = jc.lock('C', 48,  4)
    jc.withdraw(lock_a)
    jc.withdraw(lock_b)
    jc.withdraw(lock_c)

    # Providers splitting 100 from D by AGAINST pool
    # profit distributed proportional to the provided liquidity, ratio does not
    # matter (is it good property or not?):
    jc.assert_balances_equal({
        'A': (48 +  4) / 200 * 100,
        'B': (48 + 48) / 200 * 100,
        'C': ( 4 + 48) / 200 * 100
    })

    jc.assert_empty()


def test_where_providers_have_very_different_ratios_lose_case():
    jc = JusterC(duration=100)

    # Three providers are participated in the event:
    jc.provide('A', amount_for=4,  amount_against=48)  # ratio  0.083
    jc.provide('B', amount_for=48, amount_against=48)  # ratio  1.000
    jc.provide('C', amount_for=48, amount_against=4)   # ratio 12.000
    assert jc.pools == Pools(100, 100)

    # D insures for really big amount and moved pools 100:50
    insurance = jc.insure('D', 100)
    assert jc.pools == Pools(100, 50)

    jc.wait(12)
    jc.claim_insurance_case()
    jc.reward(insurance)

    # Providers lose case:
    lock_a = jc.lock('A',  4, 48)
    lock_b = jc.lock('B', 48, 48)
    lock_c = jc.lock('C', 48,  4)
    jc.withdraw(lock_a)
    jc.withdraw(lock_b)
    jc.withdraw(lock_c)

    # Wow wow wow, looks like C in profit here? wtf
    # so then, does it mean that provider should just add all liquidity to FOR pool?
    # ^^ need to test that clearly exploit this

    # Simplified profit formula: splitted AGAINST pool - provided AGAINST
    jc.assert_balances_equal({
        'A': 0.04 * 50 - 48,
        'B': 0.48 * 50 - 48,
        'C': 0.48 * 50 - 4
    })

    jc.assert_empty()


def test_provider_puts_alot_in_for_to_exploit_the_system():

    def scenario(case='win'):
        jc = JusterC(duration=100)

        # Three providers are participated in the event:
        jc.provide('A', amount_for=50,  amount_against=50)
        jc.provide('B', amount_for=150, amount_against=0)
        assert jc.pools == Pools(200, 50)

        insurance = jc.insure('C', 50)
        assert jc.pools == Pools(200, 40)

        if case == 'win':
            jc.wait(100)
            jc.dissolve(insurance)
        else:
            jc.claim_insurance_case()
            jc.reward(insurance)

        lock_a = jc.lock('A', 50, 50)
        lock_b = jc.lock('B', 150, 0)
        jc.withdraw(lock_a)
        jc.withdraw(lock_b)
        return jc

    # B have very good result here in both cases:
    scenario('win').assert_balances_equal({
        'A': 100 / 250 * 50,
        'B': 150 / 250 * 50
    })

    scenario('lose').assert_balances_equal({
        'A': 50 / 200 * 40 - 50,
        'B': 150 / 200 * 40 - 0
    })


# TODO: test where providers have lock with different ratios

