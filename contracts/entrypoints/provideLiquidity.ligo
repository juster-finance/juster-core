function provideLiquidity(
    var p : provideLiquidityParams;
    var s : storage) : (list(operation) * storage) is
block {
    (* TODO: would it work properly if one LP adds liquidity twice? *)
    (* TODO: check that both expected ratio is > 0 *)
    (* TODO: assert that Sender.amount > 0 *)
    const eventId : eventIdType = p.eventId;
    const event : eventType = getEvent(s, eventId);
    const totalBets : tez = event.poolFor + event.poolAgainst;
    const key : ledgerKey = (Tezos.sender, eventId);

    (* TODO: calculate expected ratio using provided ratios *)
    const expectedRatioSum : nat = p.expectedRatioFor + p.expectedRatioAgainst;
    const expectedRatio : nat =
        p.expectedRatioFor * event.ratioPrecision / expectedRatioSum;

    var ratio : nat := expectedRatio;
    if totalBets = 0tez then
        (* Adding first liquidity scenario *)
        skip;
    else
    block {
        (* Adding more liquidity scenario *)
        const ratioSum : tez = event.poolFor + event.poolAgainst;
        ratio := event.poolFor * event.ratioPrecision / ratioSum;
    };
    (* TODO: compare ratio and check p.maxSlippage is less than expected *)

    (* Distributing liquidity: *)
    const betFor : tez = natToTez(roundDiv(
        tezToNat(Tezos.amount * ratio), event.ratioPrecision));
    const betAgainst : tez = Tezos.amount - betFor;
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
    const alreadyProvided : tez = getLedgerAmount(key, s.providedLiquidity);
    s.providedLiquidity[key] := alreadyProvided + betAgainst + betFor;

    (* liquidity For shares: *)
    const liquidityForShares : tez =
        abs(remainedTime) * betFor / totalBettingTime;
    s.liquidityForShares[key] :=
        getLedgerAmount(key, s.liquidityForShares) + liquidityForShares;
    event.totalLiquidityForShares :=
        event.totalLiquidityForShares + liquidityForShares;

    (* liquidity Against shares: *)
    const liquidityAgainstShares : tez =
        abs(remainedTime) * betAgainst / totalBettingTime;
    s.liquidityAgainstShares[key] :=
        getLedgerAmount(key, s.liquidityAgainstShares) + liquidityAgainstShares;
    event.totalLiquidityAgainstShares :=
        event.totalLiquidityAgainstShares + liquidityAgainstShares;

    (* Recording forProfitDiff and againstProfitDiff that would allow to
        exclude any profits / losses that was made before this new liquidity
        and fairly distribute new profits / losses: *)
    const newAgainstShares : int = int(liquidityAgainstShares / 1mutez);
    const newForShares : int = int(liquidityForShares / 1mutez);
    const precision : int = int(event.sharePrecision);

    const forProfitDiff : int =
        event.forProfit * newAgainstShares / precision;
    s.forProfitDiff[key] :=
        getDiffLedgerAmount(key, s.forProfitDiff) + forProfitDiff;

    const againstProfitDiff : int =
        event.againstProfit * newForShares / precision;
    s.againstProfitDiff[key] :=
        getDiffLedgerAmount(key, s.againstProfitDiff) + againstProfitDiff;

    s.events[eventId] := event;

} with ((nil: list(operation)), s)
