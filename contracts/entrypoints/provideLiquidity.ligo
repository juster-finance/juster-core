function provideLiquidity(
    var params : provideLiquidityParams;
    var store : storage) : (list(operation) * storage) is
block {

    if ((params.expectedRatioBellow = 0n)
        or (params.expectedRatioAboveEq = 0n)) then
            failwith("Expected ratio in pool should be more than zero")
    else skip;

    if (Tezos.amount = 0tez) then
        failwith("Zero liquidity provided")
    else skip;

    const eventId : nat = params.eventId;
    const event : eventType = getEvent(store, eventId);
    const totalBets : tez = event.poolAboveEq + event.poolBellow;
    const key : ledgerKey = (Tezos.sender, eventId);

    if (Tezos.now > event.betsCloseTime) then
        failwith("Providing Liquidity after betCloseTime is not allowed")
    else skip;

    (* Calculating expected ratio using provided ratios: *)
    const expectedRatio : nat =
        params.expectedRatioAboveEq * store.ratioPrecision
        / params.expectedRatioBellow;

    (* Calculating ratio. It is equal expected ratio if this is first LP: *)
    var ratio : nat := expectedRatio;
    (* And it is calculated if this is adding more liquidity scenario *)
    if totalBets =/= 0tez then
        ratio := event.poolAboveEq * store.ratioPrecision / event.poolBellow
    else skip;

    (* Slippage calculated in ratioPrecision values as multiplicative difference
        between bigger and smaller ratios: *)
    var slippage : nat := store.ratioPrecision * ratio / expectedRatio;
    if expectedRatio > ratio then
        slippage := store.ratioPrecision * expectedRatio / ratio;
    else skip;

    (* At this point slippage is always >= store.ratioPrecision *)
    slippage := abs(slippage - store.ratioPrecision);

    if (slippage > params.maxSlippage) then
        failwith("Expected ratio very differs from current pool ratio")
    else skip;

    (* Distributing liquidity: *)
    (* aboveEqShare is share in interval (0, store.ratioPrecision) calculated from
        current ratio, 1:1 ratio leads to 50% share, 3:1 leads to 75% share *)
    var aboveEqShare : nat :=
        ratio * store.ratioPrecision / (ratio + store.ratioPrecision);
    const betAboveEq : tez = natToTez(roundDiv(
        tezToNat(Tezos.amount * aboveEqShare), store.ratioPrecision));
    const betBellow : tez = Tezos.amount - betAboveEq;

    (* liquidity shares: *)
    (* if this is first LP, newShares should be equal to sharePrecision *)
    var newShares : nat := store.sharePrecision;
    (* otherwise if this is not first LP, calculating share using betAboveEq poolit
        it should not differ from added share to betBellow pool: *)
    if totalBets =/= 0tez then
        newShares := betAboveEq * event.totalLiquidityShares / event.poolAboveEq
    else skip;

    event.poolAboveEq := event.poolAboveEq + betAboveEq;
    event.poolBellow := event.poolBellow + betBellow;

    (* Total liquidity by this LP: *)
    store.providedLiquidityAboveEq[key] := 
        getLedgerAmount(key, store.providedLiquidityAboveEq) + betAboveEq;

    store.providedLiquidityBellow[key] := 
        getLedgerAmount(key, store.providedLiquidityBellow) + betBellow;

    store.liquidityShares[key] :=
        getNatLedgerAmount(key, store.liquidityShares) + newShares;
    event.totalLiquidityShares := event.totalLiquidityShares + newShares;

    store.events[eventId] := event;

} with ((nil: list(operation)), store)
