from juster_b import JusterB
from pools import Pools


def test_two_providers_and_one_insurance_simple_linear():
    jb = JusterB.new_with_deposit('A', 100, 100)
    jb.provide_liquidity('B', 50)

    # C puts against with ratio 150/250 = 0.6 and wins 60
    lock = jb.insure('C', 100, 'against')
    jb.give_reward(lock)

    # A and B split losses: A: -40, B: -20
    lock = jb.lock_liquidity('B', 50)
    jb.withdraw_lock(lock)
    lock = jb.lock_liquidity('A', 100)
    jb.withdraw_lock(lock)

    jb.assert_balances_equal({
        'A': -40,
        'B': -20,
        'C': 60
    })
    jb.assert_empty()


def test_two_providers_and_one_insurance_simple_linear_but_C_lose():
    jb = JusterB.new_with_deposit('A', 100, 100)
    jb.provide_liquidity('B', 50)

    # C puts for and looses all 90:
    jb.insure('C', 90, 'for')
    jb.give_reward(0)

    # A and B split profits: A: +60, B: +30
    lock = jb.lock_liquidity('B', 50)
    jb.withdraw_lock(lock)
    lock = jb.lock_liquidity('A', 100)
    jb.withdraw_lock(lock)

    jb.assert_balances_equal({
        'A': 60,
        'B': 30,
        'C': -90
    })
    jb.assert_empty()


def test_some_liquidity_removed_and_then_some_bet_placed():
    jb = JusterB.new_with_deposit('A', 100, 100)
    jb.assert_balances_equal({'A': -100})

    # C wins 100/200*100 = 50 from A, because insurance case is not claimed
    insurance_one = jb.insure('C', 100, 'against')
    assert jb.pools == Pools(50, 200)

    # Taking reward returns pools to the initial value
    # but total liquidity amount reduces by agreement.delta:
    jb.give_reward(insurance_one)
    assert jb.pools == Pools(50, 200)

    # A withdraws liquidity and no one interacts while it is locked:
    lock = jb.lock_liquidity('A', 40)
    jb.withdraw_lock(lock)
    assert jb.total_shares == 60
    assert jb.pools == Pools(30, 120)

    # A returns 40% of deposit: 40 and accepts 40% of the losses (-20)
    jb.assert_balances_equal({'A': -100 + 40 - 20})

    # C makes another win with 30/150*30 = 6
    insurance_two = jb.insure('C', 30, 'against')

    # This time A withdraws first:
    lock = jb.lock_liquidity('A', 60)
    jb.withdraw_lock(lock)
    assert jb.total_shares == 0
    assert jb.pools == Pools(0, 0)

    # Then withdraws C:
    jb.give_reward(insurance_two)
    assert jb.pools == Pools(0, 0)

    jb.assert_balances_equal({
        'A': -56,
        'C': 56
    })
    jb.assert_empty()


def test_where_pools_turn_over():
    jb = JusterB.new_with_deposit('A', 1, 2)

    # B loses 1 for provider A:
    insurance_one = jb.insure('B', 1, 'for')
    assert jb.pools == Pools(2, 1)

    # A provides 100% more liquidity with opposite pools:
    jb.provide_liquidity('A', 2)
    assert jb.pools == Pools(4, 2)

    jb.give_reward(insurance_one)
    assert jb.pools == Pools(4, 2)

    lock = jb.lock_liquidity('A', 4)
    jb.withdraw_lock(lock)
    jb.assert_balances_equal({
        'A': +1,
        'B': -1,
    })
    jb.assert_empty()


def test_with_succeeded_insurance_claim():
    jb = JusterB.new_with_deposit('A', 1000, 1000)
    insurance_one = jb.insure('B', 10, 'for')
    jb.claim_insurance_case()
    lock = jb.lock_liquidity('A', 1000)
    jb.withdraw_lock(lock)
    jb.give_reward(insurance_one)
    jb.assert_empty()


