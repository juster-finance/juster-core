#include "../partial/common_errors.ligo"
#include "../partial/common_helpers.ligo"
#include "../partial/juster/juster_types.ligo"
#include "../partial/pool/pool_errors.ligo"
#include "../partial/pool/pool_types.ligo"
#include "../partial/pool/pool_helpers.ligo"


function addLine(
    const line : lineType;
    var store : storage) : (list(operation) * storage) is
block {
    checkNoAmountIncluded(unit);
    onlyManager(store.manager);
    checkLineValid(line);

    (* TODO: consider lines to be list {but then it will be harder to stop them?} *)

    store.lines[store.nextLineId] := line;
    store.nextLineId := store.nextLineId + 1n;
    store := increaseMaxActiveEvents(line.maxEvents, store);

} with ((nil: list(operation)), store)


function depositLiquidity(
    var store : storage) : (list(operation) * storage) is
block {

    checkDepositIsNotPaused(store);

    const providedAmount = Tezos.amount / 1mutez;
    if providedAmount = 0n then failwith("Should provide tez") else skip;

    const newEntry = record[
        provider = Tezos.sender;
        acceptAfter = Tezos.now + int(store.entryLockPeriod);
        amount = providedAmount;
    ];
    store.entries[store.nextEntryId] := newEntry;
    store.nextEntryId := store.nextEntryId + 1n;
    store.entryLiquidity := store.entryLiquidity + providedAmount;

} with ((nil: list(operation)), store)


function approveLiquidity(
    const entryId : nat; var store : storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    const entry = getEntry(entryId, store);
    store.entries := Big_map.remove(entryId, store.entries);

    if Tezos.now < entry.acceptAfter
    then failwith(PoolErrors.earlyApprove)
    else skip;

    (* store.entryLiquidity is the sum of all entries, so the following
        condition should not be true but it is better to check *)
    if store.entryLiquidity < entry.amount
    then failwith(PoolErrors.wrongState)
    else skip;

    store.entryLiquidity := abs(store.entryLiquidity - entry.amount);

    (* if there are no lines, then it is impossible to calculate providedPerEvent
        and there would be DIV/0 error *)
    checkHasActiveEvents(store);

    (* calculating shares *)
    const provided = entry.amount;
    const totalLiquidity = calcTotalLiquidity(store);

    (* totalLiquidity includes provided liquidity so the following condition
        should not be true but it is better to check *)
    if totalLiquidity < int(provided)
    then failwith(PoolErrors.wrongState)
    else skip;

    const liquidityBeforeDeposit = abs(totalLiquidity - provided);

    const shares = if store.totalShares = 0n
        then provided
        else provided * store.totalShares / liquidityBeforeDeposit;

    const newPosition = record [
        provider = entry.provider;
        shares = shares;
        addedCounter = store.counter;
        entryLiquidityUnits = store.liquidityUnits;
    ];

    store.positions[store.nextPositionId] := newPosition;
    store.nextPositionId := store.nextPositionId + 1n;
    store.totalShares := store.totalShares + shares;
    store.counter := store.counter + 1n;
    const providedPerEvent = provided * store.precision / store.maxEvents;
    store.nextLiquidity := store.nextLiquidity + providedPerEvent;

} with ((nil: list(operation)), store)


function cancelLiquidity(
    const entryId : nat; var store : storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    const entry = getEntry(entryId, store);
    store.entries := Big_map.remove(entryId, store.entries);

    checkSenderIs(entry.provider, PoolErrors.notEntryOwner);

    store.entryLiquidity := abs(store.entryLiquidity - entry.amount);

    const operations = if entry.amount > 0n then
        list[prepareOperation(Tezos.sender, entry.amount * 1mutez)]
    else (nil: list(operation));

} with (operations, store)


