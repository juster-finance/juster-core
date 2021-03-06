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
    store.maxEvents := store.maxEvents + line.maxEvents;

} with ((nil: list(operation)), store)


function depositLiquidity(
    var store : storage) : (list(operation) * storage) is
block {

    checkDepositIsNotPaused(store);

    const providedAmount = Tezos.amount / 1mutez;
    if providedAmount = 0n then failwith(PoolErrors.zeroAmount) else skip;

    const newEntry = record[
        provider = Tezos.sender;
        acceptAfter = Tezos.now + int(store.entryLockPeriod);
        amount = providedAmount;
    ];
    store.entries[store.nextEntryId] := newEntry;
    store.nextEntryId := store.nextEntryId + 1n;
    store.entryLiquidityF := store.entryLiquidityF + providedAmount * store.precision;

} with ((nil: list(operation)), store)


function approveLiquidity(
    const entryId : nat; var store : storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    const entry = getEntry(entryId, store);
    store.entries := Big_map.remove(entryId, store.entries);
    const provided = entry.amount;
    const providedF = entry.amount * store.precision;

    if Tezos.now < entry.acceptAfter
    then failwith(PoolErrors.earlyApprove)
    else skip;

    (* store.entryLiquidity is the sum of all entries, so the following
        condition should not be true but it is better to check *)
    if store.entryLiquidityF < providedF
    then failwith(PoolWrongState.negativeEntryLiquidity)
    else skip;

    store.entryLiquidityF := abs(store.entryLiquidityF - providedF);
    const totalLiquidityF = calcTotalLiquidityF(store);

    (* totalLiquidity includes provided liquidity so the following condition
        should not be true but it is better to check *)
    if totalLiquidityF < int(providedF)
    then failwith(PoolWrongState.negativeTotalLiquidity)
    else skip;

    const liquidityBeforeDepositF = abs(totalLiquidityF - providedF);

    const shares = if store.totalShares = 0n
        then provided
        else providedF * store.totalShares / liquidityBeforeDepositF;

    const newPosition = record [
        provider = entry.provider;
        shares = shares;
        entryLiquidityUnits = store.liquidityUnits;
    ];

    store.positions[store.nextPositionId] := newPosition;
    store.nextPositionId := store.nextPositionId + 1n;
    store.totalShares := store.totalShares + shares;

} with ((nil: list(operation)), store)


function cancelLiquidity(
    const entryId : nat; var store : storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    (* Cancel liquidity allowed only when deposit is set on pause: *)
    if not store.isDepositPaused
    then failwith(PoolErrors.cancelIsNotAllowed)
    else skip;

    const entry = getEntry(entryId, store);
    store.entries := Big_map.remove(entryId, store.entries);

    checkSenderIs(entry.provider, PoolErrors.notEntryOwner);

    const providedF = entry.amount * store.precision;
    if store.entryLiquidityF < providedF
    then failwith(PoolWrongState.negativeEntryLiquidity)
    else skip;

    store.entryLiquidityF := abs(store.entryLiquidityF - providedF);

    const operations = if entry.amount > 0n then
        list[prepareOperation(Tezos.sender, entry.amount * 1mutez)]
    else (nil: list(operation));

} with (operations, store)


function claimLiquidity(
    const claim : claimLiquidityParams;
    var store : storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    const position = getPosition(claim.positionId, store);
    checkSenderIs(position.provider, PoolErrors.notPositionOwner);

    if claim.shares > position.shares
    then failwith(PoolErrors.exceedClaimShares)
    else skip;
    const leftShares = abs(position.shares - claim.shares);

    var removedActive := 0n;

    if claim.shares = 0n
    then skip
    else block {
        (* TODO: it feels like it is possible to remove loop with new logic: *)
        for eventId -> _lineId in map store.activeEvents block {
            const event = getEvent(eventId, store);

            const key = record [
                eventId = eventId;
                positionId = claim.positionId;
            ];

            const alreadyClaimed = getClaimedAmount(key, store);

            (* TODO: check leftProvided > 0 and raise wrong state? *)
            const leftProvided = abs(event.provided - event.claimed);
            const newClaimF = (
                store.precision * claim.shares * leftProvided
                / store.totalShares
            );
            const newClaim = ceilDiv(newClaimF, store.precision);

            store.claims[key] := record [
                amount = alreadyClaimed + newClaim;
                provider = position.provider;
            ];

            removedActive := removedActive + newClaim;

            const newClaimed = event.claimed + newClaim;
            if newClaimed > event.provided
            then failwith(PoolWrongState.lockedExceedTotal)
            else skip;

            store.events[eventId] := event with record [
                claimed = newClaimed;
            ];
        }
    };

    const updatedPosition = position with record [ shares = leftShares ];
    store.positions[claim.positionId] := updatedPosition;

    const payoutValue = (
        calcFreeLiquidityF(store) * claim.shares
        / store.totalShares / store.precision
    );

    (* Having negative payoutValue should not be possible,
        but it is better to check: *)
    if payoutValue < 0
    then failwith(PoolWrongState.negativePayout)
    else skip;

    (* Another impossible condition that is better to check: *)
    if store.totalShares < claim.shares
    then failwith(PoolWrongState.negativeTotalShares)
    else skip;

    (* TODO: this block with failwith can be replaced with absOrFail *)
    store.totalShares := abs(store.totalShares - claim.shares);

    (* TODO: does this high precision still required for active liquidity calc?
        looks like it is not, consider removing it *)
    const removedActiveF = removedActive * store.precision;
    if store.activeLiquidityF < removedActiveF
    then failwith(PoolWrongState.negativeActiveLiquidity)
    else skip;

    store.activeLiquidityF := abs(store.activeLiquidityF - removedActiveF);

    const operations = if payoutValue > 0 then
        list[prepareOperation(Tezos.sender, abs(payoutValue) * 1mutez)]
    else (nil: list(operation));

    const newWithdrawal = record [
        liquidityUnits = abs(store.liquidityUnits - position.entryLiquidityUnits);
        positionId = claim.positionId;
        shares = claim.shares;
    ];

    (* TODO: store = addNewWithdrawal(store, newWithdrawal)
        and the same might be done in other places *)
    store.withdrawals[store.nextWithdrawalId] := newWithdrawal;
    store.nextWithdrawalId := store.nextWithdrawalId + 1n;

} with (operations, store)


