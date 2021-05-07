(* TODO: rename to reward? *)
function withdraw(var eventId : eventIdType; var s: storage) : (list(operation) * storage) is
block {
    (* TODO: add list of reciever addresses to make bulk transactions
        and make it possible to call it by anyone *)
    (* TODO: allow to call this method by liquidity providers after K hours after close
        and reduce withdraw amount a bit in this case *)

    const event : eventType = getEvent(s, eventId);
    const key : ledgerKey = (Tezos.sender, eventId);

    if event.isClosed then skip
    else failwith("Withdraw is not allowed until contract is closed");

    (* defining variables that dependend on winning pool: *)        
    var winPayout : tez := 0tez;
    var providerProfits : int := 0;

    if event.isBetsForWin then block {
        winPayout := getLedgerAmount(key, s.betsForWinningLedger);

        (* calculating liquidity return. It is distributed by loosed ledger: *)
        const profitLossPerShareAtEntry : int = getProfitLossLedgerAmount(key, s.winForProfitLossPerShareAtEntry);
        const totalShares : int = int(tezToNat(getLedgerAmount(key, s.liquidityAgainstSharesLedger)));
        // REMOVE: const initShares : int = int(tezToNat(event.firstProviderAgainstSharesSum));
        providerProfits := (event.winForProfitLossPerShare*totalShares) / int(event.sharePrecision) - profitLossPerShareAtEntry;
        (* TODO: refactor this lines to make it more clear? *)
    }
    else block {
        winPayout := getLedgerAmount(key, s.betsAgainstWinningLedger);

        (* calculating liquidity return. It is distributed by loosed ledger: *)
        const profitLossPerShareAtEntry : int = getProfitLossLedgerAmount(key, s.winAgainstProfitLossPerShareAtEntry);
        const totalShares : int = int(tezToNat(getLedgerAmount(key, s.liquidityForSharesLedger)));
        // REMOVE: const initShares : int = int(tezToNat(event.firstProviderForSharesSum));    
        providerProfits := (event.winAgainstProfitLossPerShare*totalShares / int(event.sharePrecision)) - profitLossPerShareAtEntry;
        (* TODO: refactor this lines to make it more clear? *)
    };

    (* Calculating liquidity bonus for provider and distributing profit/loss *)
    const providedLiquidity : tez = getLedgerAmount(key, s.providedLiquidityLedger);

    const profitOrLoss : tez = abs(providerProfits) * 1mutez;

    (* Payment for liquidity provider *)
    var liquidityPayout : tez := 0tez;
    if providerProfits > 0 then liquidityPayout := providedLiquidity + profitOrLoss
    else liquidityPayout := providedLiquidity - profitOrLoss;

    (* Removing key from all ledgers: *)
    s.betsForWinningLedger := Big_map.remove(key, s.betsForWinningLedger);
    s.betsAgainstWinningLedger := Big_map.remove(key, s.betsAgainstWinningLedger);
    s.providedLiquidityLedger := Big_map.remove(key, s.providedLiquidityLedger);
    s.liquidityForSharesLedger := Big_map.remove(key, s.liquidityForSharesLedger);
    s.liquidityAgainstSharesLedger := Big_map.remove(key, s.liquidityAgainstSharesLedger);
    s.winForProfitLossPerShareAtEntry := Big_map.remove(key, s.winForProfitLossPerShareAtEntry);
    s.winAgainstProfitLossPerShareAtEntry := Big_map.remove(key, s.winAgainstProfitLossPerShareAtEntry);
    s.depositedBets := Big_map.remove(key, s.depositedBets);

    const totalPayoutAmount : tez = winPayout + liquidityPayout;
    (* TODO: If totalPayoutAmount is zero: do finish this call without operations, this is needed to
        properly removing participants that loosed *)

    const receiver : contract(unit) = getReceiver(Tezos.sender);
    const payoutOperation : operation = Tezos.transaction(unit, totalPayoutAmount, receiver);

    (* TODO: calculate participants/LPs count and remove event if there are 0 *)
    s.events[eventId] := event;

} with (list[payoutOperation], s)
