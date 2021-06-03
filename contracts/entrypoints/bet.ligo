
function excludeLiquidity(
        var value : tez;
        var event : eventType;
        var store : storage) : tez is
    block {

        (* Calculating liquidity bonus: *)
        const totalBettingTime : nat = abs(event.betsCloseTime - event.createdTime);
        const elapsedTime : int = Tezos.now - event.createdTime;
        if (elapsedTime < 0) then
            (* It is impossible to get here, but if somehow it happens,
                it can be exploited so I made this failwith: *)
            failwith("Bet adding before contract createdTime")
        else skip;

        (* Liquidity percent is zero at the event start and goes to
            event.liquidityPercent when event.betsCloseTime comes *)
        const timeAdjustedPercent : nat =
            event.liquidityPercent * abs(elapsedTime) / totalBettingTime;
        const multiplier : nat = abs(store.liquidityPrecision - timeAdjustedPercent);
        value := natToTez(tezToNat(value) * multiplier / store.liquidityPrecision);
    } with value


function calculateWinDelta(
    const value : tez;
    const top : tez;
    const bottom : tez) : tez is

    natToTez(tezToNat(value) * tezToNat(top) / tezToNat(bottom))


function bet(
    var params : betParams;
    var store : storage) : (list(operation) * storage) is
block {

    (* TODO: assert that betAboveEq / betBellow is less than MAX_RATIO
        controlled by Manager *)
    (* TODO: assert that betBellow / betAboveEq is less than MAX_RATIO
        controlled by Manager *)

    const eventId : nat = params.eventId;
    const event : eventType = getEvent(store, eventId);

    (* Checking that there are liquidity in both pools (>0) *)
    if (event.poolAboveEq = 0tez) or (event.poolBellow = 0tez) then
        failwith("Can't process bet before liquidity added")
    else skip;

    if (Tezos.now > event.betsCloseTime) then
        failwith("Bets after betCloseTime is not allowed")
    else skip;

    if event.isClosed then failwith("Event already closed") else skip;

    (* TODO: assert that Tezos.amount is more than zero? (instead it can
        lead to junk records in ledgers, that would not be removed) *)

    const key : ledgerKey = (Tezos.sender, eventId);
    var possibleWinAmount : tez := 0tez;        

    (* Increasing participants count if this participant is not counted yet: *)
    if isParticipant(store, key)
    then skip
    else event.participants := event.participants + 1n;

    (* TODO: refactor this two similar blocks somehow?
        or keep straight and simple? *)
    case params.bet of
    | AboveEq -> block {
        (* adding liquidity to betting pool *)
        event.poolAboveEq := event.poolAboveEq + Tezos.amount;
        const winDelta : tez =
            calculateWinDelta(Tezos.amount, event.poolBellow, event.poolAboveEq);

        const winDeltaPossible : tez =
            minTez(excludeLiquidity(winDelta, event, store), event.poolBellow);

        possibleWinAmount := Tezos.amount + winDeltaPossible;
        if possibleWinAmount < params.minimalWinAmount
        then failwith("Wrong minimalWinAmount")
        else skip;

        (* removing liquidity from another pool to keep ratio balanced: *)
        (* NOTE: liquidity fee is included in the delta *)
        event.poolBellow := event.poolBellow - winDeltaPossible;

        store.betsAboveEq[key] :=
            getLedgerAmount(key, store.betsAboveEq) + possibleWinAmount;
    }
    | Bellow -> {
        (* adding liquidity to betting pool *)
        event.poolBellow := event.poolBellow + Tezos.amount;
        const winDelta : tez =
            calculateWinDelta(Tezos.amount, event.poolAboveEq, event.poolBellow);

        const winDeltaPossible : tez =
            minTez(excludeLiquidity(winDelta, event, store), event.poolAboveEq);

        possibleWinAmount := Tezos.amount + winDeltaPossible;
        if possibleWinAmount < params.minimalWinAmount
        then failwith("Wrong minimalWinAmount")
        else skip;

        (* removing liquidity from another pool to keep ratio balanced: *)
        (* NOTE: liquidity fee is included in the delta *)
        event.poolAboveEq := event.poolAboveEq - winDeltaPossible;

        store.betsBellow[key] :=
            getLedgerAmount(key, store.betsBellow) + possibleWinAmount;
    }
    end;

    (* Adding this bet into deposited bets ledger that tracks all bets
        regardless above / bellow: *)
    store.depositedBets[key] :=
        getLedgerAmount(key, store.depositedBets) + Tezos.amount;

    store.events[eventId] := event;
} with ((nil: list(operation)), store)
