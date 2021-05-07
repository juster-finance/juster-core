### List of collected TODO's that not distributed for future tests:
- TODO: test that LP can withdraw instead of participant after some time
        * test that LP can't withdraw instead of participant before this time
- TODO: make some tests inside sandbox
- TODO: test Force Majeure:
    - event 1: measurement not started in the window time, check that withdrawals are succesfull
    - event 2: close is not started in the window time
    - event 3: no bets provided ? or this is normal ?


""" EDGECASE 1 test, different zero-cases:
    - event created
    - A provides liquidity with 0 tez, assert failed
    - A tries to bet but there are no liquidity, so assert MichelsonError
    - B provides liquidity
    - A provides liquidity with 0 tez, assert failed again
    - A tries to adding liquidity with rate that very different from internal rate

    - A tries to Bet with winRate a lot more than expected (assert MichelsonError raises)

    - in the end: no one bets, measure
    - TODO: test that adding liquidity after bets time is not allowed

    - close, B withdraws all
        TODO: check contract balance is 0
        TODO: check B withdraws all the sum invested

    - TODO: test trying close twice: assert failed
    - TODO: test trying to bet after close is failed
    - TODO: test trying to call measurement after close is failed
"""


""" MULTIEVENT test and MODELS EQUAL:
    - event 1 created
    - PARALLEL: B provides liquidity [x3 1 tez]

    - event 2 created
    - PARALLEL: B provides liquidity [x1 3 tez]
        TODO: check that ratios in event 1 and 2 are the same

    - no one bets, measure, close, B withdraws all in both events
        TODO: check balance is ok
        TODO: check value the same 

    - event created 3
    - A provides liquidity with 3:1 rate
    - PARALLEL: B bets three times for 1 tez

    - event created 4
    - A provides liquidity with 3:1 rate
    - PARALLEL: B bets one time for 3 tez
    TODO: check that ratios in event 3 & 4 the same
    - finishing event 3, 4, withdrawing
        - check balance account is zero
    - event 3 B loosed, check that zero operation in withdraw is succeed
    - event 3 B wins

    - TODO: check that all ledgers and event records is cleaned at close
"""

