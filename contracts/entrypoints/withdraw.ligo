(* Returned record from calculatePayout function: *)
type payoutInfo is record [
    bet : nat;
    provider : nat;
    fee : nat;
]


function calculatePayout(
    const store: storage;
    const event : eventType;
    const key : ledgerKey) : payoutInfo is

block {

    (* Calculating bet return: *)
    const betA : nat = tezToNat(getLedgerAmount(key, store.betsAboveEq));
    const betB : nat = tezToNat(getLedgerAmount(key, store.betsBellow));
    const bet : nat = if event.isBetsAboveEqWin then betA else betB;

    (* Calculating provider return: *)
    const share : nat = getNatLedgerAmount(key, store.liquidityShares);
    const providedA : nat = tezToNat(
        getLedgerAmount(key, store.providedLiquidityAboveEq));
    const providedB : nat = tezToNat(
        getLedgerAmount(key, store.providedLiquidityBellow));
    const poolA : nat = tezToNat(event.poolAboveEq);
    const poolB : nat = tezToNat(event.poolBellow);
    const totalShares : nat = event.totalLiquidityShares;

    const providerProfit : int = if event.isBetsAboveEqWin
        then share * poolB / totalShares - providedB
        else share * poolA / totalShares - providedA;

    (* Cutting profits from provided liquidity: *)
    const profitFee : nat = store.config.providerProfitFee;
    const precision : nat = store.providerProfitFeePrecision;

    const fee : nat = if providerProfit > 0
        then abs(providerProfit) * profitFee / precision
        else 0n;

    if fee > abs(providerProfit) then failwith("Fee is more than 100%")
    else skip;

    const provider : nat = abs(providedA + providedB + providerProfit - fee);

} with record[bet=bet; provider=provider; fee=fee];


function forceMajeureReturnPayout(
    const store: storage;
    const key : ledgerKey) : tez is (
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
    const key : ledgerKey;
    const payout : tez) : list(operation) is
block {

    (* By default creating one operation to participantAddress: *)
    var operations : list(operation) :=
        makeOperationsIfNotZero(params.participantAddress, payout);

    (* If a lot time passed from closed time, splitting reward and
        rewriting operations: *)

    case event.closedOracleTime of
    | Some(time) -> block{
        const feeTime : timestamp = time + int(store.config.rewardFeeSplitAfter);

        if (Tezos.sender =/= params.participantAddress) and (Tezos.now >= feeTime)
        then operations := excludeFeeReward(store, params, payout)
        else skip;
    }
    | None -> skip
    end;

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
    const params : withdrawParams;
    var store: storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    const event : eventType = getEvent(store, params.eventId);
    const key : ledgerKey = (params.participantAddress, params.eventId);

    if event.isClosed then skip
    else failwith("Withdraw is not allowed until contract is closed");

    const payout : payoutInfo = calculatePayout(store, event, key);
    store.retainedProfits := store.retainedProfits + natToTez(payout.fee);
    const payoutValue : tez = natToTez(payout.bet + payout.provider);

    const operations : list(operation) = makeWithdrawOperations(
        store, params, event, key, payoutValue);

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
