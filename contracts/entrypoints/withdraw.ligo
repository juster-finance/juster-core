function calculatePayout(
    var store: storage;
    var event : eventType;
    var key : ledgerKey) : tez is

block {

    var payout : tez := 0tez;
    const share : nat = getNatLedgerAmount(key, store.liquidityShares);

    if event.isbetsAboveEqWin then block {
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
    var eventId : nat;
    var store: storage) : (list(operation) * storage) is
block {
    (* TODO: add list of reciever addresses to make bulk transactions
        and make it possible to call it by anyone *)
    (* TODO: allow to call this method by liquidity providers after K hours
        after close and reduce withdraw amount a bit in this case *)

    checkNoAmountIncluded(unit);

    const event : eventType = getEvent(store, eventId);
    const key : ledgerKey = (Tezos.sender, eventId);

    if event.isClosed then skip
    else failwith("Withdraw is not allowed until contract is closed");

    var payout : tez := calculatePayout(store, event, key);

    (* If Force Majeure was activated, returning payout calcs differently: *)
    if event.isForceMajeure then
        payout := forceMajeureReturnPayout(store, key)
    else skip;

    (* Removing key from all ledgers: *)
    store.betsAboveEq := Big_map.remove(key, store.betsAboveEq);
    store.betsBellow := Big_map.remove(key, store.betsBellow);
    store.providedLiquidityAboveEq := Big_map.remove(key, store.providedLiquidityAboveEq);
    store.providedLiquidityBellow :=
        Big_map.remove(key, store.providedLiquidityBellow);
    store.liquidityShares := Big_map.remove(key, store.liquidityShares);
    store.depositedBets := Big_map.remove(key, store.depositedBets);

    const operations : list(operation) = makeOperationsIfNeeded(Tezos.sender, payout);

    (* TODO: calculate participants/LPs count and remove event if there are 0 *)
    store.events[eventId] := event;

} with (operations, store)
