function bet(var p : betParams; var s : storage) : (list(operation) * storage) is
block {
    (* TODO: check that there are liquidity in both pools (>0) *)
    (* TODO: reduce bet value by liquidity percent (done? check it) *)
    (* TODO: maybe reduce/raise liquidity percent during bet period? *)

    (* TODO: assert that betFor / betAgainst is less than MAX_RATIO controlled by Manager *)
    (* TODO: assert that betAgainst / betFor is less than MAX_RATIO controlled by Manager *)

    const eventId : eventIdType = p.eventId;
    const event : eventType = getEvent(s, eventId);

    if (Tezos.now > event.betsCloseTime) then
        failwith("Bets after betCloseTime is not allowed")
    else skip;

    if event.isClosed then failwith("Event already closed") else skip;

    (* TODO: assert that Tezos.amount is more than zero? (instead it can lead to junk records
        in ledgers, that would not be removed) *)

    const key : ledgerKey = (Tezos.sender, eventId);

    const alreadyBetValue : tez =
        getLedgerAmount(key, s.betsForLedger) + getLedgerAmount(key, s.betsAgainstLedger);

    if (alreadyBetValue = 0tez) then
        event.participants := event.participants + 1n;
    else skip;

    var possibleWinAmount : tez := 0tez;
    const totalBets : tez = event.betsForSum + event.betsAgainstSum;

    (* TODO: refactor this two similar blocks somehow? or keep straight and simple? *)
    case p.bet of
    | For -> block {
        event.betsForSum := event.betsForSum + Tezos.amount;
        possibleWinAmount := (
            Tezos.amount + Tezos.amount / 1mutez * event.betsAgainstSum / event.betsForSum * 1mutez);

        (* Excluding liquidity fee: *)
        (* TODO: maybe make raising fee from 0 to liquidityPercent during bet period? *)
        possibleWinAmount :=
            possibleWinAmount * abs(event.liquidityPrecision - event.liquidityPercent)
            / event.liquidityPrecision;
        const unallocatedBets : tez = totalBets - event.betsForWinningPoolSum;
        possibleWinAmount := minTez(possibleWinAmount, unallocatedBets);

        if possibleWinAmount < p.minimalWinAmount then failwith("Wrong minimalWinAmount")
        else skip;

        event.betsForWinningPoolSum := event.betsForWinningPoolSum + possibleWinAmount;
        s.betsForLedger[key] := getLedgerAmount(key, s.betsForLedger) + possibleWinAmount;
    }
    | Against -> {
        event.betsAgainstSum := event.betsAgainstSum + Tezos.amount;
        possibleWinAmount := (
            Tezos.amount + Tezos.amount / 1mutez * event.betsForSum / event.betsAgainstSum * 1mutez);

        (* Excluding liquidity fee: *)
        (* TODO: maybe make raising fee from 0 to liquidityPercent during bet period? *)
        possibleWinAmount :=
            possibleWinAmount * abs(event.liquidityPrecision - event.liquidityPercent)
            / event.liquidityPrecision;
        const unallocatedBets : tez = totalBets - event.betsAgainstWinningPoolSum;
        possibleWinAmount := minTez(possibleWinAmount, unallocatedBets);

        if possibleWinAmount < p.minimalWinAmount then failwith("Wrong minimalWinAmount")
        else skip;

        event.betsAgainstWinningPoolSum := event.betsAgainstWinningPoolSum + possibleWinAmount;
        s.betsAgainstLedger[key] := getLedgerAmount(key, s.betsAgainstLedger) + possibleWinAmount;
    }
    end;

    s.events[eventId] := event;
} with ((nil: list(operation)), s)
