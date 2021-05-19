function provideLiquidity(
    var params : provideLiquidityParams;
    var store : storage) : (list(operation) * storage) is
block {

    (* TODO: check that both expected ratio is > 0 *)

    if (Tezos.amount = 0tez) then
        failwith("Zero liquidity provided")
    else skip;

    const eventId : nat = params.eventId;
    const event : eventType = getEvent(store, eventId);
    const totalBets : tez = event.poolFor + event.poolAgainst;
    const key : ledgerKey = (Tezos.sender, eventId);

    if (Tezos.now > event.betsCloseTime) then
        failwith("Providing Liquidity after betCloseTime is not allowed")
    else skip;

    (* TODO: calculate expected ratio using provided ratios *)
    const expectedRatioSum : nat =
        params.expectedRatioFor + params.expectedRatioAgainst;
    const expectedRatio : nat =
        params.expectedRatioFor * store.ratioPrecision / expectedRatioSum;

    (* Calculating ratio. It is equal expected ratio if this is first LP: *)
    var ratio : nat := expectedRatio;
    (* And it is calculated if this is adding more liquidity scenario *)
    if totalBets =/= 0tez then
        ratio := event.poolFor * store.ratioPrecision / totalBets
    else skip;

    (* TODO: compare ratio and check p.maxSlippage is less than expected *)

    (* Distributing liquidity: *)
    const betFor : tez = natToTez(roundDiv(
        tezToNat(Tezos.amount * ratio), store.ratioPrecision));
    const betAgainst : tez = Tezos.amount - betFor;

    (* liquidity shares: *)
    (* if this is first LP, newShares should be equal to sharePrecision *)
    var newShares : nat := store.sharePrecision;
    (* otherwise if this is not first LP, calculating share using betFor poolit
        it should not differ from added share to betAgainst pool: *)
    if totalBets =/= 0tez then
        newShares := betFor * event.totalLiquidityShares / event.poolFor
    else skip;

    event.poolFor := event.poolFor + betFor;
    event.poolAgainst := event.poolAgainst + betAgainst;

    (* Calculating liquidity bonus: *)
    const totalBettingTime : nat = abs(event.betsCloseTime - event.createdTime);
    const elapsedTime : int = Tezos.now - event.createdTime;
    if (elapsedTime < 0) then
        failwith("Bet adding before contract createdTime (wrong createdTime?)")
    else skip;

    const remainedTime : int = totalBettingTime - elapsedTime;

    (* Total liquidity by this LP: *)
    store.providedLiquidityFor[key] := 
        getLedgerAmount(key, store.providedLiquidityFor) + betFor;

    store.providedLiquidityAgainst[key] := 
        getLedgerAmount(key, store.providedLiquidityAgainst) + betAgainst;

    (* Reducing share with time have passed: *)
    (* This time reduce scheme is not working with the current algorhytm
    newShares := newShares * abs(remainedTime) / totalBettingTime;
    *)

    store.liquidityShares[key] :=
        getNatLedgerAmount(key, store.liquidityShares) + newShares;
    event.totalLiquidityShares := event.totalLiquidityShares + newShares;

    store.events[eventId] := event;

} with ((nil: list(operation)), store)
