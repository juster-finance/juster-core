#include "../partial/common_errors.ligo"
#include "../partial/common_helpers.ligo"
#include "../partial/juster/juster_types.ligo"
#include "../partial/pool/pool_errors.ligo"
#include "../partial/pool/pool_types.ligo"
#include "../partial/pool/pool_helpers.ligo"


function updateDurationPoints(const provider : address; const s : storageT) is {
    const initPoints : durationPointsT = record [
        amount = 0n;
        updateLevel = Tezos.get_level();
    ];
    const lastPoints = getOrDefault(provider, s.durationPoints, initPoints);
    const shares = getSharesOrZero(provider, s);
    const newBlocks = absPositive(Tezos.get_level() - lastPoints.updateLevel);
    const addedPoints = shares*newBlocks;
    const newPoints : durationPointsT = record [
        amount = lastPoints.amount + addedPoints;
        updateLevel = Tezos.get_level();
    ];
    const updStore = s with record [
        durationPoints = Big_map.update(provider, Some(newPoints), s.durationPoints);
        totalDurationPoints = s.totalDurationPoints + addedPoints;
    ]
} with updStore


function updateDurationPointsEntry(const provider : address; const s : storageT) is {
    checkNoAmountIncluded(unit);
} with (noOps, updateDurationPoints(provider, s))


function addLine(
    const line : lineT;
    var s : storageT) : (list(operation) * storageT) is
block {
    checkNoAmountIncluded(unit);
    onlyManager(s.manager);
    checkLineValid(line);

    s.lines[s.nextLineId] := line;
    s.nextLineId := s.nextLineId + 1n;
    if not line.isPaused
    then s.maxEvents := s.maxEvents + line.maxEvents
    else skip;

} with ((nil: list(operation)), s)


function depositLiquidity(
    var s : storageT) : (list(operation) * storageT) is
block {

    checkDepositIsNotPaused(s);

    const providedAmount = Tezos.get_amount() / 1mutez;
    if providedAmount = 0n then failwith(PoolErrors.zeroAmount) else skip;

    const newEntry = record[
        provider = Tezos.get_sender();
        acceptAfter = Tezos.get_now() + int(s.entryLockPeriod);
        amount = providedAmount;
    ];
    s.entries[s.nextEntryId] := newEntry;
    s.nextEntryId := s.nextEntryId + 1n;
    s.entryLiquidityF := s.entryLiquidityF + providedAmount * s.precision;

} with ((nil: list(operation)), s)


function approveEntry(
    const entryId : nat; var s : storageT) : (list(operation) * storageT) is
block {

    checkNoAmountIncluded(unit);

    const entry = getEntry(entryId, s);
    s.entries := Big_map.remove(entryId, s.entries);

    s := updateDurationPoints(entry.provider, s);
    const provided = entry.amount;
    const providedF = entry.amount * s.precision;

    (* TODO: wrap it into checkAcceptTime *)
    if Tezos.get_now() < entry.acceptAfter
    then failwith(PoolErrors.earlyApprove)
    else skip;

    (* s.entryLiquidity is the sum of all entries, so the following
        condition should not be true but it is better to check *)
    if s.entryLiquidityF < providedF
    then failwith(PoolWrongState.negativeEntryLiquidity)
    else skip;

    s.entryLiquidityF := abs(s.entryLiquidityF - providedF);
    const totalLiquidityF = calcTotalLiquidityF(s);

    (* totalLiquidity includes provided liquidity so the following condition
        should not be true but it is better to check *)
    if totalLiquidityF < int(providedF)
    then failwith(PoolWrongState.negativeTotalLiquidity)
    else skip;

    const liquidityBeforeDepositF = abs(totalLiquidityF - providedF);

    const shares = if s.totalShares = 0n
        then provided
        else providedF * s.totalShares / liquidityBeforeDepositF;

    s.shares[entry.provider] := getSharesOrZero(entry.provider, s) + shares;
    s.totalShares := s.totalShares + shares;

} with ((nil: list(operation)), s)


function cancelEntry(
    const entryId : nat; var s : storageT) : (list(operation) * storageT) is
block {

    checkNoAmountIncluded(unit);

    (* Cancel liquidity allowed only when deposit is set on pause: *)
    if not s.isDepositPaused
    then failwith(PoolErrors.cancelIsNotAllowed)
    else skip;

    const entry = getEntry(entryId, s);
    s.entries := Big_map.remove(entryId, s.entries);

    if not s.isDisbandAllow
    then checkSenderIs(entry.provider, PoolErrors.notEntryOwner)
    else skip;

    const providedF = entry.amount * s.precision;
    if s.entryLiquidityF < providedF
    then failwith(PoolWrongState.negativeEntryLiquidity)
    else skip;

    s.entryLiquidityF := abs(s.entryLiquidityF - providedF);

    const operations = if entry.amount > 0n then
        list[prepareOperation(entry.provider, entry.amount * 1mutez)]
    else (nil: list(operation));

} with (operations, s)


