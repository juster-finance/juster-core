function calculatePayout(
    var store: storage;
    var event : eventType;
    var key : ledgerKey) : tez is

block {

    var payout : tez := 0tez;
    const share : nat = getNatLedgerAmount(key, store.liquidityShares);

    if event.isBetsForWin then block {
        payout := getLedgerAmount(key, store.betsFor);

        (* calculating liquidity return: *)
        const providedFor : tez =
            getLedgerAmount(key, store.providedLiquidityFor);
        const againstReturn : tez =
            share * event.poolAgainst/ event.totalLiquidityShares;
        payout := payout + providedFor + againstReturn;
    }
    else block {
        payout := getLedgerAmount(key, store.betsAgainst);

        (* calculating liquidity return. It is distributed by loosed ledger: *)
        const providedAgainst : tez =
            getLedgerAmount(key, store.providedLiquidityAgainst);
        const forReturn : tez =
            share * event.poolFor / event.totalLiquidityShares;
        payout := payout + providedAgainst + forReturn;
    };
} with payout


function forceMajeureReturnPayout(
    var store: storage;
    var key : ledgerKey) : tez is (
        getLedgerAmount(key, store.depositedBets)
        + getLedgerAmount(key, store.providedLiquidityFor)
        + getLedgerAmount(key, store.providedLiquidityAgainst))


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
    store.betsFor := Big_map.remove(key, store.betsFor);
    store.betsAgainst := Big_map.remove(key, store.betsAgainst);
    store.providedLiquidityFor := Big_map.remove(key, store.providedLiquidityFor);
    store.providedLiquidityAgainst :=
        Big_map.remove(key, store.providedLiquidityAgainst);
    store.liquidityShares := Big_map.remove(key, store.liquidityShares);
    store.depositedBets := Big_map.remove(key, store.depositedBets);

    const operations : list(operation) = makeOperationsIfNeeded(Tezos.sender, payout);

    (* TODO: calculate participants/LPs count and remove event if there are 0 *)
    store.events[eventId] := event;

} with (operations, store)
