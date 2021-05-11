function bet(
    var params : betParams;
    var store : storage) : (list(operation) * storage) is
block {
    (* TODO: check that there are liquidity in both pools (>0) *)
    (* TODO: reduce bet value by liquidity percent (done? check it) *)
    (* TODO: maybe reduce/raise liquidity percent during bet period? *)

    (* TODO: assert that betFor / betAgainst is less than MAX_RATIO
        controlled by Manager *)
    (* TODO: assert that betAgainst / betFor is less than MAX_RATIO
        controlled by Manager *)

    const eventId : eventIdType = params.eventId;
    const event : eventType = getEvent(store, eventId);

    if (Tezos.now > event.betsCloseTime) then
        failwith("Bets after betCloseTime is not allowed")
    else skip;

    if event.isClosed then failwith("Event already closed") else skip;

    (* TODO: assert that Tezos.amount is more than zero? (instead it can
        lead to junk records in ledgers, that would not be removed) *)

    const key : ledgerKey = (Tezos.sender, eventId);
    var possibleWinAmount : tez := 0tez;

    function excludeLiquidity(var value : tez; var event : eventType) : tez is
        (* TODO: maybe make raising fee from 0 to
            liquidityPercent during bet period? *)
        value * abs(event.liquidityPrecision - event.liquidityPercent)
        / event.liquidityPrecision;

    (* TODO: refactor this two similar blocks somehow?
        or keep straight and simple? *)
    case params.bet of
    | For -> block {
        (* adding liquidity to betting pool *)
        event.poolFor := event.poolFor + Tezos.amount;
        const winDelta : tez =
            natToTez(tezToNat(Tezos.amount) * event.poolAgainst
            / event.poolFor);

        const winDeltaPossible : tez =
            minTez(excludeLiquidity(winDelta, event), event.poolAgainst);

        possibleWinAmount := Tezos.amount + winDeltaPossible;
        if possibleWinAmount < params.minimalWinAmount
        then failwith("Wrong minimalWinAmount")
        else skip;

        (* removing liquidity from another pool to keep ratio balanced: *)
        (* NOTE: removing winDelta before liquidity excluded (it is lowering
            liquidity amount. Maybe it would be better first remove liquidity
            and then exclude it from pool). This requires to change tests,
            to do it simply: need to remove liquidity from current tests and
            add additional liquidity tests *)
        event.poolAgainst := event.poolAgainst - winDelta;

        (* Updating LP profit losses for For/Against win scenarios: *)
        event.againstProfit := (event.againstProfit
            + tezToNat(Tezos.amount) * event.sharePrecision
                / tezToNat(event.totalLiquidityForShares));
        event.forProfit := (event.forProfit
            - tezToNat(winDeltaPossible) * event.sharePrecision
                / tezToNat(event.totalLiquidityAgainstShares));

        store.betsFor[key] :=
            getLedgerAmount(key, store.betsFor) + possibleWinAmount;
    }
    | Against -> {
        (* adding liquidity to betting pool *)
        event.poolAgainst := event.poolAgainst + Tezos.amount;
        const winDelta : tez =
            natToTez(tezToNat(Tezos.amount) * event.poolFor
            / event.poolAgainst);

        const winDeltaPossible : tez =
            minTez(excludeLiquidity(winDelta, event), event.poolFor);

        possibleWinAmount := Tezos.amount + winDeltaPossible;
        if possibleWinAmount < params.minimalWinAmount
        then failwith("Wrong minimalWinAmount")
        else skip;

        (* removing liquidity from another pool to keep ratio balanced: *)
        event.poolFor := event.poolFor - winDelta;

        (* Updating LP profit losses for For/Against win scenarios: *)
        event.forProfit := (event.forProfit
            + tezToNat(Tezos.amount) * event.sharePrecision
                / tezToNat(event.totalLiquidityAgainstShares));
        event.againstProfit := (event.againstProfit
            - tezToNat(winDeltaPossible) * event.sharePrecision
                / tezToNat(event.totalLiquidityForShares));

        store.betsAgainst[key] :=
            getLedgerAmount(key, store.betsAgainst) + possibleWinAmount;
    }
    end;

    (* Adding this bet into deposited bets ledger that tracks all bets
        regardless for / against: *)
    store.depositedBets[key] :=
        getLedgerAmount(key, store.depositedBets) + Tezos.amount;

    store.events[eventId] := event;
} with ((nil: list(operation)), store)
