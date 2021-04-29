function provideLiquidity(var p : provideLiquidityParams; var s : storage) : storage is
block {
    (* TODO: check that both expected ratio is > 0 *)
    (* TODO: assert that Sender.amount > 0 *)
    const eventId : eventIdType = p.eventId;
    const event : eventType = getEvent(s, eventId);
    const totalBets : tez = event.betsForSum + event.betsAgainstSum;
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
        const ratioSum : tez = event.betsForSum + event.betsAgainstSum;
        ratio := event.betsForSum * event.ratioPrecision / ratioSum;
    };
    (* TODO: compare ratio and check p.maxSlippage is less than expected *)

    (* Distributing liquidity: *)
    (* TODO: this division leads to round 99.9 to 99, maybe need to do something with this? *)
    const betFor : tez = natToTez(roundDiv(tezToNat(Tezos.amount * ratio), event.ratioPrecision));
    const betAgainst : tez = Tezos.amount - betFor;
    event.betsForSum := event.betsForSum + betFor;
    event.betsAgainstSum := event.betsAgainstSum + betAgainst;

    (* Calculating liquidity bonus: *)
    const totalBettingTime : nat = abs(event.betsCloseTime - event.createdTime);
    const elapsedTime : int = Tezos.now - event.createdTime;
    if (elapsedTime < 0) then
        failwith("Bet adding before contract createdTime (possible wrong createdTime?)")
    else skip;

    const remainedTime : int = totalBettingTime - elapsedTime;

    (* Total liquidity: *)
    event.totalLiquidityProvided := event.totalLiquidityProvided + betAgainst + betFor;
    const newAmount : tez = getLedgerAmount(key, s.providedLiquidityLedger) + betAgainst + betFor;
    s.providedLiquidityLedger[key] := newAmount;

    (* liquidity For bonus: *)
    const liquidityForBonus : tez = abs(remainedTime) * betFor / totalBettingTime;
    const newAmount : tez = getLedgerAmount(key, s.liquidityForBonusLedger) + liquidityForBonus;
    s.liquidityForBonusLedger[key] := newAmount;
    event.totalLiquidityForBonusSum := event.totalLiquidityForBonusSum + liquidityForBonus;

    (* liquidity Against bonus: *)
    const liquidityAgainstBonus : tez = abs(remainedTime) * betAgainst / totalBettingTime;
    const newAmount : tez = getLedgerAmount(key, s.liquidityAgainstBonusLedger) + liquidityAgainstBonus;
    s.liquidityAgainstBonusLedger[key] := newAmount;
    event.totalLiquidityAgainstBonusSum := event.totalLiquidityAgainstBonusSum + liquidityAgainstBonus;

    s.events[eventId] := event;

} with s
