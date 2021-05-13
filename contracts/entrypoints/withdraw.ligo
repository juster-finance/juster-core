(* TODO: rename to reward? *)
function withdraw(
    var eventId : eventIdType;
    var s: storage) : (list(operation) * storage) is
block {
    (* TODO: add list of reciever addresses to make bulk transactions
        and make it possible to call it by anyone *)
    (* TODO: allow to call this method by liquidity providers after K hours
        after close and reduce withdraw amount a bit in this case *)

    const event : eventType = getEvent(s, eventId);
    const key : ledgerKey = (Tezos.sender, eventId);

    if event.isClosed then skip
    else failwith("Withdraw is not allowed until contract is closed");

    (* defining variables that dependend on winning pool: *)        
    var payout : tez := 0tez;
    const share : nat = getNatLedgerAmount(key, s.liquidityShares);

    if event.isBetsForWin then block {
        payout := getLedgerAmount(key, s.betsFor);

        (* calculating liquidity return: *)
        const providedFor : tez =
            getLedgerAmount(key, s.providedLiquidityFor);
        const againstReturn : tez =
            share * event.poolAgainst/ event.totalLiquidityShares;
        payout := payout + providedFor + againstReturn;
    }
    else block {
        payout := getLedgerAmount(key, s.betsAgainst);

        (* calculating liquidity return. It is distributed by loosed ledger: *)
        const providedAgainst : tez =
            getLedgerAmount(key, s.providedLiquidityAgainst);
        const forReturn : tez =
            share * event.poolFor / event.totalLiquidityShares;
        payout := payout + providedAgainst + forReturn;
    };

    (* Removing key from all ledgers: *)
    s.betsFor := Big_map.remove(key, s.betsFor);
    s.betsAgainst := Big_map.remove(key, s.betsAgainst);
    s.providedLiquidityFor := Big_map.remove(key, s.providedLiquidityFor);
    s.providedLiquidityAgainst := Big_map.remove(key, s.providedLiquidityAgainst);
    s.liquidityShares := Big_map.remove(key, s.liquidityShares);
    s.depositedBets := Big_map.remove(key, s.depositedBets);

    const receiver : contract(unit) = getReceiver(Tezos.sender);
    const operation : operation = Tezos.transaction(unit, payout, receiver);

    (* Operation should be returned only if there are some amount to return: *)
    var operations : list(operation) := nil;
    if payout > 0tez then operations := operation # operations
    else skip;

    (* TODO: calculate participants/LPs count and remove event if there are 0 *)
    s.events[eventId] := event;

} with (operations, s)