function claimLiquidity(
    const claim : claimLiquidityParamsT;
    var s : storageT) : (list(operation) * storageT) is
block {

    checkNoAmountIncluded(unit);
    s := updateDurationPoints(claim.provider, s);

    const shares = getSharesOrZero(claim.provider, s);

    (* If contract in disband state -> anyone can claim liquidity for anyone *)
    if not s.isDisbandAllow
    then checkSenderIs(claim.provider, PoolErrors.notSharesOwner)
    else skip;

    if claim.shares > shares
    then failwith(PoolErrors.exceedClaimShares)
    else skip;
    const leftShares = abs(shares - claim.shares);

    var removedActive := 0n;

    if claim.shares = 0n
    then skip
    else block {
        (* TODO: it feels like it is possible to remove loop with new logic: *)
        for eventId -> _lineId in map s.activeEvents block {
            const event = getEvent(eventId, s);

            const key = record [
                eventId = eventId;
                provider = claim.provider;
            ];

            const alreadyClaimed = getClaimedAmountOrZero(key, s);

            (* TODO: check leftProvided > 0 and raise wrong state?
                [it is very similar test bellow for newClaimed > event.provided] *)
            const leftProvided = abs(event.provided - event.claimed);
            const newClaimF = (
                s.precision * claim.shares * leftProvided
                / s.totalShares
            );
            const newClaim = ceilDiv(newClaimF, s.precision);

            s.claims[key] := alreadyClaimed + newClaim;
            removedActive := removedActive + newClaim;

            const newClaimed = event.claimed + newClaim;
            if newClaimed > event.provided
            then failwith(PoolWrongState.lockedExceedTotal)
            else skip;

            s.events[eventId] := event with record [
                claimed = newClaimed;
            ];
        }
    };

    s.shares[claim.provider] := leftShares;

    const payoutValue = (
        calcFreeLiquidityF(s) * claim.shares
        / s.totalShares / s.precision
    );

    (* Having negative payoutValue should not be possible,
        but it is better to check: *)
    if payoutValue < 0
    then failwith(PoolWrongState.negativePayout)
    else skip;

    (* Another impossible condition that is better to check: *)
    if s.totalShares < claim.shares
    then failwith(PoolWrongState.negativeTotalShares)
    else skip;

    (* TODO: this block with failwith can be replaced with absOrFail *)
    s.totalShares := abs(s.totalShares - claim.shares);

    (* TODO: does this high precision still required for active liquidity calc?
        looks like it is not, consider removing it *)
    const removedActiveF = removedActive * s.precision;
    if s.activeLiquidityF < removedActiveF
    then failwith(PoolWrongState.negativeActiveLiquidity)
    else skip;

    s.activeLiquidityF := abs(s.activeLiquidityF - removedActiveF);

    const operations = if payoutValue > 0 then
        list[prepareOperation(claim.provider, abs(payoutValue) * 1mutez)]
    else (nil: list(operation));

} with (operations, s)


function withdrawClaims(
    const withdrawRequests : withdrawClaimsParamsT;
    var s : storageT) : (list(operation) * storageT) is
