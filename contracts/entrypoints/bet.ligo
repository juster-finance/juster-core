
function excludeLiquidity(
        var value : nat;
        const event : eventType;
        const store : storage) : nat is
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
        value := value * multiplier / store.liquidityPrecision;
    } with value


function bet(
    const params : betParams;
    var store : storage) : (list(operation) * storage) is
block {

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
    if Tezos.amount = 0tez then failwith("Bet without tez") else skip;

    const key : ledgerKey = (Tezos.sender, eventId);

    (* poolTo is the pool where bet goes *)
    var poolTo : nat := case params.bet of
    | AboveEq -> tezToNat(event.poolAboveEq)
    | Bellow -> tezToNat(event.poolBellow)
    end;

    (* poolFrom is the pool where possible win earrings coming *)
    var poolFrom : nat := case params.bet of
    | AboveEq -> tezToNat(event.poolBellow)
    | Bellow -> tezToNat(event.poolAboveEq)
    end;

    const betValue : nat = tezToNat(Tezos.amount);

    (* Increasing participants count if this participant is not counted yet: *)
    if isParticipant(store, key) then skip
    else event.participants := event.participants + 1n;

    (* adding liquidity to betting pool *)
    poolTo := poolTo + betValue;

    const winDelta : nat = betValue * poolFrom / poolTo;
    const winDeltaCut : nat = excludeLiquidity(winDelta, event, store);
    const winDeltaPossible : nat = minNat(winDeltaCut, poolFrom);

    (* removing liquidity from another pool to keep ratio balanced: *)
    (* NOTE: liquidity fee is included in the delta *)
    poolFrom := abs(poolFrom - winDeltaPossible);

    const possibleWinAmount : tez = natToTez(betValue + winDeltaPossible);
    if possibleWinAmount < params.minimalWinAmount
    then failwith("Wrong minimalWinAmount")
    else skip;

    (* Updating event and ledger: *)
    case params.bet of
    | AboveEq -> block {
        store.betsAboveEq[key] :=
            getLedgerAmount(key, store.betsAboveEq) + possibleWinAmount;
        event.poolAboveEq := natToTez(poolTo);
        event.poolBellow := natToTez(poolFrom);
    }
    | Bellow -> block {
        store.betsBellow[key] :=
            getLedgerAmount(key, store.betsBellow) + possibleWinAmount;
        event.poolAboveEq := natToTez(poolFrom);
        event.poolBellow := natToTez(poolTo);
    }
    end;

    (* Adding this bet into deposited bets ledger that tracks all bets
        regardless above / bellow: *)
    store.depositedBets[key] :=
        getLedgerAmount(key, store.depositedBets) + Tezos.amount;

    store.events[eventId] := event;

} with ((nil: list(operation)), store)
