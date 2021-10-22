from juster_b import JusterB

def test_two_providers_and_one_insurance_simple_linear():
    jb = JusterB.new_with_deposit('A', 100, 100)
    jb.provide_liquidity('B', 50)
    jb.insure('C', 100, 'against')
    jb.give_reward(0)
    jb.remove_liquidity('B', 50)
    jb.remove_liquidity('A', 100)

    jb.assert_empty()


def test_two_providers_and_one_insurance_simple_linear_but_C_lose():
    jb = JusterB.new_with_deposit('A', 100, 100)
    jb.provide_liquidity('B', 50)
    jb.insure('C', 100, 'for')
    jb.give_reward(0)
    jb.remove_liquidity('B', 50)
    jb.remove_liquidity('A', 100)

    jb.assert_empty()


def test_some_liquidity_removed_and_then_some_bet_placed():
    jb = JusterB.new_with_deposit('A', 100, 100)
    insurance_one = jb.insure('C', 100, 'against')
    jb.give_reward(insurance_one)
    jb.remove_liquidity('A', 50)
    insurance_two = jb.insure('C', 25, 'against')
    jb.remove_liquidity('A', 50)
    jb.give_reward(insurance_two)
    jb.assert_empty()


def test_where_pools_turn_over():
    jb = JusterB.new_with_deposit('A', 1, 2)
    insurance_one = jb.insure('B', 1, 'for')
    jb.provide_liquidity('A', 2)
    jb.give_reward(insurance_one)
    insurance_two = jb.insure('C', 4, 'against')
    jb.remove_liquidity('A', 4)
    jb.give_reward(insurance_two)
    jb.assert_empty()


def test_with_succeeded_insurance_claim():
    jb = JusterB.new_with_deposit('A', 1000, 1000)
    insurance_one = jb.insure('B', 10, 'for')
    jb.claim_insurance_case()
    jb.remove_liquidity('A', 1000)
    jb.give_reward(insurance_one)
    jb.assert_empty()


def test_where_provider_exploits_insurance_case():
    jb = JusterB.new_with_deposit('A', 1000, 1000)
    insurance_one = jb.insure('B', 10, 'for')
    jb.remove_liquidity('A', 1000)
    jb.claim_insurance_case()
    jb.give_reward(insurance_one)

    # because both A and B "wins" - there are divergent balance:
    assert sum(jb.balances.values()) > 10

    # This is why it is required to implement SHARE LOCK (or another mechanics)