block {

    checkNoAmountIncluded(unit);

    var sums := (Map.empty : map(address, nat));
    for key in list withdrawRequests block {
        const event = getEvent(key.eventId, s);
        (* TODO: it might be better to (1) checkEventFinished(event) and then
            (2) use event.result (default: 0 and can't be None) with @inline
            and @inline calcEventReward(shares, event)
        *)
        const eventResult = getEventResult(event);
        const claimAmount = getClaim(key, s);
        const eventRewardF = eventResult * claimAmount * s.precision / event.provided;

        sums[key.provider] := case Map.find_opt(key.provider, sums) of [
        | Some(sum) -> sum + eventRewardF
        | None -> eventRewardF
        ];

        s.claims := Big_map.remove(key, s.claims);
    };

    var operations := (nil : list(operation));
    for participant -> withdrawSumF in map sums block {
        const payout = withdrawSumF / s.precision * 1mutez;
        if payout > 0tez
        then operations := prepareOperation(participant, payout) # operations
        else skip;

        (* withdrawableLiquidity forms from Juster payments as a percentage for
            all locked claims so it should not be less than withdrawSum, so
            next case should not be possible: *)
        if withdrawSumF > s.withdrawableLiquidityF
        then failwith(PoolWrongState.negativeWithdrawableLiquidity)
        else skip;

        s.withdrawableLiquidityF := abs(s.withdrawableLiquidityF - withdrawSumF);
    }

} with (operations, s)


function payReward(
    const eventId : nat;
    var s : storageT) : (list(operation) * storageT) is
block {
    (* NOTE: this method based on assumption that payReward only called by
        Juster when event is finished / canceled *)
    const lineId = getLineIdByEventId(eventId, s);
    const line = getLine(lineId, s);
    checkSenderIs(line.juster, PoolErrors.notExpectedAddress);

    (* adding event result *)
    const reward = Tezos.get_amount() / 1mutez;
    var event := getEvent(eventId, s);
    event.result := Some(reward);
    s.events := Big_map.update(eventId, Some(event), s.events);
    s.activeEvents := Map.remove(eventId, s.activeEvents);

    (* adding withdrawable liquidity to the pool: *)
    const newWithdrawableF = (
        reward * event.claimed * s.precision / event.provided
    );
    s.withdrawableLiquidityF := s.withdrawableLiquidityF + newWithdrawableF;

    (* Part of activeLiquidity was already excluded if there was some claims *)
    const remainedLiquidityF = (event.provided - event.claimed) * s.precision;

    (* remainedLiquidity should always be less than s.activeLiquidity but
        it is better to cap it on zero if it somehow goes negative: *)
    s.activeLiquidityF := absPositive(s.activeLiquidityF - remainedLiquidityF);

} with ((nil: list(operation)), s)


function createEvent(
    const lineId : nat;
    var s : storageT) : (list(operation) * storageT) is
block {

    var line := getLine(lineId, s);
    const nextEventId = getNextEventId(line.juster);

    checkNoAmountIncluded(unit);
    checkHaveFreeEventSlots(s);
    checkLineIsNotPaused(line);
    checkEventNotDuplicated(nextEventId, s);
    checkLineHaveFreeSlots(lineId, line, s);
    checkReadyToEmitEvent(line);

    const nextBetsCloseTime = calcBetsCloseTime(line);
    line.lastBetsCloseTime := nextBetsCloseTime;
    s.lines[lineId] := line;

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
    const nextLiquidity = calcLiquidityPayout(s);
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

    s.events[nextEventId] := event;
    s.activeEvents := Map.add(nextEventId, lineId, s.activeEvents);
    s.activeLiquidityF := s.activeLiquidityF + eventCosts * s.precision;

} with (operations, s)


function triggerPauseLine(const lineId : nat; var s : storageT) is
block {
    checkNoAmountIncluded(unit);
    onlyManager(s.manager);

    const line = getLine(lineId, s);

    s.maxEvents := if line.isPaused
        then s.maxEvents + line.maxEvents
        else absOrFail(
            s.maxEvents - line.maxEvents,
            PoolWrongState.negativeEvents
        );

    s.lines[lineId] := line with record [isPaused = not line.isPaused];

} with ((nil: list(operation)), s)


function triggerPauseDeposit(var s : storageT) is
block {
    checkNoAmountIncluded(unit);
    onlyManager(s.manager);
    s.isDepositPaused := not s.isDepositPaused;
} with ((nil: list(operation)), s)


function setEntryLockPeriod(const newPeriod : nat; var s : storageT) is
block {
    checkNoAmountIncluded(unit);
    onlyManager(s.manager);
    s.entryLockPeriod := newPeriod;
} with ((nil: list(operation)), s)


function proposeManager(
    const proposedManager : address;
    var s : storageT) is
block {
    checkNoAmountIncluded(unit);
    onlyManager(s.manager);
    s.proposedManager := proposedManager;
} with ((nil: list(operation)), s)


function acceptOwnership(var s : storageT) is
block {
    checkNoAmountIncluded(unit);
    checkSenderIs(s.proposedManager, Errors.notProposedManager);
    s.manager := s.proposedManager;
} with ((nil: list(operation)), s)


function setDelegate(
    const newDelegate : option (key_hash);
    var s : storageT) is
block {
    checkNoAmountIncluded(unit);
    onlyManager(s.manager);
    const operations : list (operation) = list [Tezos.set_delegate(newDelegate)];
} with (operations, s)


function default(var s : storageT) is ((nil: list(operation)), s)


function disband(var s : storageT) is {
    checkNoAmountIncluded(unit);
    onlyManager(s.manager);
} with ((nil: list(operation)), s with record [isDisbandAllow = true])


(* entrypoints:
    - addLine: adding new line of typical events, only manager can add new lines
    - depositLiquidity: creating request for adding new liquidity
    - approveEntry: adds requested liquidity to the aggregator
    - cancelEntry: cancels request for adding new liquidity
    - claimLiquidity: creates request for withdraw liquidity from all current events
    - withdrawClaims: withdraws claimed events
    - payReward: callback that receives withdraws from Juster
    - createEvent: creates new event in line, anyone can call this
    - triggerPauseLine: pauses/unpauses given line by lineId
    - triggerPauseDeposit: pauses/unpauses deposit & approve liquidity entrypoints
    - SetEntryLockPeriod: sets amount of seconds that required to approve liquidity
    - ProposeManager: allows manager to propose new manager
    - AcceptOwnership: allows proposed manager to accept given rights
    - SetDelegate: allows to change delegate
    - Default: allows to receive funds from delegate
    - disband: allows anyone to claimLiquidity for everyone, used to emtpy pool
    - updateDurationPoints: forced update of provider integrated shares
*)

type action is
| AddLine of lineT
| DepositLiquidity of unit
| ApproveEntry of nat
| CancelEntry of nat
| ClaimLiquidity of claimLiquidityParamsT
| WithdrawClaims of withdrawClaimsParamsT
| PayReward of nat
| CreateEvent of nat
| TriggerPauseLine of nat
| TriggerPauseDeposit of unit
| SetEntryLockPeriod of nat
| ProposeManager of address
| AcceptOwnership of unit
| SetDelegate of option (key_hash)
| Default of unit
| Disband of unit
| UpdateDurationPoints of address


function main (const params : action; var s : storageT) : (list(operation) * storageT) is
case params of [
| AddLine(p) -> addLine(p, s)
| DepositLiquidity -> depositLiquidity(s)
| ApproveEntry(p) -> approveEntry(p, s)
| CancelEntry(p) -> cancelEntry(p, s)
| ClaimLiquidity(p) -> claimLiquidity(p, s)
| WithdrawClaims(p) -> withdrawClaims(p, s)
| PayReward(p) -> payReward(p, s)
| CreateEvent(p) -> createEvent(p, s)
| TriggerPauseLine(p) -> triggerPauseLine(p, s)
| TriggerPauseDeposit -> triggerPauseDeposit(s)
| SetEntryLockPeriod(p) -> setEntryLockPeriod(p, s)
| ProposeManager(p) -> proposeManager(p, s)
| AcceptOwnership -> acceptOwnership(s)
| SetDelegate(p) -> setDelegate(p, s)
| Default -> default(s)
| Disband -> disband(s)
| UpdateDurationPoints(p) -> updateDurationPointsEntry(p, s)
]

[@view] function getLine (const lineId : nat; const s: storageT) is
    Big_map.find_opt(lineId, s.lines)

[@view] function getEntry(const entryId : nat; const s: storageT) is
    Big_map.find_opt(entryId, s.entries)

[@view] function getNextEntryId(const _ : unit; const s: storageT) is
    s.nextEntryId

[@view] function getShares(const provider : address; const s: storageT) is
    Big_map.find_opt(provider, s.shares)

[@view] function getClaim(const claimId : claimKeyT; const s: storageT) is
    Big_map.find_opt(claimId, s.claims)

[@view] function getEvent(const eventId : nat; const s: storageT) is
    Big_map.find_opt(eventId, s.events)

[@view] function getTotalShares(const _ : unit; const s: storageT) is
    s.totalShares

[@view] function getActiveEvents(const _ : unit; const s: storageT) is
    s.activeEvents

[@view] function getNextLineId(const _ : unit; const s: storageT) is
    s.nextLineId

[@view] function getBalance (const _ : unit ; const _s: storageT) is
    Tezos.get_balance()

[@view] function isDepositPaused(const _ : unit; const s: storageT) is
    s.isDepositPaused

[@view] function getEntryLockPeriod(const _ : unit; const s: storageT) is
    s.entryLockPeriod

[@view] function getManager(const _ : unit; const s: storageT) is
    s.manager

[@view] function getNextLiquidity(const _ : unit; const s: storageT) is
    calcLiquidityPayout(s)

[@view] function getDurationPoints(const provider : address; const s: storageT) is
    Big_map.find_opt(provider, s.durationPoints)

[@view] function getTotalDurationPoints(const _ : unit; const s: storageT) is
    s.totalDurationPoints

(* TODO: split this view or add here some info from other views: *)
[@view] function getStateValues(const _ : unit; const s: storageT) is
    record [
        precision = s.precision;
        activeLiquidityF = s.activeLiquidityF;
        withdrawableLiquidityF = s.withdrawableLiquidityF;
        entryLiquidityF = s.entryLiquidityF;
        maxEvents = s.maxEvents
    ]
