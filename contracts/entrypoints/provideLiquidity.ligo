function provideLiquidity(var p : provideLiquidityParams; var s : storage) : (list(operation) * storage) is
block {
    (* TODO: would it work properly if one LP adds liquidity twice? *)
    (* TODO: check that both expected ratio is > 0 *)
    (* TODO: assert that Sender.amount > 0 *)
    const eventId : eventIdType = p.eventId;
    const event : eventType = getEvent(s, eventId);
    const totalBets : tez = event.betsForLiquidityPoolSum + event.betsAgainstLiquidityPoolSum;
    const key : ledgerKey = (Tezos.sender, eventId);

    (* TODO: calculate expected ratio using provided ratios *)
    const expectedRatioSum : nat = p.expectedRatioFor + p.expectedRatioAgainst;
    const expectedRatio : nat = p.expectedRatioFor * event.ratioPrecision / expectedRatioSum;

    var ratio : nat := expectedRatio;
    if totalBets = 0tez then
        (* Adding first liquidity scenario *)
        skip;
    else
    block {
        (* Adding more liquidity scenario *)
        const ratioSum : tez = event.betsForLiquidityPoolSum + event.betsAgainstLiquidityPoolSum;
        ratio := event.betsForLiquidityPoolSum * event.ratioPrecision / ratioSum;
    };
    (* TODO: compare ratio and check p.maxSlippage is less than expected *)

    (* Distributing liquidity: *)
    const betFor : tez = natToTez(roundDiv(tezToNat(Tezos.amount * ratio), event.ratioPrecision));
    const betAgainst : tez = Tezos.amount - betFor;
    event.betsForLiquidityPoolSum := event.betsForLiquidityPoolSum + betFor;
    event.betsAgainstLiquidityPoolSum := event.betsAgainstLiquidityPoolSum + betAgainst;

    (* Calculating liquidity bonus: *)
    const totalBettingTime : nat = abs(event.betsCloseTime - event.createdTime);
    const elapsedTime : int = Tezos.now - event.createdTime;
    if (elapsedTime < 0) then
        failwith("Bet adding before contract createdTime (possible wrong createdTime?)")
    else skip;

    const remainedTime : int = totalBettingTime - elapsedTime;

    (* Total liquidity by this LP: *)
    const alreadyProvided : tez = getLedgerAmount(key, s.providedLiquidityLedger);
    const newAmount : tez = alreadyProvided + betAgainst + betFor;
    s.providedLiquidityLedger[key] := newAmount;

    (* liquidity For shares: *)
    const liquidityForShares : tez = abs(remainedTime) * betFor / totalBettingTime;
    const newAmount : tez = getLedgerAmount(key, s.liquidityForSharesLedger) + liquidityForShares;
    s.liquidityForSharesLedger[key] := newAmount;
    event.totalLiquidityForSharesSum := event.totalLiquidityForSharesSum + liquidityForShares;

    (* liquidity Against shares: *)
    const liquidityAgainstShares : tez = abs(remainedTime) * betAgainst / totalBettingTime;
    const newAmount : tez = getLedgerAmount(key, s.liquidityAgainstSharesLedger) + liquidityAgainstShares;
    s.liquidityAgainstSharesLedger[key] := newAmount;
    event.totalLiquidityAgainstSharesSum := event.totalLiquidityAgainstSharesSum + liquidityAgainstShares;

    (* Recording forProfitDiff and againstProfitDiff that would allow to
        exclude any profits / losses that was made before this new liquidity and fairly
        distribute new profits / losses: *)
    const newAgainstShares : int = int(liquidityAgainstShares / 1mutez);
    const newForShares : int = int(liquidityForShares / 1mutez);
    const precision : int = int(event.sharePrecision);

    const forProfitDiff : int = event.winForProfitLossPerShare * newAgainstShares / precision;
    s.forProfitDiff[key] := getDiffLedgerAmount(key, s.forProfitDiff) + forProfitDiff;

    const againstProfitDiff : int = event.winAgainstProfitLossPerShare * newForShares / precision;
    s.againstProfitDiff[key] := getDiffLedgerAmount(key, s.againstProfitDiff) + againstProfitDiff;

    s.events[eventId] := event;

} with ((nil: list(operation)), s)
