from juster_b import JusterB

def test_two_providers_and_one_insurance_simple_linear():
    jb = JusterB.new_with_deposit('A', 100, 100)
    jb.provide_liqudity('B', 50)
    jb.insure('C', 100, 'against')
    jb.give_reward(0)
    jb.remove_liqudity('B', 50)
    jb.remove_liqudity('A', 100)

    jb.assert_empty()

