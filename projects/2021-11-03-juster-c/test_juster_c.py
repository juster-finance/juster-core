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

    # TODO: need to understand how this earned value can be distributed amount providers
    # a) special `profit` variable that providers can withdraw when he apply to lock
    #    (calculating difference between profit at the moment provider get into and
    #    the moment he withdraws liquidity?)

    # b) the better way for liquidity is to redistribute it to the pools according
    #    to the current ratio. But how to track then how much providers earned?
    #    maybe some kind of inflation ratio?

    # MAYBE: to have some coefficient to split profits and part of the profits
    # should go to providers and another part should go directly to the AGAINST pool?
    # and idk maybe this coef can be equal to the current ratio?

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

    insurance = jc.insure('D', 10)
    jc.wait(100)
    jc.dissolve(insurance)

    jc.provide('B', amount_for=20, amount_against=150)
    lock_a_1 = jc.lock('A', 5, 45)

    insurance = jc.insure('E', 10)
    jc.wait(100)
    jc.dissolve(insurance)
    jc.withdraw(lock_a_1)

    jc.provide('C', amount_for=10, amount_against=120)
    lock_a_2 = jc.lock('A', 5, 45)

    insurance = jc.insure('E', 10)
    jc.wait(25)
    jc.claim_insurance_case()

    jc.withdraw(lock_a_2)
    jc.reward(insurance)

    lock_b = jc.lock('B', 20, 150)
    lock_c = jc.lock('C', 10, 120)
    jc.withdraw(lock_b)
    jc.withdraw(lock_c)

    jc.assert_empty()

# TODO: test where providers have very different ratios, one with 10:1, one 1:1 and one 1:10
# TODO: test where providers have lock with different ratios

