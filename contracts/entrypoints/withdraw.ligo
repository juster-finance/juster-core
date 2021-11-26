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
    const betB : nat = tezToNat(getLedgerAmount(key, store.betsBelow));

    const isBetsAboveEqWin : bool = case event.isBetsAboveEqWin of
    | Some(isWin) -> isWin
    (* should not be here: *)
    | None -> (failwith("Winner is undefined") : bool)
    end;

    const bet : nat = if isBetsAboveEqWin then betA else betB;

    (* Calculating provider return: *)
    const share : nat = getNatLedgerAmount(key, store.liquidityShares);
    const providedA : nat = tezToNat(
        getLedgerAmount(key, store.providedLiquidityAboveEq));
    const providedB : nat = tezToNat(
        getLedgerAmount(key, store.providedLiquidityBelow));
    const deposited : nat = tezToNat(
        getLedgerAmount(key, store.depositedLiquidity));
    const poolA : nat = tezToNat(event.poolAboveEq);
    const poolB : nat = tezToNat(event.poolBelow);
    const totalShares : nat = event.totalLiquidityShares;

    (* Leveraged liquidity provided in the smallest pool should be excluded: *)
    var providerProfit : int := 0;

    (* One of the edgecases if there was no liquidity provided and there are 0n shares: *)
    if (totalShares = 0n) then skip else
        providerProfit := if isBetsAboveEqWin
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

    const provider : nat = abs(deposited + providerProfit - fee);

} with record[bet=bet; provider=provider; fee=fee];


function forceMajeureReturnPayout(
    const store: storage;
    const key : ledgerKey) : tez is
        getLedgerAmount(key, store.depositedBets)
        + getLedgerAmount(key, store.depositedLiquidity);


function calculateFee(
    const store : storage;
    const params : withdrawParams;
    const event : eventType;
    const payout : tez) : tez is
block {
    (* fee cannot exceed payout: *)
    const fee = if payout < store.config.rewardCallFee
        then payout
        else store.config.rewardCallFee;

    (* fee can be extracted only if two conditions meet:
        - sender is not participant itself
        - after closing event timedelta was passed *)
    const closedTime = case event.closedOracleTime of
    | Some(time) -> time
    | None -> (failwith("Wrong state: caulculating fee for unfinished event"): timestamp)
    end;

    const feeTime : timestamp = closedTime + int(store.config.rewardFeeSplitAfter);
    const senderCanGetFee = Tezos.now >= feeTime;
    const senderIsNotParticipant = Tezos.sender =/= params.participantAddress;

    const senderFee = if senderIsNotParticipant and senderCanGetFee
        then fee
        else 0tez;
} with senderFee


function makeParticipantPayoutOperation(
    const payout : tez;
    const destination : address;
    const eventId : nat) : operation is
case (Tezos.get_entrypoint_opt("%payReward", destination) : option(contract(nat))) of
| None -> Tezos.transaction(unit, payout, getReceiver(destination))
| Some(receiver) -> Tezos.transaction(eventId, payout, receiver)
end;


function makeWithdrawOperations(
    const store : storage;
    const params : withdrawParams;
    const event : eventType;
    const payout : tez) : list(operation) is
block {

    const senderFee = calculateFee(store, params, event, payout);
    const participantPayout = payout - senderFee;

    var operations : list(operation) := nil;

    if participantPayout > 0tez
    then operations := makeParticipantPayoutOperation
        (participantPayout, params.participantAddress, params.eventId) # operations
    else skip;

    if senderFee > 0tez
    then operations := Tezos.transaction 
        (unit, senderFee, getReceiver(Tezos.sender)) # operations
    else skip;

} with operations;


(* Removing key from all ledgers: *)
function removeKeyFromAllLedgers(
    var store : storage;
    const key : ledgerKey) : storage is
block {

    store.betsAboveEq := Big_map.remove(key, store.betsAboveEq);
    store.betsBelow := Big_map.remove(key, store.betsBelow);
    store.providedLiquidityAboveEq :=
        Big_map.remove(key, store.providedLiquidityAboveEq);
    store.providedLiquidityBelow :=
        Big_map.remove(key, store.providedLiquidityBelow);
    store.liquidityShares := Big_map.remove(key, store.liquidityShares);
    store.depositedBets := Big_map.remove(key, store.depositedBets);
    store.depositedLiquidity := Big_map.remove(key, store.depositedLiquidity);

} with store


function withdraw(
    const params : withdrawParams;
    var store: storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    var event : eventType := getEvent(store, params.eventId);
    const key : ledgerKey = (params.participantAddress, params.eventId);

    if event.isClosed then skip
    else failwith("Withdraw is not allowed until event is closed");

    var operations : list(operation) := nil;

    (* If Force Majeure was activated, returning all bets and provided liquidity.
        - in force majeure reward fee split should be not active so it is
        just rewriting all operations: *)
    if event.isForceMajeure then
    block {
        const payoutValue : tez = forceMajeureReturnPayout(store, key);
        operations := if payoutValue > 0tez
            then list[
                makeParticipantPayoutOperation
                    (payoutValue, params.participantAddress, params.eventId)]
            else (nil: list(operation))
    }
    else block {
        const payout : payoutInfo = calculatePayout(store, event, key);
        store.retainedProfits := store.retainedProfits + natToTez(payout.fee);
        const payoutValue : tez = natToTez(payout.bet + payout.provider);
        operations := makeWithdrawOperations(store, params, event, payoutValue);
    };

    (* Decreasing participants count: *)
    if isParticipant(store, key)
    then event.participants := abs(event.participants - 1n)
    else failwith("Participant not found");

    store := removeKeyFromAllLedgers(store, key);

    (* If there are no participants in event left: removing event: *)
    if event.participants = 0n
    then store.events := Big_map.remove(params.eventId, store.events)
    else store.events[params.eventId] := event;

} with (operations, store)
