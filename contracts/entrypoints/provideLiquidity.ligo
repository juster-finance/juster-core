function provideLiquidity(
    var p : provideLiquidityParams;
    var s : storage) : (list(operation) * storage) is
block {
    (* TODO: would it work properly if one LP adds liquidity twice? *)
    (* TODO: check that both expected ratio is > 0 *)
    (* TODO: assert that Sender.amount > 0 *)
    const eventId : nat = p.eventId;
    const event : eventType = getEvent(s, eventId);
    const totalBets : tez = event.poolFor + event.poolAgainst;
    const key : ledgerKey = (Tezos.sender, eventId);

    (* TODO: calculate expected ratio using provided ratios *)
    const expectedRatioSum : nat = p.expectedRatioFor + p.expectedRatioAgainst;
    const expectedRatio : nat =
        p.expectedRatioFor * event.ratioPrecision / expectedRatioSum;

    (* Calculating ratio. It is equal expected ratio if this is first LP: *)
    var ratio : nat := expectedRatio;
    (* And it is calculated if this is adding more liquidity scenario *)
    if totalBets =/= 0tez then
        ratio := event.poolFor * event.ratioPrecision / totalBets
    else skip;

    (* TODO: compare ratio and check p.maxSlippage is less than expected *)

    (* Distributing liquidity: *)
    const betFor : tez = natToTez(roundDiv(
        tezToNat(Tezos.amount * ratio), event.ratioPrecision));
    const betAgainst : tez = Tezos.amount - betFor;

    (* liquidity shares: *)
    (* if this is first LP, newShares should be equal to sharePrecision *)
    var newShares : nat := event.sharePrecision;
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
    const providedFor : tez = getLedgerAmount(key, s.providedLiquidityFor);
    s.providedLiquidityFor[key] := providedFor + betFor;

    const providedAgainst : tez = getLedgerAmount(key, s.providedLiquidityAgainst);
    s.providedLiquidityAgainst[key] := providedAgainst + betAgainst;

    (* Reducing share with time have passed: *)
    (* This time reduce scheme is not working with the current algorhytm
    newShares := newShares * abs(remainedTime) / totalBettingTime;
    *)

    s.liquidityShares[key] :=
        getNatLedgerAmount(key, s.liquidityShares) + newShares;
    event.totalLiquidityShares := event.totalLiquidityShares + newShares;

    s.events[eventId] := event;

} with ((nil: list(operation)), s)
