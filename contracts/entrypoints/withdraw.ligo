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
    var winPayout : tez := 0tez;
    var providerProfits : int := 0;

    if event.isBetsForWin then block {
        winPayout := getLedgerAmount(key, s.betsFor);

        (* calculating liquidity return. It is distributed by loosed ledger: *)
        const profitDiff : int = getDiffLedgerAmount(key, s.forProfitDiff);
        const totalShares : int =
            int(tezToNat(getLedgerAmount(key, s.liquidityAgainstShares)));
        providerProfits :=
            (event.forProfit*totalShares) / int(event.sharePrecision)
            - profitDiff;
    }
    else block {
        winPayout := getLedgerAmount(key, s.betsAgainst);

        (* calculating liquidity return. It is distributed by loosed ledger: *)
        const profitDiff : int = getDiffLedgerAmount(key, s.againstProfitDiff);
        const totalShares : int =
            int(tezToNat(getLedgerAmount(key, s.liquidityForShares)));
        providerProfits :=
            (event.againstProfit*totalShares / int(event.sharePrecision))
            - profitDiff;
    };

    (* Calculating liquidity bonus for provider and distributing profit/loss *)
    const providedLiquidity : tez = getLedgerAmount(key, s.providedLiquidity);

    const profitOrLoss : tez = abs(providerProfits) * 1mutez;

    (* Payment for liquidity provider *)
    var liquidityPayout : tez := 0tez;
    if providerProfits > 0
    then liquidityPayout := providedLiquidity + profitOrLoss
    else liquidityPayout := providedLiquidity - profitOrLoss;

    (* Removing key from all ledgers: *)
    s.betsFor := Big_map.remove(key, s.betsFor);
    s.betsAgainst := Big_map.remove(key, s.betsAgainst);
    s.providedLiquidity := Big_map.remove(key, s.providedLiquidity);
    s.liquidityForShares := Big_map.remove(key, s.liquidityForShares);
    s.liquidityAgainstShares := Big_map.remove(key, s.liquidityAgainstShares);
    s.forProfitDiff := Big_map.remove(key, s.forProfitDiff);
    s.againstProfitDiff := Big_map.remove(key, s.againstProfitDiff);
    s.depositedBets := Big_map.remove(key, s.depositedBets);

    const totalPayoutAmount : tez = winPayout + liquidityPayout;
    (* TODO: If totalPayoutAmount is zero: do finish this call without
        operations, this is needed to properly removing participants
        that loosed *)

    const receiver : contract(unit) = getReceiver(Tezos.sender);
    const payoutOperation : operation =
        Tezos.transaction(unit, totalPayoutAmount, receiver);

    (* TODO: calculate participants/LPs count and remove event if there are 0 *)
    s.events[eventId] := event;

} with (list[payoutOperation], s)
