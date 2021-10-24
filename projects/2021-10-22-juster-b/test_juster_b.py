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
    assert jb.pools == Pools(50, 50)

    # A withdraws liquidity and no one interacts while it is locked:
    lock = jb.lock_liquidity('A', 40)
    jb.withdraw_lock(lock)
    assert jb.total_shares == 60
    assert jb.pools == Pools(30, 30)
    # A returns 40% of deposit: 40 and accepts 40% of the losses (-20)
    # TODO: ^^ is this logic correct? Maybe he accepts 100% of the losses?
    jb.assert_balances_equal({'A': -100 + 40 - 20})

    # C makes another win with 30/60*30 = 15
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
        'A': -65,
        'C': 65
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

    # B return pools to the balance (3:3) and adds his losed 1 on the top:
    jb.give_reward(insurance_one)
    assert jb.pools == Pools(4, 4)

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


# def test_case_where_part_of_liquidity_withdrawn_and_then_
