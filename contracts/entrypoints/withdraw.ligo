(* TODO: rename to reward? *)
function withdraw(
    var eventId : nat;
    var store: storage) : (list(operation) * storage) is
block {
    (* TODO: add list of reciever addresses to make bulk transactions
        and make it possible to call it by anyone *)
    (* TODO: allow to call this method by liquidity providers after K hours
        after close and reduce withdraw amount a bit in this case *)

    const event : eventType = getEvent(store, eventId);
    const key : ledgerKey = (Tezos.sender, eventId);

    if event.isClosed then skip
    else failwith("Withdraw is not allowed until contract is closed");

    (* defining variables that dependend on winning pool: *)        
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

    (* Removing key from all ledgers: *)
    store.betsFor := Big_map.remove(key, store.betsFor);
    store.betsAgainst := Big_map.remove(key, store.betsAgainst);
    store.providedLiquidityFor := Big_map.remove(key, store.providedLiquidityFor);
    store.providedLiquidityAgainst :=
        Big_map.remove(key, store.providedLiquidityAgainst);
    store.liquidityShares := Big_map.remove(key, store.liquidityShares);
    store.depositedBets := Big_map.remove(key, store.depositedBets);

    const receiver : contract(unit) = getReceiver(Tezos.sender);
    const operation : operation = Tezos.transaction(unit, payout, receiver);

    (* Operation should be returned only if there are some amount to return: *)
    var operations : list(operation) := nil;
    if payout > 0tez then operations := operation # operations
    else skip;

    (* TODO: calculate participants/LPs count and remove event if there are 0 *)
    store.events[eventId] := event;

} with (operations, store)