function claimLiquidity(
    const params : claimLiquidityParams;
    var store : storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    const position = getPosition(params.positionId, store);
    checkSenderIs(position.provider, PoolErrors.notPositionOwner);

    if params.shares > position.shares then
        failwith("Claim shares is exceed position shares")
    else skip;
    const leftShares = abs(position.shares - params.shares);

    var providedSum := 0n;

    for eventId -> _lineId in map store.activeEvents block {
        const event = getEvent(eventId, store);
        const isImpactedEvent = position.addedCounter < event.createdCounter;
        const isHaveShares = params.shares > 0n;

        // if isShouldBeClaimed(position, event, params)
        if isImpactedEvent and isHaveShares
        then block {
            const key = record [
                eventId = eventId;
                positionId = params.positionId;
            ];

            store.claims[key] := record [
                shares = getClaimedShares(key, store) + params.shares;
                provider = position.provider;
            ];

            providedSum := providedSum + calcEventProvided(params.shares, event);
            store.events[eventId] := increaseLocked(params.shares, event);
        }
        else skip;
    };

    const updatedPosition = record [
        provider = position.provider;
        shares = leftShares;
        addedCounter = position.addedCounter;
        entryLiquidityUnits = position.entryLiquidityUnits;
    ];

    store.positions[params.positionId] := updatedPosition;

    const totalLiquidity = calcTotalLiquidity(store);
    const userLiquidity = params.shares * totalLiquidity / store.totalShares;
    const payoutValue = userLiquidity - providedSum;

    (* Having negative payoutValue should not be possible,
        but it is better to check: *)
    if payoutValue < 0
    then failwith(PoolErrors.wrongState)
    else skip;

    const liquidityPerEvent = userLiquidity * store.precision / store.maxEvents;

    (* TODO: is it possible to have liquidityPerEvent > store.nextLiquidity ?
        - is it better to failwith here with wrongState? *)
    store.nextLiquidity :=
        absPositive(store.nextLiquidity - liquidityPerEvent);

    (* Another impossible condition that is better to check: *)
    if store.totalShares < params.shares
    then failwith(PoolErrors.wrongState)
    else skip;

    store.totalShares := abs(store.totalShares - params.shares);

    (* activeLiquidity cannot be less than providedLiquidity because it is
        provided liquidity that used in evetns (so it is part of activeLiquidity
        but it is better to check: *)
    if store.activeLiquidity < providedSum
    then failwith(PoolErrors.wrongState)
    else skip;

    store.activeLiquidity := abs(store.activeLiquidity - providedSum);

    const operations = if payoutValue > 0 then
        list[prepareOperation(Tezos.sender, abs(payoutValue) * 1mutez)]
    else (nil: list(operation));

    const newWithdrawal = record [
        liquidityUnits = abs(store.liquidityUnits - position.entryLiquidityUnits);
        positionId = params.positionId;
        shares = params.shares;
    ];
    store.withdrawals[store.nextWithdrawalId] := newWithdrawal;
    store.nextWithdrawalId := store.nextWithdrawalId + 1n;

} with (operations, store)


function withdrawLiquidity(
    const withdrawRequests : withdrawLiquidityParams;
    var store : storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    var withdrawalSums := (Map.empty : map(address, nat));
    for key in list withdrawRequests block {
        const event = getEvent(key.eventId, store);
        const eventResult = case event.result of [
        | Some(result) -> result
        | None -> (failwith("Event result is not received yet") : nat)
        ];

        const claim = case Big_map.find_opt(key, store.claims) of [
        | Some(claim) -> claim
        | None -> (failwith("Claim is not found") : claimParams)
        ];

        const eventReward = eventResult * claim.shares / event.totalShares;

        const updatedSum = case Map.find_opt(claim.provider, withdrawalSums) of [
        | Some(sum) -> sum + eventReward
        | None -> eventReward
        ];

        withdrawalSums := Map.update(claim.provider, Some(updatedSum), withdrawalSums);

        store.claims := Big_map.remove(key, store.claims);
    };

    var operations := (nil : list(operation));
    for participant -> withdrawSum in map withdrawalSums block {
        const payout = withdrawSum * 1mutez;
        if payout > 0tez
        then operations := prepareOperation(participant, payout) # operations
        else skip;

        (* withdrawableLiquidity forms from Juster payments as a percentage for
            all locked claims so it should not be less than withdrawSum, so
            next case should not be possible: *)
        if withdrawSum > store.withdrawableLiquidity
        then failwith(PoolErrors.wrongState)
        else skip;

        store.withdrawableLiquidity := abs(store.withdrawableLiquidity - withdrawSum);
    }

} with (operations, store)


function payReward(
    const eventId : nat;
    var store : storage) : (list(operation) * storage) is
block {
    (* NOTE: this method based on assumption that payReward only called by
        Juster when event is finished / canceled *)
    const lineId = getLineIdByEventId(eventId, store);
    const line = getLine(lineId, store);
    checkSenderIs(line.juster, PoolErrors.notExpectedAddress);

    (* adding event result *)
    const reward = Tezos.amount / 1mutez;
    var event := getEvent(eventId, store);
    event.result := Some(reward);
    store.events := Big_map.update(eventId, Some(event), store.events);
    store.activeEvents := Map.remove(eventId, store.activeEvents);

    (* adding withdrawable liquidity to the pool: *)
    const newWithdrawable = reward * event.lockedShares / event.totalShares;

    store.withdrawableLiquidity := store.withdrawableLiquidity + newWithdrawable;

    (* Part of activeLiquidity was already excluded if there was some claims *)
    const claimedLiquidity = event.provided * event.lockedShares / event.totalShares;
    const remainedLiquidity = event.provided - claimedLiquidity;

    (* remainedLiquidity should always be less than store.activeLiquidity but
        it is better to cap it on zero if it somehow goes negative: *)
    store.activeLiquidity := absPositive(store.activeLiquidity - remainedLiquidity);

    const profitLossPerEvent = (reward - event.provided) * store.precision / store.maxEvents;
    const lockedProfit = profitLossPerEvent * event.lockedShares / event.totalShares;
    const remainedProfit = profitLossPerEvent - lockedProfit;

    (* TODO: is it possible to make nextLiquidity < 0? when liquidity withdrawn
        for example and then failed event? Its good to be sure that it is impossible *)
    (* TODO: need to find this test cases if it is possible or find some proof that it is not *)
    store.nextLiquidity := absPositive(store.nextLiquidity + remainedProfit);
    (* TODO: consider failwith here instead of absPositive
        the same for store.activeLiquidity, but don't want to block this entrypoint *)

} with ((nil: list(operation)), store)


function createEvent(
    const lineId : nat;
    var store : storage) : (list(operation) * storage) is
block {

    var line := getLine(lineId, store);
    const nextEventId = getNextEventId(line.juster);

    checkNoAmountIncluded(unit);
    checkHaveFreeEventSlots(store);
    checkLineIsNotPaused(line);
    checkEventNotDuplicated(nextEventId, store);
    checkLineHaveFreeSlots(lineId, line, store);
    checkReadyToEmitEvent(line);

    const nextBetsCloseTime = calcBetsCloseTime(line);
    line.lastBetsCloseTime := nextBetsCloseTime;
    store.lines[lineId] := line;

    const newEvent = record [
        currencyPair = line.currencyPair;
        targetDynamics = line.targetDynamics;
        betsCloseTime = nextBetsCloseTime;
        measurePeriod = line.measurePeriod;
        liquidityPercent = line.liquidityPercent;
    ];

    const newEventFee = getNewEventFee(line.juster);
    const newEventOperation = Tezos.transaction(
        newEvent,
        newEventFee,
        getNewEventEntry(line.juster));

    (* TODO: is it possible to have some hook (view) to calculate line ratios?
        using data from another contract? *)
    const provideLiquidity = record [
        eventId = nextEventId;
        expectedRatioAboveEq = line.rateAboveEq;
        expectedRatioBelow = line.rateBelow;
        maxSlippage = 0n;
    ];

    (* TODO: is it possible to have some hook (view) to adjust payout?
        so it will allow to change line priorities and reallocate funds using token *)
    const liquidityPayout = calcLiquidityPayout(store, newEventFee);
    const provideLiquidityOperation = Tezos.transaction(
        provideLiquidity,
        liquidityPayout,
        getProvideLiquidityEntry(line.juster));

    const operations = list[newEventOperation; provideLiquidityOperation];
    const eventCosts = (liquidityPayout + newEventFee)/1mutez;

    const event = record [
        createdCounter = store.counter;
        totalShares = store.totalShares;
        lockedShares = 0n;
        result = (None : option(nat));
        provided = eventCosts;
    ];

    store.events[nextEventId] := event;
    store.activeEvents := Map.add(nextEventId, lineId, store.activeEvents);
    store.activeLiquidity := store.activeLiquidity + eventCosts;

    const newUnits = eventCosts * calcDuration(line) / store.totalShares;
    store.liquidityUnits := store.liquidityUnits + newUnits;
    store.counter := store.counter + 1n;

} with (operations, store)


function triggerPauseLine(const lineId : nat; var store : storage) is
block {
    checkNoAmountIncluded(unit);
    onlyManager(store.manager);

    const line = getLine(lineId, store);

    store := if line.isPaused
        then increaseMaxActiveEvents(line.maxEvents, store)
        else decreaseMaxActiveEvents(line.maxEvents, store);

    store.lines[lineId] := line with record [isPaused = not line.isPaused];

} with ((nil: list(operation)), store)


function triggerPauseDeposit(var store : storage) is
block {
    checkNoAmountIncluded(unit);
    onlyManager(store.manager);
    store.isDepositPaused := not store.isDepositPaused;
} with ((nil: list(operation)), store)


function setEntryLockPeriod(const newPeriod : nat; var store : storage) is
block {
    checkNoAmountIncluded(unit);
    onlyManager(store.manager);
    store.entryLockPeriod := newPeriod;
} with ((nil: list(operation)), store)


function proposeManager(
    const proposedManager : address;
    var store : storage) is
block {
    checkNoAmountIncluded(unit);
    onlyManager(store.manager);
    store.proposedManager := proposedManager;
} with ((nil: list(operation)), store)


function acceptOwnership(var store : storage) is
block {
    checkNoAmountIncluded(unit);
    checkSenderIs(store.proposedManager, Errors.notProposedManager);
    store.manager := store.proposedManager;
} with ((nil: list(operation)), store)


function setDelegate(
    const newDelegate : option (key_hash);
    var store : storage) is
block {
    checkNoAmountIncluded(unit);
    onlyManager(store.manager);
    const operations : list (operation) = list [Tezos.set_delegate(newDelegate)];
} with (operations, store)


function default(var store : storage) is
block {
    (* If there are no active lines this entrypoint is disabled *)
    checkHasActiveEvents(store);
    const distributedAmount =
        Tezos.amount / 1mutez * store.precision / store.maxEvents;
    store.nextLiquidity := store.nextLiquidity + distributedAmount;
} with ((nil: list(operation)), store)


(* entrypoints:
    - addLine: adding new line of typical events, only manager can add new lines
    - depositLiquidity: creating request for adding new liquidity
    - approveLiquidity: adds requested liquidity to the aggregator
    - cancelLiquidity: cancels request for adding new liquidity
    - claimLiquidity: creates request for withdraw liquidity from all current events
    - withdrawLiquidity: withdraws claimed events
    - payReward: callback that receives withdraws from Juster
    - createEvent: creates new event in line, anyone can call this
    - triggerPauseLine: pauses/unpauses given line by lineId
    - triggerPauseDeposit: pauses/unpauses deposit & approve liquidity entrypoints
    - SetEntryLockPeriod: sets amount of seconds that required to approve liquidity
    - ProposeManager: allows manager to propose new manager
    - AcceptOwnership: allows proposed manager to accept given rights
    - SetDelegate: allows to change delegate
    - Default: allows to receive funds from delegate
*)

type action is
| AddLine of lineType
| DepositLiquidity of unit
| ApproveLiquidity of nat
| CancelLiquidity of nat
| ClaimLiquidity of claimLiquidityParams
| WithdrawLiquidity of withdrawLiquidityParams
| PayReward of nat
| CreateEvent of nat
| TriggerPauseLine of nat
| TriggerPauseDeposit of unit
| SetEntryLockPeriod of nat
| ProposeManager of address
| AcceptOwnership of unit
| SetDelegate of option (key_hash)
| Default of unit


function main (const params : action; var s : storage) : (list(operation) * storage) is
case params of [
| AddLine(p) -> addLine(p, s)
| DepositLiquidity -> depositLiquidity(s)
| ApproveLiquidity(p) -> approveLiquidity(p, s)
| CancelLiquidity(p) -> cancelLiquidity(p, s)
| ClaimLiquidity(p) -> claimLiquidity(p, s)
| WithdrawLiquidity(p) -> withdrawLiquidity(p, s)
| PayReward(p) -> payReward(p, s)
| CreateEvent(p) -> createEvent(p, s)
| TriggerPauseLine(p) -> triggerPauseLine(p, s)
| TriggerPauseDeposit -> triggerPauseDeposit(s)
| SetEntryLockPeriod(p) -> setEntryLockPeriod(p, s)
| ProposeManager(p) -> proposeManager(p, s)
| AcceptOwnership -> acceptOwnership(s)
| SetDelegate(p) -> setDelegate(p, s)
| Default -> default(s)
]

[@view] function getLine (const lineId : nat; const s: storage) is
    Big_map.find_opt(lineId, s.lines)

[@view] function getEntry(const entryId : nat; const s: storage) is
    Big_map.find_opt(entryId, s.entries)

[@view] function getNextEntryId(const _ : unit; const s: storage) is
    s.nextEntryId

[@view] function getPosition(const positionId : nat; const s: storage) is
    Big_map.find_opt(positionId, s.positions)

[@view] function getNextPositionId(const _ : unit; const s: storage) is
    s.nextPositionId

[@view] function getClaim(const claimId : claimKey; const s: storage) is
    Big_map.find_opt(claimId, s.claims)

[@view] function getWithdrawal(const withdrawalId : nat; const s: storage) is
    Big_map.find_opt(withdrawalId, s.withdrawals)

[@view] function getNextWithdrawalId(const _ : unit; const s: storage) is
    s.nextWithdrawalId

[@view] function getEvent(const eventId : nat; const s: storage) is
    Big_map.find_opt(eventId, s.events)

[@view] function getTotalShares(const _ : unit; const s: storage) is
    s.totalShares

(* TODO: the following views are commented out because LIGO 0.38.1 doesn't allow
    to compile contract with > 10 views, issue 1388 *)

(*
[@view] function getActiveEvents(const _ : unit; const s: storage) is
    s.activeEvents

[@view] function getNextLineId(const _ : unit; const s: storage) is
    s.nextLineId

[@view] function getBalance (const _ : unit ; const _s: storage) is
    Tezos.balance

[@view] function isDepositPaused(const _ : unit; const s: storage) is
    s.isDepositPaused

[@view] function getEntryLockPeriod(const _ : unit; const s: storage) is
    s.entryLockPeriod

[@view] function getManager(const _ : unit; const s: storage) is
    s.manager

[@view] function getNextLiquidity(const _ : unit; const s: storage) is
    s.nextLiquidity

[@view] function getLiquidityUnits(const _ : unit; const s: storage) is
    s.liquidityUnits

[@view] function getStateValues(const _ : unit; const s: storage) is
    record [
        activeLiquidity = s.activeLiquidity;
        withdrawableLiquidity = s.withdrawableLiquidity;
        entryLiquidity = s.entryLiquidity;
        counter = s.counter;
        maxEvents = s.maxEvents
    ]
*)
