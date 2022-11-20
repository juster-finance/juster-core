# Juster pool:
    - TODO: describe all entrypoints, storage and calculations

# liquidity types:
    - withdrawable liquidity: is amount of liquidity that cannot be used
        in any future events but it is still included in balance

    - working/total liquidity:
        - is amount of liquidity that valuated and used in (can be spent on)
            events, consists of active liquidity and free liquidity

        - is amount of all liquidity controlled by contract
            consists of active liquidity and free liquidity. Total liquidity
            used to calculate amount of liquidity that expected to be provided
            to the next event. Total liquidity used in share valuation.

    - entry liquidity: is amount of newly added liquidity that not valuated
        yet and not associated with pool shares yet

    - free liquidity: is amount of liquidity that not locked in events and
        that already valuated. This liquidity can be withdrawn on claim call

    - active liquidity: is amount of liquidity locked in active events,
        valuated by provided amount
