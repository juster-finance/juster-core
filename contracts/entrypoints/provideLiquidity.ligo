function provideLiquidity(
    const params : provideLiquidityParams;
    var store : storage) : (list(operation) * storage) is
block {

    const expectedA : nat = params.expectedRatioAboveEq;
    const expectedB : nat = params.expectedRatioBellow;
    const precision : nat = store.ratioPrecision;

    const eventId : nat = params.eventId;
    const event : eventType = getEvent(store, eventId);
    const totalBets : tez = event.poolAboveEq + event.poolBellow;
    const key : ledgerKey = (Tezos.sender, eventId);
    const poolA : nat = tezToNat(event.poolAboveEq);
    const poolB : nat = tezToNat(event.poolBellow);
    const providedAmount : nat = tezToNat(Tezos.amount);
    const totalShares : nat = event.totalLiquidityShares;

    if ((expectedA = 0n) or (expectedB = 0n)) then
        failwith("Expected ratio in pool should be more than zero")
    else skip;

    if (Tezos.now > event.betsCloseTime) then
        failwith("Providing Liquidity after betCloseTime is not allowed")
    else skip;

    (* Calculating expected ratio using provided ratios: *)
    const expectedRatio : nat = expectedA * precision / expectedB;

    (* Calculating ratio. It is equal expected ratio if this is first LP: *)
    var ratio : nat := if totalBets =/= 0tez
        then poolA * precision / poolB
        else expectedRatio;

    (* Slippage calculated in ratioPrecision values as multiplicative difference
        between bigger and smaller ratios: *)
    var slippage : nat := if expectedRatio > ratio
        then precision * expectedRatio / ratio;
        else precision * ratio / expectedRatio;

    (* At this point slippage is always >= store.ratioPrecision *)
    slippage := abs(slippage - precision);

    if (slippage > params.maxSlippage) then
        failwith("Expected ratio very differs from current pool ratio")
    else skip;

    (* Increasing providers count if this participant is not provider yet: *)
    if isParticipant(store, key)
    then skip
    else event.participants := event.participants + 1n;

    (* Distributing liquidity: *)
    (* aboveEqShare is share in interval (0, store.ratioPrecision) calculated from
        current ratio, 1:1 ratio leads to 50% share, 3:1 leads to 75% share *)
    var aboveEqShare : nat := ratio * precision / (ratio + precision);
    const betA : nat = roundDiv(providedAmount * aboveEqShare, precision);
    const betB : nat = abs(providedAmount - betA);

    if (betA = 0n) or (betB = 0n) then
        failwith("Zero liquidity provided")
    else skip;

    (* liquidity shares: *)
    (* - if this is first LP, newShares should be equal to sharePrecision *)
    (* - otherwise if this is not first LP, calculating share using betAboveEq poolit
        it should not differ from added share to betBellow pool: *)
    const newShares : nat = if totalBets =/= 0tez
        then betA * totalShares / poolA
        else precision;

    if newShares = 0n then failwith("Added liquidity is less than one share")
    else skip;

    event.poolAboveEq := event.poolAboveEq + natToTez(betA);
    event.poolBellow := event.poolBellow + natToTez(betB);

    (* Total liquidity by this LP: *)
    store.providedLiquidityAboveEq[key] := 
        getLedgerAmount(key, store.providedLiquidityAboveEq) + natToTez(betA);

    store.providedLiquidityBellow[key] := 
        getLedgerAmount(key, store.providedLiquidityBellow) + natToTez(betB);

    store.liquidityShares[key] :=
        getNatLedgerAmount(key, store.liquidityShares) + newShares;
    event.totalLiquidityShares := totalShares + newShares;

    store.events[eventId] := event;

} with ((nil: list(operation)), store)
