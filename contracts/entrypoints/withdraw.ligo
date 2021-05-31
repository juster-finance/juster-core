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


function withdraw(
    var params : withdrawParams;
    var store: storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    const event : eventType = getEvent(store, params.eventId);
    const key : ledgerKey = (Tezos.sender, params.eventId);

    if event.isClosed then skip
    else failwith("Withdraw is not allowed until contract is closed");

    var payout : tez := calculatePayout(store, event, key);
    operations := makeOperationsIfNotZero(Tezos.sender, payout);

    (* Splitting payout fee if time passed from closed is more than
        config rewardFeeSplitAfter: *)
    // if Tezos.now > event.closedOracleTime + store.
    // var operations : list(operation) := nil;

    (* If Force Majeure was activated, returning payout calcs differently.
        - in force majeure reward fee split should be not active so it is
        just rewriting all operations: *)
    if event.isForceMajeure then
    block {
        payout := forceMajeureReturnPayout(store, key);
        operations := makeOperationsIfNotZero(Tezos.sender, payout);
    } else skip;

    (* Removing key from all ledgers: *)
    store.betsAboveEq := Big_map.remove(key, store.betsAboveEq);
    store.betsBellow := Big_map.remove(key, store.betsBellow);
    store.providedLiquidityAboveEq := Big_map.remove(key, store.providedLiquidityAboveEq);
    store.providedLiquidityBellow :=
        Big_map.remove(key, store.providedLiquidityBellow);
    store.liquidityShares := Big_map.remove(key, store.liquidityShares);
    store.depositedBets := Big_map.remove(key, store.depositedBets);

    (* TODO: calculate participants/LPs count and remove event if there are 0 *)
    store.events[params.eventId] := event;

} with (operations, store)