def test_where_provider_exploits_insurance_case():
    jb = JusterB.new_with_deposit('A', 1000, 1000)
    insurance_one = jb.insure('B', 10, 'for')
    lock = jb.lock_liquidity('A', 1000)
    # in reality withdraw_lock should not be possible before the next claim:
    jb.withdraw_lock(lock)
    jb.claim_insurance_case()
    jb.give_reward(insurance_one)

    # because both A and B "wins" - there are divergent balance:
    assert sum(jb.balances.values()) > 1


def test_insurance_after_lock_affect_provider():
    jb = JusterB.new_with_deposit('A', 1000, 1000)
    insurance_one = jb.insure('B', 1000, 'for')
    lock = jb.lock_liquidity('A', 1000)
    jb.claim_insurance_case()
    jb.give_reward(insurance_one)
    jb.withdraw_lock(lock)
    jb.assert_empty()

    assert jb.balances['A'] == -500


def test_where_negative_pool_arised_when_give_reward_after_lock():
    jb = JusterB.new_with_deposit('A', 1000, 1000)
    insurance_one = jb.insure('B', 1000, 'for')
    lock = jb.lock_liquidity('A', 1000)
    jb.claim_insurance_case()
    jb.give_reward(insurance_one)
    jb.withdraw_lock(lock)
    jb.assert_empty()


def test_case_when_provider_first_wins_and_then_loses_within_same_pool():
    jb = JusterB.new_with_deposit('A', 1000, 1000)
    insurance_one = jb.insure('B', 1000, 'for')
    jb.give_reward(insurance_one)

    insurance_two = jb.insure('C', 2000, 'for')
    lock = jb.lock_liquidity('A', 1000)
    jb.claim_insurance_case()
    jb.give_reward(insurance_two)
    jb.withdraw_lock(lock)


def test_case_with_insurance_case_while_partial_liquidity_lock():
    # A deposits equally 1000:1000
    jb = JusterB.new_with_deposit('A', 1000, 1000)

    # B get insurance (and then wins, during A liquidity lock):
    insurance_one = jb.insure('B', 1000, 'for')
    assert jb.pools == Pools(2000, 500)

    # A tries to remove liquidity, but this liquidity would be required to pay B:
    lock_one = jb.lock_liquidity('A', 500)
    assert jb.pools == Pools(1000, 250)

    # C get insurance with possible win 800 (=1000/1250*1000) but lose:
    # it is important that he used only active liquidity
    insurance_two = jb.insure('C', 1000, 'against')
    assert jb.pools == Pools(200, 1250)

    jb.claim_insurance_case()

    jb.give_reward(insurance_one)
    jb.give_reward(insurance_two)

    # First lock: A should pay B 50% of 500 and get 50% of 1000 deposit:
    # -1000 - 500/2 + 1000/2 = -750
    jb.withdraw_lock(lock_one)
    jb.assert_balances_equal({'A': -750})

    lock_two = jb.lock_liquidity('A', 500)
    # A should pay B 50% of 500 and get from C the whole 1000 + 50% of 1000 deposit:
    # -750 - 500/2 + 1000/2 + 1000 = +500
    jb.withdraw_lock(lock_two)
    jb.assert_balances_equal({'A': 500})

    jb.assert_empty()


'''
def test_case_where_one_wins_with_against_and_then_other_wins_with_for():
    jb = JusterB.new_with_deposit('A', 100, 100)
    insurance_one = jb.insure('B', 9900, 'against')

    assert jb.pools == Pools(1, 10000)
    jb.give_reward(insurance_one)

    # Pools should be reduced here, but there are no such kind of logic in model yet:
    # assert jb.pools == Pools(0.01, 100)

    insurance_two = jb.insure('C', 1, 'for')

    # at the moment jb.pools == Pools(2, 5000) and this is wrong
    # either jb.pools == Pools(1.01, ??)
    # either there should be some kind of pool inflation multiplier used

    jb.claim_insurance_case()
    jb.give_reward(insurance_two)

    lock = jb.lock_liquidity('A', 100)
    jb.withdraw_lock(lock)
    jb.assert_empty()
'''

