
function excludeLiquidity(
        var value : nat;
        const event : eventType;
        const store : storage) : nat is
    block {

        (* Calculating liquidity bonus: *)
        const totalBettingTime : nat = abs(event.betsCloseTime - event.createdTime);
        const elapsedTime : int = Tezos.get_now() - event.createdTime;
        if (elapsedTime < 0) then
            (* It is impossible to get here, but if somehow it happens,
                it can be exploited so I made this failwith: *)
            failwith("Bet adding before event createdTime")
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
    var event : eventType := getEvent(store, eventId);

    (* Checking that there are liquidity in both pools (>0) *)
    if (event.poolAboveEq = 0tez) or (event.poolBelow = 0tez) then
        failwith("Can't process bet before liquidity added")
    else skip;

    if (Tezos.get_now() > event.betsCloseTime) then
        failwith("Bets after betCloseTime is not allowed")
    else skip;

    if Tezos.get_amount() = 0tez then failwith("Bet without tez") else skip;

    const key : ledgerKey = (Tezos.get_sender(), eventId);

    (* poolTo is the pool where bet goes *)
    var poolTo : nat := case params.bet of [
    | AboveEq -> tezToNat(event.poolAboveEq)
    | Below -> tezToNat(event.poolBelow)
    ];

    (* poolFrom is the pool where possible win earrings coming *)
    var poolFrom : nat := case params.bet of [
    | AboveEq -> tezToNat(event.poolBelow)
    | Below -> tezToNat(event.poolAboveEq)
    ];

    const betValue : nat = tezToNat(Tezos.get_amount());

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
    case params.bet of [
    | AboveEq -> block {
        store.betsAboveEq[key] :=
            getLedgerAmount(key, store.betsAboveEq) + possibleWinAmount;
        event.poolAboveEq := natToTez(poolTo);
        event.poolBelow := natToTez(poolFrom);
    }
    | Below -> block {
        store.betsBelow[key] :=
            getLedgerAmount(key, store.betsBelow) + possibleWinAmount;
        event.poolAboveEq := natToTez(poolFrom);
        event.poolBelow := natToTez(poolTo);
    }
    ];

    (* Adding this bet into deposited bets ledger that tracks all bets
        regardless above / below: *)
    store.depositedBets[key] :=
        getLedgerAmount(key, store.depositedBets) + Tezos.get_amount();

    store.events[eventId] := event;

} with ((nil: list(operation)), store)
