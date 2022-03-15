function calcFreeLiquidity(const store : storage) : int is
    Tezos.balance/1mutez
    - store.withdrawableLiquidity
    - store.entryLiquidity

function checkIsEnoughLiquidity(const store : storage) : unit is
    if calcFreeLiquidity(store) < int(store.nextEventLiquidity)
    then failwith(PoolErrors.noLiquidity)
    else unit;

function calcLiquidityPayout(const store : storage) : tez is
    block {
        checkIsEnoughLiquidity(store);

        var liquidityAmount := store.nextEventLiquidity - store.newEventFee/1mutez;

        if liquidityAmount <= 0
        then failwith(PoolErrors.noLiquidity)
        else skip;

    } with abs(liquidityAmount) * 1mutez

