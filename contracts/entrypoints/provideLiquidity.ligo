function calculateSlippage(
    const ratio : nat;
    const expectedRatio : nat;
    const precision : nat) is
block {

    (* Slippage calculated in ratioPrecision values as multiplicative difference
        between bigger and smaller ratios: *)
    var slippage : nat := if expectedRatio > ratio
        then precision * expectedRatio / ratio;
        else precision * ratio / expectedRatio;

    (* At this point slippage is always >= store.ratioPrecision *)
    slippage := abs(slippage - precision);

} with slippage


function provideLiquidity(
    const params : provideLiquidityParams;
    var store : storage) : (list(operation) * storage) is
block {

    const expectedA : nat = params.expectedRatioAboveEq;
    const expectedB : nat = params.expectedRatioBelow;
    const precision : nat = store.ratioPrecision;

    const eventId : nat = params.eventId;
    var event : eventType := getEvent(store, eventId);
    const totalBets : tez = event.poolAboveEq + event.poolBelow;
    const key : ledgerKey = (Tezos.sender, eventId);
    const providedAmount : nat = tezToNat(Tezos.amount);
    const totalShares : nat = event.totalLiquidityShares;

    const isFirstLP : bool = totalBets = 0tez;
    const isNoShares : bool = totalShares = 0n;

    (* This check should never be true, but it better to have one: *)
    if isFirstLP =/= isNoShares then failwith("Wrong state") else skip;

    (* If pools are epmty, using expected pools provided in params: *)
    const poolA : nat = if isFirstLP
        then expectedA else tezToNat(event.poolAboveEq);
    const poolB : nat = if isFirstLP
        then expectedB else tezToNat(event.poolBelow);

    if ((expectedA = 0n) or (expectedB = 0n)) then
        failwith("Expected ratio in pool should be more than zero")
    else skip;

    if (Tezos.now > event.betsCloseTime) then
        failwith("Providing Liquidity after betCloseTime is not allowed")
    else skip;

    (* Calculating expected ratio using provided ratios: *)
    const expectedRatio : nat = expectedA * precision / expectedB;
    const ratio : nat = poolA * precision / poolB;

    const slippage : nat = calculateSlippage(ratio, expectedRatio, precision);
    if (slippage > params.maxSlippage) then
        failwith("Expected ratio very differs from current pool ratio")
    else skip;

    (* Increasing providers count if this participant is not provider yet: *)
    if isParticipant(store, key)
    then skip
    else event.participants := event.participants + 1n;

    (* Distributing liquidity: *)
    (* To cover all possible bets, it is enough for LP
        to fill only the largest pool, because only one pool loose in the end: *)
    const maxPool : nat = maxNat(poolA, poolB);

    const providedA : nat = roundDiv(providedAmount * poolA, maxPool);
    const providedB : nat = roundDiv(providedAmount * poolB, maxPool);

    if (providedA = 0n) or (providedB = 0n) then
        failwith("Zero liquidity provided")
    else skip;

    (* liquidity shares: *)
    (* - if this is first LP, newShares should be equal to sharePrecision *)
    (* - otherwise if this is not first LP, calculating share as the amount
        LP provided to maxPool amount: *)
    const newShares : nat = if isFirstLP then precision
        else providedAmount * totalShares / maxPool;

    if newShares = 0n then failwith("Added liquidity is less than one share")
    else skip;

    event.poolAboveEq := event.poolAboveEq + natToTez(providedA);
    event.poolBelow := event.poolBelow + natToTez(providedB);

    (* Total liquidity by this LP: *)
    store.providedLiquidityAboveEq[key] := 
        getLedgerAmount(key, store.providedLiquidityAboveEq) + natToTez(providedA);

    store.providedLiquidityBelow[key] := 
        getLedgerAmount(key, store.providedLiquidityBelow) + natToTez(providedB);

    store.depositedLiquidity[key] :=
        getLedgerAmount(key, store.depositedLiquidity) + natToTez(providedAmount);

    store.liquidityShares[key] :=
        getNatLedgerAmount(key, store.liquidityShares) + newShares;
    event.totalLiquidityShares := totalShares + newShares;

    store.events[eventId] := event;

} with ((nil: list(operation)), store)
