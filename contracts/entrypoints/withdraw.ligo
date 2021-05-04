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
    var totalProfits : int := 0;
    var providedLiquidityBonus : tez := 0tez;
    var totalLiquidityBonusSum : tez := 0tez;
    
    if event.isBetsForWin then block {
        winPayout := getLedgerAmount(key, s.betsForWinningLedger);
        totalProfits := event.winForProfitLoss;

        (* liquidity bonus distributed by loosed ledger: *)
        providedLiquidityBonus := getLedgerAmount(key, s.liquidityAgainstBonusLedger);
        totalLiquidityBonusSum := event.totalLiquidityAgainstBonusSum;
    }
    else block {
        winPayout := getLedgerAmount(key, s.betsAgainstWinningLedger);
        totalProfits := event.winAgainstProfitLoss;

        (* liquidity bonus distributed by loosed ledger: *)
        providedLiquidityBonus := getLedgerAmount(key, s.liquidityForBonusLedger);
        totalLiquidityBonusSum := event.totalLiquidityForBonusSum;
    };

    (* Calculating liquidity bonus for provider and distributing profit/loss *)
    const providedLiquidity : tez = getLedgerAmount(key, s.providedLiquidityLedger);

    const profitOrLoss : tez =
        providedLiquidityBonus * abs(totalProfits) / totalLiquidityBonusSum * 1mutez;

    (* Payment for liquidity provider *)
    var liquidityPayout : tez := 0tez;
    if totalProfits > 0 then liquidityPayout := providedLiquidity + profitOrLoss
    else liquidityPayout := providedLiquidity - profitOrLoss;

    (* Removing key from all ledgers: *)
    s.betsForWinningLedger := Big_map.remove(key, s.betsForWinningLedger);
    s.betsAgainstWinningLedger := Big_map.remove(key, s.betsAgainstWinningLedger);
    s.providedLiquidityLedger := Big_map.remove(key, s.providedLiquidityLedger);
    s.liquidityForBonusLedger := Big_map.remove(key, s.liquidityForBonusLedger);
    s.liquidityAgainstBonusLedger := Big_map.remove(key, s.liquidityAgainstBonusLedger);

    const totalPayoutAmount : tez = winPayout + liquidityPayout;
    (* TODO: If totalPayoutAmount is zero: do finish this call without operations, this is needed to
        properly removing participants that loosed *)

    const receiver : contract(unit) = getReceiver(Tezos.sender);
    const payoutOperation : operation = Tezos.transaction(unit, totalPayoutAmount, receiver);

    s.events[eventId] := event;

} with (list[payoutOperation], s)
