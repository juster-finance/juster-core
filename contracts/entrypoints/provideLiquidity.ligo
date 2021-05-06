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

    (* Total liquidity: *)
    event.totalLiquidityProvided := event.totalLiquidityProvided + betAgainst + betFor;
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

    (* if this is the first provided liquidity: *)
    (* TODO: would it be better to use special flag to this kind of first LP scenario?
        Is it possible to combine this if-else tree with one that was before? *)
    if totalBets = 0tez then
    block {
        (* setting up firstProviderForSharesSum and firstProviderAgainstSharesSum: *)
        event.firstProviderForSharesSum := liquidityForShares;
        event.firstProviderAgainstSharesSum := liquidityAgainstShares;
    } else skip;

    (* in case this participant does not added new liquidity: *)
    if alreadyProvided = 0tez then
    block {
        (* recording current profit/losses that would be excluded in withdraw: *)
        const forProfitLoss : int = (
            getProfitLossLedgerAmount(key, s.winForProfitLossPerShareAtEntry) + event.winForProfitLossPerShare);
        s.winForProfitLossPerShareAtEntry[key] := forProfitLoss;

        const againstProfitLoss : int = (
            getProfitLossLedgerAmount(key, s.winAgainstProfitLossPerShareAtEntry) + event.winAgainstProfitLossPerShare);
        s.winAgainstProfitLossPerShareAtEntry[key] := againstProfitLoss;
    } else
    block {    
        (* The same provider adds liquidity second time: THIS SCENARIO IS VERY COMPLICATED
        
            TODO: is that logic valid? participant would raise his share and then it would need to pay more
            for already expected sum

        !! Maybe if LP provides liquidity second time, I should divide his current PLAtEntry
            by his share change multiplier? So if he had 1000 shares and adds 1000 more, his PLAtEntry
            should be divided by 2? If he had 500 shares and adds 100, it should be multiplied by 5/6.

            All this matter if LP adds liquidity after he already added with some profit/loss in pool. At the moment
            there are no tests that cover this scenario, I should do it.
        *)

        const newAgainstShares : int = int(liquidityAgainstShares / 1mutez);
        const totalAgainstShares : int = int(tezToNat(getLedgerAmount(key, s.liquidityAgainstSharesLedger))); 

        const newForShares : int = int(liquidityForShares / 1mutez);
        const totalForShares : int = int(tezToNat(getLedgerAmount(key, s.liquidityForSharesLedger)));

        const forProfitLoss : int = (
            getProfitLossLedgerAmount(key, s.winForProfitLossPerShareAtEntry)
            + event.winForProfitLossPerShare * newAgainstShares / totalAgainstShares);
        s.winForProfitLossPerShareAtEntry[key] := forProfitLoss;

        const againstProfitLoss : int = (
            getProfitLossLedgerAmount(key, s.winAgainstProfitLossPerShareAtEntry)
            + event.winAgainstProfitLossPerShare * newForShares / totalForShares);
        s.winAgainstProfitLossPerShareAtEntry[key] := againstProfitLoss;
    };

    s.events[eventId] := event;

} with ((nil: list(operation)), s)
