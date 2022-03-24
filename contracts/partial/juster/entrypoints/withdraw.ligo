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

    const isBetsAboveEqWin : bool = case event.isBetsAboveEqWin of [
    | Some(isWin) -> isWin
    (* should not be here: *)
    | None -> (failwith("Winner is undefined") : bool)
    ];

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
    const payout : nat) : nat is
block {
    (* fee cannot exceed payout: *)
    const maxFee = tezToNat(store.config.rewardCallFee);
    const fee = if payout < maxFee
        then payout
        else maxFee;

    (* fee can be extracted only if two conditions meet:
        - sender is not participant itself
        - after closing event timedelta was passed *)
    const closedTime = case event.closedOracleTime of [
    | Some(time) -> time
    | None -> (failwith("Wrong state: caulculating fee for unfinished event"): timestamp)
    ];

    const feeTime : timestamp = closedTime + int(store.config.rewardFeeSplitAfter);
    const senderCanGetFee = Tezos.now >= feeTime;
    const senderIsNotParticipant = Tezos.sender =/= params.participantAddress;

    const senderFee = if senderIsNotParticipant and senderCanGetFee
        then fee
        else 0n;
} with senderFee


function makePayoutOp(
    const payout : tez;
    const destination : address;
    const eventId : nat) : operation is
case (Tezos.get_entrypoint_opt("%payReward", destination) : option(contract(nat))) of [
| None -> Tezos.transaction(unit, payout, getReceiver(destination))
| Some(receiver) -> Tezos.transaction(eventId, payout, receiver)
];


function makeWithdrawOperations(
    const store : storage;
    const params : withdrawParams;
    const event : eventType;
    const payout : nat) : list(operation) is
block {

    const senderFee = calculateFee(store, params, event, payout);
    const netPayout = payout - senderFee;

    var operations : list(operation) := nil;

    if netPayout > 0
    then operations := makePayoutOp
        (natToTez(abs(netPayout)), params.participantAddress, params.eventId) # operations
    else skip;

    if senderFee > 0n
    then operations := Tezos.transaction 
        (unit, natToTez(senderFee), getReceiver(Tezos.sender)) # operations
    else skip;

} with operations;


function withdraw(
    const params : withdrawParams;
    var store: storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    const event : eventType = getEvent(store, params.eventId);
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
                makePayoutOp
                    (payoutValue, params.participantAddress, params.eventId)]
            else (nil: list(operation))
    }
    else block {
        const payout : payoutInfo = calculatePayout(store, event, key);
        store.retainedProfits := store.retainedProfits + natToTez(payout.fee);
        const payoutValue : nat = payout.bet + payout.provider;
        operations := makeWithdrawOperations(store, params, event, payoutValue);
    };

    if isParticipant(store, key) then skip else failwith("Participant not found");

    (* Checking that participant was not withdrawn before: *)
    if Big_map.mem(key, store.isWithdrawn) then failwith("Already withdrawn")
    else store.isWithdrawn := Big_map.add(key, Unit, store.isWithdrawn);

} with (operations, store)

