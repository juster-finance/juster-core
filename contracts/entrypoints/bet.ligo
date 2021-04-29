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

    const alreadyBetValue : tez =
        getLedgerAmount(key, store.betsForWinningLedger)
        + getLedgerAmount(key, store.betsAgainstWinningLedger);

    if (alreadyBetValue = 0tez) then
        event.participants := event.participants + 1n;
    else skip;

    var possibleWinAmount : tez := 0tez;
    const totalBets : tez = event.betsForSum + event.betsAgainstSum;

    function excludeLiquidity(var value : tez; var event : eventType) : tez is
        value * abs(event.liquidityPrecision - event.liquidityPercent)
        / event.liquidityPrecision;

    (* TODO: refactor this two similar blocks somehow? or keep straight and simple? *)
    case params.bet of
    | For -> block {
        event.betsForSum := event.betsForSum + Tezos.amount;
        const winDelta : tez =
            natToTez(tezToNat(Tezos.amount) * event.betsAgainstSum / event.betsForSum);
        possibleWinAmount := Tezos.amount + winDelta;

        (* Excluding liquidity fee: *)
        (* TODO: maybe make raising fee from 0 to liquidityPercent during bet period? *)
        possibleWinAmount := excludeLiquidity(possibleWinAmount, event);
        const unallocatedBets : tez = totalBets - event.betsForWinningPoolSum;
        possibleWinAmount := minTez(possibleWinAmount, unallocatedBets);

        if possibleWinAmount < params.minimalWinAmount then failwith("Wrong minimalWinAmount")
        else skip;

        event.betsForWinningPoolSum := event.betsForWinningPoolSum + possibleWinAmount;
        store.betsForWinningLedger[key] :=
            getLedgerAmount(key, store.betsForWinningLedger) + possibleWinAmount;
    }
    | Against -> {
        event.betsAgainstSum := event.betsAgainstSum + Tezos.amount;
        const winDelta : tez =
            natToTez(tezToNat(Tezos.amount) * event.betsForSum / event.betsAgainstSum);
        possibleWinAmount := Tezos.amount + winDelta;

        (* Excluding liquidity fee: *)
        (* TODO: maybe make raising fee from 0 to liquidityPercent during bet period? *)
        possibleWinAmount := excludeLiquidity(possibleWinAmount, event);
        const unallocatedBets : tez = totalBets - event.betsAgainstWinningPoolSum;
        possibleWinAmount := minTez(possibleWinAmount, unallocatedBets);

        if possibleWinAmount < params.minimalWinAmount then failwith("Wrong minimalWinAmount")
        else skip;

        event.betsAgainstWinningPoolSum := event.betsAgainstWinningPoolSum + possibleWinAmount;
        store.betsAgainstWinningLedger[key] :=
            getLedgerAmount(key, store.betsAgainstWinningLedger) + possibleWinAmount;
    }
    end;

    store.events[eventId] := event;
} with ((nil: list(operation)), store)
