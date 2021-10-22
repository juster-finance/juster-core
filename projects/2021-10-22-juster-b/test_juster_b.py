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

