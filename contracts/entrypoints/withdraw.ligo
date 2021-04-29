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

    (* TODO: calculate payout only for winning ledger *)
    var winPayout : tez := getLedgerAmount(key, s.betsForLedger);
    if event.isBetsForWin then skip
    else winPayout := getLedgerAmount(key, s.betsAgainstLedger);

    (* Getting reciever: *)
    const receiver : contract(unit) = getReceiver(Tezos.sender);

    (* TODO: winPayout calculated only for winners, need to remove loosed particiants too *)
    const totalBets : tez = (
        getLedgerAmount(key, s.betsForLedger)
        + getLedgerAmount(key, s.betsAgainstLedger));

    if totalBets > 0tez then
        event.participants := abs(event.participants - 1n);
    else skip;

    (* Removing sender from all ledgers: *)
    s.betsForLedger := Big_map.remove(key, s.betsForLedger);
    s.betsAgainstLedger := Big_map.remove(key, s.betsAgainstLedger);

    (* Payment for liquidity provider *)
    var liquidityPayout : tez := 0tez;
    if event.participants = 0n then
    block {
        (* Calculating liquidity bonus for provider and distributing profit/loss *)
        const providedLiquidity : tez = getLedgerAmount(key, s.providedLiquidityLedger);

        (* Profits can be positive or negative (losses) *)
        const totalProfits : int = (
            tezToNat(Tezos.balance)
            + tezToNat(event.withdrawnLiquidity)
            - tezToNat(event.totalLiquidityProvided));

        (* There are two possible outcomes:
            1. When providers have profits - they are distributed using win ledger
            2. When providers have losses - they are distributed using loss ledger
        *)

        (* TODO: this staircases look very complex, maybe there are a way to refactor them?
            -- but only after there are would some tests
            -- maybe use ledger with 4 keys, two of them options: (address*eventId*[For|Against]*[Liquidity|Bonus|Bet])?
            -- or maybe wrap profitOrLoss calculation into separate function and keep only one staircase? (<<this worth to try!)
        *)

        var providedLiquidityBonus : tez := 0tez;
        if event.isBetsForWin then
            if totalProfits > 0 then providedLiquidityBonus := getLedgerAmount(key, s.liquidityForBonusLedger)
            else providedLiquidityBonus := getLedgerAmount(key, s.liquidityAgainstBonusLedger)
        else
            if totalProfits > 0 then providedLiquidityBonus := getLedgerAmount(key, s.liquidityAgainstBonusLedger)
            else providedLiquidityBonus := getLedgerAmount(key, s.liquidityForBonusLedger);

        (* The same staicase for totalLiquidityBonusSum: *)
        var totalLiquidityBonusSum : tez := 0tez;
        if event.isBetsForWin then
            if totalProfits > 0 then totalLiquidityBonusSum := event.totalLiquidityForBonusSum
            else totalLiquidityBonusSum := event.totalLiquidityAgainstBonusSum
        else
            if totalProfits > 0 then totalLiquidityBonusSum := event.totalLiquidityAgainstBonusSum
            else totalLiquidityBonusSum := event.totalLiquidityForBonusSum;


        const profitOrLoss : tez =
            providedLiquidityBonus * abs(totalProfits) / totalLiquidityBonusSum * 1mutez;

        if totalProfits > 0 then liquidityPayout := providedLiquidity + profitOrLoss
        else liquidityPayout := providedLiquidity - profitOrLoss;

        event.withdrawnLiquidity := event.withdrawnLiquidity + liquidityPayout;

        (* Removing keys from liquidity ledgers *)
        s.providedLiquidityLedger := Big_map.remove(key, s.providedLiquidityLedger);
        s.liquidityForBonusLedger := Big_map.remove(key, s.liquidityForBonusLedger);
        s.liquidityAgainstBonusLedger := Big_map.remove(key, s.liquidityAgainstBonusLedger);
    }
    else skip;

    const totalPayoutAmount : tez = winPayout + liquidityPayout;
    const payoutOperation : operation = Tezos.transaction(unit, totalPayoutAmount, receiver);

    s.events[eventId] := event;

} with (list[payoutOperation], s)
