function calculatePayout(
    var store: storage;
    var event : eventType;
    var key : ledgerKey) : tez is

block {

    var payout : tez := 0tez;
    const share : nat = getNatLedgerAmount(key, store.liquidityShares);

    if event.isBetsAboveEqWin then block {
        payout := getLedgerAmount(key, store.betsAboveEq);

        (* calculating liquidity return: *)
        const providedAboveEq : tez =
            getLedgerAmount(key, store.providedLiquidityAboveEq);
        const bellowReturn : tez =
            share * event.poolBellow/ event.totalLiquidityShares;
        payout := payout + providedAboveEq + bellowReturn;
    }
    else block {
        payout := getLedgerAmount(key, store.betsBellow);

        (* calculating liquidity return. It is distributed by loosed ledger: *)
        const providedBellow : tez =
            getLedgerAmount(key, store.providedLiquidityBellow);
        const aboveEqReturn : tez =
            share * event.poolAboveEq / event.totalLiquidityShares;
        payout := payout + providedBellow + aboveEqReturn;
    };
} with payout


function forceMajeureReturnPayout(
    var store: storage;
    var key : ledgerKey) : tez is (
        getLedgerAmount(key, store.depositedBets)
        + getLedgerAmount(key, store.providedLiquidityAboveEq)
        + getLedgerAmount(key, store.providedLiquidityBellow))


function excludeFeeReward(
    const store : storage;
    const params : withdrawParams;
    const payout : tez) : list(operation) is

block {
    var operations : list(operation) := nil;
    var participantPayout : tez := 0tez;
    var senderPayout : tez := 0tez;

    if payout > store.config.rewardCallFee
    then block {
        participantPayout := payout - store.config.rewardCallFee;
        senderPayout := store.config.rewardCallFee;
    } else senderPayout := payout;

    if participantPayout > 0tez
    then operations := prepareOperation(
            params.participantAddress, participantPayout) # operations
    else skip;

    if senderPayout > 0tez
    then operations := prepareOperation(
            Tezos.sender, senderPayout) # operations
    else skip;

} with operations


function makeWithdrawOperations(
    const store : storage;
    const params : withdrawParams;
    const event : eventType;
    const key : ledgerKey) : list(operation) is
block {

    var payout : tez := calculatePayout(store, event, key);

    (* By default creating one operation to participantAddress: *)
    var operations : list(operation) :=
        makeOperationsIfNotZero(params.participantAddress, payout);

    (* If a lot time passed from closed time, splitting reward and
        rewriting operations: *)
    const feeTime : timestamp =
        event.closedOracleTime + int(store.config.rewardFeeSplitAfter);

    if (Tezos.sender =/= params.participantAddress) and (Tezos.now >= feeTime)
    then operations := excludeFeeReward(store, params, payout)
    else skip;

    (* If Force Majeure was activated, returning all bets and provided liquidity.
        - in force majeure reward fee split should be not active so it is
        just rewriting all operations: *)
    if event.isForceMajeure then
    block {
        payout := forceMajeureReturnPayout(store, key);
        operations := makeOperationsIfNotZero(params.participantAddress, payout);
    } else skip;

} with operations;


(* Removing key from all ledgers: *)
function removeKeyFromAllLedgers(
    var store : storage;
    const key : ledgerKey) : storage is
block {

    store.betsAboveEq := Big_map.remove(key, store.betsAboveEq);
    store.betsBellow := Big_map.remove(key, store.betsBellow);
    store.providedLiquidityAboveEq :=
        Big_map.remove(key, store.providedLiquidityAboveEq);
    store.providedLiquidityBellow :=
        Big_map.remove(key, store.providedLiquidityBellow);
    store.liquidityShares := Big_map.remove(key, store.liquidityShares);
    store.depositedBets := Big_map.remove(key, store.depositedBets);

} with store


function withdraw(
    var params : withdrawParams;
    var store: storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    const event : eventType = getEvent(store, params.eventId);
    const key : ledgerKey = (params.participantAddress, params.eventId);

    if event.isClosed then skip
    else failwith("Withdraw is not allowed until contract is closed");

    const operations : list(operation) =
        makeWithdrawOperations(store, params, event, key);

    (* Decreasing participants count: *)
    if isParticipant(store, key)
    then event.participants := abs(event.participants - 1n)
    else skip;

    store := removeKeyFromAllLedgers(store, key);

    (* If there are no participants in event left: removing event: *)
    if event.participants = 0n
    then store.events := Big_map.remove(params.eventId, store.events)
    else store.events[params.eventId] := event;

} with (operations, store)