function withdrawLiquidity(
    const withdrawRequests : withdrawLiquidityParams;
    var store : storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    var sums := (Map.empty : map(address, nat));
    for key in list withdrawRequests block {
        const event = getEvent(key.eventId, store);
        (* TODO: it might be better to (1) checkEventFinished(event) and then
            (2) use event.result (default: 0 and can't be None) with @inline
            and @inline calcEventReward(shares, event)
        *)
        const eventResult = getEventResult(event);
        const claim = getClaim(key, store);
        const eventRewardF = eventResult * claim.amount * store.precision / event.provided;

        sums[claim.provider] := case Map.find_opt(claim.provider, sums) of [
        | Some(sum) -> sum + eventRewardF
        | None -> eventRewardF
        ];

        store.claims := Big_map.remove(key, store.claims);
    };

    var operations := (nil : list(operation));
    for participant -> withdrawSumF in map sums block {
        const payout = withdrawSumF / store.precision * 1mutez;
        if payout > 0tez
        then operations := prepareOperation(participant, payout) # operations
        else skip;

        (* withdrawableLiquidity forms from Juster payments as a percentage for
            all locked claims so it should not be less than withdrawSum, so
            next case should not be possible: *)
        if withdrawSumF > store.withdrawableLiquidityF
        then failwith(PoolWrongState.negativeWithdrawableLiquidity)
        else skip;

        store.withdrawableLiquidityF := abs(store.withdrawableLiquidityF - withdrawSumF);
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
    const newWithdrawableF = (
        reward * event.claimed * store.precision / event.provided
    );
    store.withdrawableLiquidityF := store.withdrawableLiquidityF + newWithdrawableF;

    (* Part of activeLiquidity was already excluded if there was some claims *)
    const remainedLiquidityF = (event.provided - event.claimed) * store.precision;

    (* remainedLiquidity should always be less than store.activeLiquidity but
        it is better to cap it on zero if it somehow goes negative: *)
    store.activeLiquidityF := absPositive(store.activeLiquidityF - remainedLiquidityF);

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
    const nextLiquidity = calcLiquidityPayout(store);
    const liquidityPayout = excludeFee(nextLiquidity, newEventFee / 1mutez) * 1mutez;
    const provideLiquidityOperation = Tezos.transaction(
        provideLiquidity,
        liquidityPayout,
        getProvideLiquidityEntry(line.juster));

    const operations = list[newEventOperation; provideLiquidityOperation];
    const eventCosts = (liquidityPayout + newEventFee)/1mutez;

    const event = record [
        claimed = 0n;
        result = (None : option(nat));
        provided = eventCosts;
    ];

    store.events[nextEventId] := event;
    store.activeEvents := Map.add(nextEventId, lineId, store.activeEvents);
    store.activeLiquidityF := store.activeLiquidityF + eventCosts * store.precision;

    const newUnits = eventCosts * calcDuration(line) / store.totalShares;
    store.liquidityUnits := store.liquidityUnits + newUnits;

} with (operations, store)


function triggerPauseLine(const lineId : nat; var store : storage) is
block {
    checkNoAmountIncluded(unit);
    onlyManager(store.manager);

    const line = getLine(lineId, store);

    store.maxEvents := if line.isPaused
        then store.maxEvents + line.maxEvents
        else absOrFail(
            store.maxEvents - line.maxEvents,
            PoolWrongState.negativeEvents
        );

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


function default(var store : storage) is ((nil: list(operation)), store)


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
    calcLiquidityPayout(s)

[@view] function getLiquidityUnits(const _ : unit; const s: storage) is
    s.liquidityUnits

(* TODO: split this view or add here some info from other views: *)
[@view] function getStateValues(const _ : unit; const s: storage) is
    record [
        precision = s.precision;
        activeLiquidityF = s.activeLiquidityF;
        withdrawableLiquidityF = s.withdrawableLiquidityF;
        entryLiquidityF = s.entryLiquidityF;
        maxEvents = s.maxEvents
    ]
