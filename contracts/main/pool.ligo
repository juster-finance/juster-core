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
    store := increaseMaxActiveEvents(line.maxActiveEvents, store);

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
    ];

    store.positions[store.nextPositionId] := newPosition;
    store.nextPositionId := store.nextPositionId + 1n;
    store.totalShares := store.totalShares + shares;
    store.counter := store.counter + 1n;
    const providedPerEvent = provided / store.maxActiveEvents;
    store.nextEventLiquidity := store.nextEventLiquidity + providedPerEvent;

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
    var providedLiquiditySum := 0n;

    (* TODO: refactor this loop and simplify this code *)
    for eventId -> _lineId in map store.activeEvents block {
        const key = record [
            eventId = eventId;
            positionId = params.positionId;
        ];

        var event := getEvent(eventId, store);

        (* checking if this claim already have some shares: *)
        const alreadyClaimedShares = case Big_map.find_opt(key, store.claims) of
        | Some(claim) -> claim.shares
        | None -> 0n
        end;

        const updatedClaim = record [
            shares = alreadyClaimedShares + params.shares;
            provider = position.provider;
        ];

        const isImpactedEvent = position.addedCounter < event.createdCounter;
        const isHaveShares = params.shares > 0n;

        if isImpactedEvent and isHaveShares
        then block {
            store.claims := Big_map.update(key, Some(updatedClaim), store.claims);

            const providedLiquidity = params.shares * event.provided / event.totalShares;
            providedLiquiditySum := providedLiquiditySum + providedLiquidity;

            event.lockedShares := event.lockedShares + params.shares;

            if event.lockedShares > event.totalShares
            then failwith(PoolErrors.wrongState)
            else skip;
        }
        else skip;

        store.events := Big_map.update(eventId, Some(event), store.events);
    };

    const updatedPosition = record [
        provider = position.provider;
        shares = leftShares;
        addedCounter = position.addedCounter;
    ];

    store.positions := if leftShares > 0n
    then Big_map.update(params.positionId, Some(updatedPosition), store.positions);
    else Big_map.remove(params.positionId, store.positions);

    const totalLiquidity = calcTotalLiquidity(store);
    const participantLiquidity = params.shares * totalLiquidity / store.totalShares;
    const payoutValue = participantLiquidity - providedLiquiditySum;

    (* Having negative payoutValue should not be possible,
        but it is better to check: *)
    if payoutValue < 0
    then failwith(PoolErrors.wrongState)
    else skip;

    (* TODO: make you sure that it is required to distribute
        participantLiquidity and not payoutValue instead
        {is there any tests for this difference?}
        payoutValue is part of liquidity that user can withdraw right now,
        but next event liquidity should be reduced with all removed liquidity
    *)
    const liquidityPerEvent = participantLiquidity / store.maxActiveEvents;

    (* TODO: is it possible to have liquidityPerEvent > store.nextEventLiquidity ?
        - is it better to failwith here with wrongState? *)
    store.nextEventLiquidity :=
        absPositive(store.nextEventLiquidity - liquidityPerEvent);

    (* Another impossible condition that is better to check: *)
    if store.totalShares < params.shares
    then failwith(PoolErrors.wrongState)
    else skip;

    store.totalShares := abs(store.totalShares - params.shares);

    (* activeLiquidity cannot be less than providedLiquidity because it is
        provided liquidity that used in evetns (so it is part of activeLiquidity
        but it is better to check: *)
    if store.activeLiquidity < store.activeLiquidity
    then failwith(PoolErrors.wrongState)
    else skip;

    store.activeLiquidity := abs(store.activeLiquidity - providedLiquiditySum);

    const operations = if payoutValue > 0 then
        list[prepareOperation(Tezos.sender, abs(payoutValue) * 1mutez)]
    else (nil: list(operation));

    (* TODO: add new withdrawalStat position with data that can be used in reward programs? *)

} with (operations, store)


