function bet(var params : betParams; var store : storage) : (list(operation) * storage) is
block {
    (* TODO: check that there are liquidity in both pools (>0) *)
    (* TODO: reduce bet value by liquidity percent (done? check it) *)
    (* TODO: maybe reduce/raise liquidity percent during bet period? *)

    (* TODO: assert that betFor / betAgainst is less than MAX_RATIO controlled by Manager *)
    (* TODO: assert that betAgainst / betFor is less than MAX_RATIO controlled by Manager *)

    const eventId : eventIdType = params.eventId;
    const event : eventType = getEvent(store, eventId);

    if (Tezos.now > event.betsCloseTime) then
        failwith("Bets after betCloseTime is not allowed")
    else skip;

    if event.isClosed then failwith("Event already closed") else skip;

    (* TODO: assert that Tezos.amount is more than zero? (instead it can lead to junk records
        in ledgers, that would not be removed) *)

    const key : ledgerKey = (Tezos.sender, eventId);
    var possibleWinAmount : tez := 0tez;

    function excludeLiquidity(var value : tez; var event : eventType) : tez is
        (* TODO: maybe make raising fee from 0 to liquidityPercent during bet period? *)
        value * abs(event.liquidityPrecision - event.liquidityPercent)
        / event.liquidityPrecision;

    (* TODO: refactor this two similar blocks somehow? or keep straight and simple? *)
    case params.bet of
    | For -> block {
        (* adding liquidity to betting pool *)
        event.betsForLiquidityPoolSum := event.betsForLiquidityPoolSum + Tezos.amount;
        const winDelta : tez =
            natToTez(tezToNat(Tezos.amount) * event.betsAgainstLiquidityPoolSum / event.betsForLiquidityPoolSum);

        const winDeltaExcludedLiquidity : tez = excludeLiquidity(winDelta, event);
        const winDeltaPossible : tez = minTez(winDeltaExcludedLiquidity, event.betsAgainstLiquidityPoolSum);

        possibleWinAmount := Tezos.amount + winDeltaPossible;
        if possibleWinAmount < params.minimalWinAmount then failwith("Wrong minimalWinAmount")
        else skip;

        (* removing liquidity from another pool to keep ratio balanced: *)
        (* NOTE: removing winDelta before liquidity excluded (is it correct?) *)
        event.betsAgainstLiquidityPoolSum := event.betsAgainstLiquidityPoolSum - winDelta;

        (* Updating LP profit losses for For/Against win scenarios: *)
        event.winAgainstProfitLoss := event.winAgainstProfitLoss + tezToNat(Tezos.amount);
        event.winForProfitLoss := event.winForProfitLoss - tezToNat(winDeltaPossible);

        store.betsForWinningLedger[key] :=
            getLedgerAmount(key, store.betsForWinningLedger) + possibleWinAmount;
    }
    | Against -> {
        (* adding liquidity to betting pool *)
        event.betsAgainstLiquidityPoolSum := event.betsAgainstLiquidityPoolSum + Tezos.amount;
        const winDelta : tez =
            natToTez(tezToNat(Tezos.amount) * event.betsForLiquidityPoolSum / event.betsAgainstLiquidityPoolSum);

        const winDeltaExcludedLiquidity : tez = excludeLiquidity(winDelta, event);
        const winDeltaPossible : tez = minTez(winDeltaExcludedLiquidity, event.betsForLiquidityPoolSum);

        possibleWinAmount := Tezos.amount + winDeltaPossible;
        if possibleWinAmount < params.minimalWinAmount then failwith("Wrong minimalWinAmount")
        else skip;

        (* removing liquidity from another pool to keep ratio balanced: *)
        (* NOTE: removing winDelta before liquidity excluded (is it correct?) *)
        event.betsForLiquidityPoolSum := event.betsForLiquidityPoolSum - winDelta;

        (* Updating LP profit losses for For/Against win scenarios: *)
        event.winForProfitLoss := event.winForProfitLoss + tezToNat(Tezos.amount);
        event.winAgainstProfitLoss := event.winAgainstProfitLoss - tezToNat(winDeltaPossible);

        store.betsAgainstWinningLedger[key] :=
            getLedgerAmount(key, store.betsAgainstWinningLedger) + possibleWinAmount;
    }
    end;

    store.events[eventId] := event;
} with ((nil: list(operation)), store)