function withdrawLiquidity(
    const withdrawRequests : withdrawLiquidityParams;
    var store : storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    var withdrawalSums := (Map.empty : map(address, nat));
    for key in list withdrawRequests block {
        const event = getEvent(key.eventId, store);
        const eventResult = case event.result of
        | Some(result) -> result
        | None -> (failwith("Event result is not received yet") : nat)
        end;

        const claim = case Big_map.find_opt(key, store.claims) of
        | Some(claim) -> claim
        | None -> (failwith("Claim is not found") : claimParams)
        end;

        const eventReward = eventResult * claim.shares / event.totalShares;

        const updatedSum = case Map.find_opt(claim.provider, withdrawalSums) of
        | Some(sum) -> sum + eventReward
        | None -> eventReward
        end;

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

    (* TODO: consider removing events when they are fully withdrawn?
        Alternative: moving event result to separate ledger and remove event
        when payReward received
        {2022-03-11: it might be good to keep events to use it in reward programs}
    *)

} with (operations, store)


function payReward(
    const eventId : nat;
    var store : storage) : (list(operation) * storage) is
block {
    (* TODO: assert that Tezos.sender is store.juster {or one of possible justers}
        maybe it is possible to keep juster address in line and get it using
        eventId {but it might be confusing if two Juster contracts will have the
        same ids: this might be solved if juster address added to eventId key}
    *)
    (* NOTE: this method based on assumption that payReward only called by
        Juster when event is finished / canceled *)

    (* adding event result *)
    const reward = Tezos.amount / 1mutez;
    var event := getEvent(eventId, store);
    event.result := Some(reward);
    store.events := Big_map.update(eventId, Some(event), store.events);
    store.activeEvents := Map.remove(eventId, store.activeEvents);

    (* adding withdrawable liquidity to the pool: *)
    const newWithdrawable = reward * event.lockedShares / event.totalShares;

    store.withdrawableLiquidity := store.withdrawableLiquidity + newWithdrawable;

    (* TODO: is it possible that this withdrawableLiquidity would be less than
        the sum of the claims because of the nat divison?
        for example totalShares == 3, liquidity amount is 100 mutez, two
        claims for 1 share (each for 33 mutez), total 66... looks OK, but need
        to make sure
    *)

    (* Part of activeLiquidity was already excluded if there was some claims *)
    const claimedLiquidity = event.provided * event.lockedShares / event.totalShares;
    const remainedLiquidity = event.provided - claimedLiquidity;

    (* remainedLiquidity should always be less than store.activeLiquidity but
        it is better to cap it on zero if it somehow goes negative: *)
    store.activeLiquidity := absPositive(store.activeLiquidity - remainedLiquidity);
    const profitLossPerEvent = (reward - event.provided) / store.maxActiveEvents;

    (* TODO: is it possible to make newNextEventLiquidity < 0? when liquidity withdrawn
        for example and then failed event? Its good to be sure that it is impossible *)
    (* TODO: need to find this test cases if it is possible or find some proof that it is not *)
    store.nextEventLiquidity :=
        absPositive(store.nextEventLiquidity + profitLossPerEvent);
    (* TODO: consider failwith here instead of absPositive
        the same for store.activeLiquidity, but don't want to block this entrypoint *)

} with ((nil: list(operation)), store)


function createEvent(
    const lineId : nat;
    var store : storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);
    checkHaveFreeEventSlots(store);

    var line := getLine(lineId, store);
    checkLineIsNotPaused(line);

    (* checking how much events already runned in the line *)
    function countEvents (const count : nat; const ids : nat*nat) : nat is
        if ids.1 = lineId then count + 1n else count;
    const activeEventsInLine = Map.fold(countEvents, store.activeEvents, 0n);
    if activeEventsInLine > line.maxActiveEvents
        then failwith("Max active events limit reached")
        else skip;

    (* checking that event can be created *)
    (* only one event in line can be opened for bets *)
    (* TODO: consider having some 1-5 min advance for event creation? *)
    if Tezos.now < line.lastBetsCloseTime then
        failwith("Event cannot be created until previous event betsCloseTime")
    else skip;

    (* If there was some missed events, need to adjust nextBetsCloseTime *)
    const periods = (Tezos.now - line.lastBetsCloseTime) / line.betsPeriod + 1n;
    const nextBetsCloseTime = line.lastBetsCloseTime + line.betsPeriod*periods;

    (* TODO: it is good to move nextBetsCloseTime in time for one more period
        if time that left is less than 30 minutes (or some const provided in
        event line params) *)
    (* TODO {the same}: maybe this is good to have some logic that shifts nextBetsCloseTime
        for one more period if there are not enough time left for the bets
        (for example if this is less than a half of the betsPeriod) *)

    (* Updating line *)
    line.lastBetsCloseTime := nextBetsCloseTime;
    store.lines[lineId] := line;

    (* newEvent transaction *)
    (* TODO: store juster address in line instead of storage? *)
    const newEventEntrypoint =
        case (Tezos.get_entrypoint_opt("%newEvent", store.juster)
              : option(contract(newEventParams))) of
        | None -> (failwith("Juster.newEvent is not found") : contract(newEventParams))
        | Some(con) -> con
        end;

    const newEvent = record [
        currencyPair = line.currencyPair;
        targetDynamics = line.targetDynamics;
        betsCloseTime = nextBetsCloseTime;
        measurePeriod = line.measurePeriod;
        liquidityPercent = line.liquidityPercent;
    ];

    (* TODO: make call to juster.getConfig view instead of using store.newEventFee *)
    const newEventOperation = Tezos.transaction(
        newEvent, store.newEventFee, newEventEntrypoint);

    (* getting nextEventId from Juster *)
    const nextEventIdOption : option(nat) = Tezos.call_view
        ("getNextEventId", Unit, store.juster);
    const nextEventId = case nextEventIdOption of
    | Some(id) -> id
    | None -> (failwith("Juster.getNextEventId view is not found") : nat)
    end;

    (* provideLiquidity transaction *)
    const provideLiquidityEntrypoint =
        case (Tezos.get_entrypoint_opt("%provideLiquidity", store.juster)
              : option(contract(provideLiquidityParams))) of
        | None -> (failwith("Juster.provideLiquidity is not found") : contract(provideLiquidityParams))
        | Some(con) -> con
        end;

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
    const liquidityPayout = calcLiquidityPayout(store);
    const provideLiquidityOperation = Tezos.transaction(
        provideLiquidity, liquidityPayout, provideLiquidityEntrypoint);

    const operations = list[newEventOperation; provideLiquidityOperation];

    const eventCosts = (liquidityPayout + store.newEventFee)/1mutez;

    (* adding new activeEvent: *)
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
    store.counter := store.counter + 1n;

} with (operations, store)


(*
function createEvents(
    const lineIds : list(nat);
    var store : storage) : (list(operation) * storage) is
block {
    var operations := (nil : list(operation));
    for lineId in list lineIds block {
        const (newEventOperation, provideLiquidityOperation, updatedStore) = createEvent(lineId, store);
        operations := newEventOperation # provideLiquidityOperation # operations;
        store := updatedStore
    }
} with (operations, store)
*)


function triggerPauseLine(const lineId : nat; var store : storage) is
block {
    checkNoAmountIncluded(unit);
    onlyManager(store.manager);

    const line = getLine(lineId, store);

    store := if line.isPaused
        then increaseMaxActiveEvents(line.maxActiveEvents, store);
        else decreaseMaxActiveEvents(line.maxActiveEvents, store);

    store.lines[lineId] := line with record [isPaused = not line.isPaused];

} with ((nil: list(operation)), store)


function triggerPauseDeposit(var store : storage) is
block {
    checkNoAmountIncluded(unit);
    onlyManager(store.manager);
    store.isDepositPaused := not store.isDepositPaused;
} with ((nil: list(operation)), store)


function main (const params : action; var s : storage) : (list(operation) * storage) is
case params of
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
end

[@view] function getBalance (const _ : unit ; const _s: storage) : tez is Tezos.balance

