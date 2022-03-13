#include "../partials/errors.ligo"
#include "../partials/helpers.ligo"


(* TODO: move all aggegator types to separate interface .ligo *)
type lineType is record [
    currencyPair : string;
    targetDynamics : nat;
    liquidityPercent : nat;
    rateAboveEq : nat;
    rateBelow : nat;

    measurePeriod : nat;
    betsPeriod : nat;

    (* parameters used to control events flow *)
    lastBetsCloseTime : timestamp;

    (* maxEvents is amount of events that can be runned in parallel for the line? *)
    maxActiveEvents : nat;
    (* TODO: consider having advanceTime that allows to create new event before
        lastBetsCloseTime
        {2022-03-11: but this is not very effective liquidity use} *)
    (* TODO: consider having min time delta before next betsCloseTime to prevent
        possibility of event creation with very small period until betsClose *)

    (* TODO: consider having isPaused field *)
    (* TODO: consider having Juster address in line instead of storage
        (easier to update and possibility to have multiple juster contracts) *)
]

type positionType is record [
    (* TODO: replace provider with NFT token_id that represents this position? *)
    provider : address;
    shares : nat;
    addedCounter : nat;
]

type eventType is record [
    createdCounter : nat;
    totalShares : nat;
    lockedShares : nat;
    result : option(nat);
    (* TODO: consider having isFinished : bool field? Or result as an option
        is enough? *)
    provided : nat;
]

type claimKey is record [
    eventId : nat;
    positionId : nat;
]

type claimParams is record [
    shares : nat;
    (* TODO: is it required to record this totalShares here, they already
        recorded in event ledger *)
    totalShares : nat;
    provider : address;
]

(*  entryPosition is not accepted yet position including provider address,
    timestamp when liquidity can be accepted and amount of this liquidity *)
type entryPositionType is record [
    provider : address;
    acceptAfter : timestamp;
    amount : nat;
]

type storage is record [
    nextLineId: nat;

    (* lines is ledger with all possible event lines that can be created *)
    lines : map(nat, lineType);

    (* active lines is mapping between eventId and lineId *)
    activeEvents : map(nat, nat);
    events : big_map(nat, eventType);

    positions : big_map(nat, positionType);
    nextPositionId : nat;
    totalShares : nat;

    (* activeLiquidity aggregates all liquidity that are in activeEvents,
        it is needed to calculate new share amount for new positions *)
    activeLiquidity : nat;

    withdrawableLiquidity : nat;

    (* added liquidity that not recognized yet *)
    entryLiquidity : nat;

    (* amount of time before liquidity can be recognized *)
    entryLockPeriod : nat;
    (* TODO: ^^ consider moving this to `configs` and having configs ledger *)

    entryPositions : big_map(nat, entryPositionType);
    nextEntryPositionId : nat;

    claims : big_map(claimKey, claimParams);

    manager : address;

    juster : address;

    (* TODO: remove newEventFee and use config view instead
            (require Juster redeploying in hangzhounet) *)
    newEventFee : tez;

    (* aggregated max active events required to calculate liquidity amount *)
    maxActiveEvents : nat;

    (* As far as liquidity can be added in the same block as a new event created
        it is required to understand if this liquidity was added before or
        after event creation. There is why special counter used instead of
        using time/level *)
    counter : nat;

    nextEventLiquidity : nat;

    (* TODO: condider having withdrawStats ledger with some data that can be
        used in reward programs *)
    (* TODO: to calculate withdrawalStats it might be good to have
        - createdEventsCount
        - providedPerShare
        - maybe something else
        - it might be in some kind of stats record
    *)
]


type claimLiquidityParams is record [
    positionId : nat;
    shares : nat;
]

type withdrawLiquidityParams is list(claimKey)

(* entrypoints:
    - addLine: adding new line of typical events, only manager can add new lines
    - depositLiquidity: creating request for adding new liquidity
    - approveLiquidity: adds requested liquidity to the aggregator
    - cancelLiquidity: cancels request for adding new liquidity
    - claimLiquidity: creates request for withdraw liquidity from all current events
    - withdrawLiquidity: withdraws claimed events
    - payReward: callback that receives withdraws from Juster
    - createEvent: creates new event in line, anyone can call this
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
(* TODO: consider having CreateEvents of list(nat) *)
(* TODO: removeLine?
        1) consider to have at least one line to support nextEventLiquidity
        2) it is better to stopLine / pauseLine / triggerPauseLine instead so the info can be used in views later
*)
(* TODO: updateLine? to change ratios for example, only manager can call
        2022-03-11: it is better to have just stopLine/pauseLine + addLine so any updates would
            require both removing and adding line (this will allow use this data in the
            reward programs in the future, updating lines will remove info about this lines
*)
(* TODO: updateNewEventFee if it changed in Juster, only manager can call
    - it is better read config from Juster views
    - maybe it would be good to have here some kind of config too (with juster address etc)
    - and lines can be binded to different configs
*)
(* TODO: updateEntryLockPeriod {or move this to updateConfig} *)
(* TODO: pauseEvents *)
(* TODO: pauseDepositLiquidity *)
(* TODO: views: getLineOfEvent, getNextEventLiquidity, getWithdrawableLiquidity,
    getNextPositionId, getNextEntryPositionId, getNextClaimId,
    getConfig, getWithdrawalStat ... etc *)
(* TODO: views: getPosition(id), getClaim(id), getEvent? *)
(* TODO: default entrypoint for baking rewards *)
(* TODO: entrypoint to change delegator
        - reuse Juster code
*)
(* TODO: change manager entrypoints handshake
        - reuse Juster code
*)


(* Some helpers, TODO: move to some separate .ligo *)
function getEntry(const entryId : nat; const store : storage) : entryPositionType is
    getOrFail(entryId, store.entryPositions, Errors.entryNotFound)

function getPosition(const positionId : nat; const store : storage) : positionType is
    getOrFail(positionId, store.positions, Errors.positionNotFound)

function getEvent(const eventId : nat; const store : storage) : eventType is
    getOrFail(eventId, store.events, Errors.eventNotFound)

function checkHasActiveEvents(const store : storage) : unit is
    if store.maxActiveEvents = 0n
    then failwith(Errors.noActiveEvents)
    else unit;


function addLine(
    const line : lineType;
    var store : storage) : (list(operation) * storage) is
block {
    checkNoAmountIncluded(unit);
    onlyManager(store.manager);

    (* TODO: consider lines to be list {but then it will be harder to stop them?} *)

    store.lines[store.nextLineId] := line;
    store.nextLineId := store.nextLineId + 1n;
    const newMaxActiveEvents = store.maxActiveEvents + line.maxActiveEvents;
    store.nextEventLiquidity :=
        store.nextEventLiquidity * store.maxActiveEvents / newMaxActiveEvents;
    store.maxActiveEvents := newMaxActiveEvents;

} with ((nil: list(operation)), store)


function depositLiquidity(
    var store : storage) : (list(operation) * storage) is
block {

    const providedAmount = Tezos.amount / 1mutez;
    if providedAmount = 0n then failwith("Should provide tez") else skip;

    const newEntryPosition = record[
        provider = Tezos.sender;
        acceptAfter = Tezos.now + int(store.entryLockPeriod);
        amount = providedAmount;
    ];
    store.entryPositions[store.nextEntryPositionId] := newEntryPosition;
    store.nextEntryPositionId := store.nextEntryPositionId + 1n;
    store.entryLiquidity := store.entryLiquidity + providedAmount;

} with ((nil: list(operation)), store)


function approveLiquidity(
    const entryId : nat; var store : storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    const entryPosition = getEntry(entryId, store);
    store.entryPositions := Big_map.remove(entryId, store.entryPositions);

    if Tezos.now < entryPosition.acceptAfter
    then failwith(Errors.earlyApprove)
    else skip;

    (* store.entryLiquidity is the sum of all entryPositions, so the following
        condition should not be true but it is better to check *)
    if store.entryLiquidity < entryPosition.amount
    then failwith(Errors.wrongState)
    else skip;

    store.entryLiquidity := abs(store.entryLiquidity - entryPosition.amount);

    (* if there are no lines, then it is impossible to calculate providedPerEvent
        and there would be DIV/0 error *)
    checkHasActiveEvents(store);

    (* calculating shares *)
    const provided = entryPosition.amount;
    const totalLiquidity =
        store.activeLiquidity + Tezos.balance/1mutez - store.entryLiquidity;

    (* totalLiquidity includes provided liquidity so the following condition
        should not be true but it is better to check *)
    if totalLiquidity < int(provided)
    then failwith(Errors.wrongState)
    else skip;

    const liquidityBeforeDeposit = abs(totalLiquidity - provided);

    const shares = if store.totalShares = 0n
        then provided
        else provided * store.totalShares / liquidityBeforeDeposit;

    const newPosition = record [
        provider = entryPosition.provider;
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


(* TODO: use tools that created for Juster? *)
function getReceiver(const a : address) : contract(unit) is
    case (Tezos.get_contract_opt(a): option(contract(unit))) of
    | Some (con) -> con
    | None -> (failwith ("Not a contract") : (contract(unit)))
    end;

function prepareOperation(
    const addressTo : address;
    const payout : tez
) : operation is Tezos.transaction(unit, payout, getReceiver(addressTo));


function cancelLiquidity(
    const entryId : nat; var store : storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    const entryPosition = getEntry(entryId, store);
    store.entryPositions := Big_map.remove(entryId, store.entryPositions);

    checkSenderIs(entryPosition.provider, Errors.notEntryOwner);

    store.entryLiquidity := abs(store.entryLiquidity - entryPosition.amount);

    const operations = if entryPosition.amount > 0n then
        list[prepareOperation(Tezos.sender, entryPosition.amount * 1mutez)]
    else (nil: list(operation));

} with (operations, store)


function absPositive(const value : int) is if value >= 0 then abs(value) else 0n


function claimLiquidity(
    const params : claimLiquidityParams;
    var store : storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    const position = getPosition(params.positionId, store);
    checkSenderIs(position.provider, Errors.notPositionOwner);

    if params.shares > position.shares then
        failwith("Claim shares is exceed position shares")
    else skip;
    const leftShares = abs(position.shares - params.shares);
    var providedLiquiditySum := 0n;

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
            totalShares = event.totalShares;
            provider = position.provider;
        ];

        if position.addedCounter < event.createdCounter then block {
            if params.shares > 0n
            then store.claims := Big_map.update(key, Some(updatedClaim), store.claims)
            else skip;

            const providedLiquidity = params.shares * event.provided / event.totalShares;
            providedLiquiditySum := providedLiquiditySum + providedLiquidity;
        }
        else skip;

        event.lockedShares := event.lockedShares + params.shares;
        (* TODO: assert that event.lockedShares < event.totalShares ?
            this is wrongState but feels that it is better to assert it *)
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

    (* TODO: assert that store.withdrawableLiquidity < Tezos.balance/1mutez?
        but if this happens: it would mean that things went very wrong
        somewhere else (Errors.wrongState) *)
    const totalLiquidity = abs(
        Tezos.balance/1mutez
        - store.withdrawableLiquidity
        - store.entryLiquidity
        + store.activeLiquidity);

    const participantLiquidity = params.shares * totalLiquidity / store.totalShares;
    const payoutValue = participantLiquidity - providedLiquiditySum;
    (* TODO: check that payoutValue > 0 (is it possible to have it < 0?) *)

    (* TODO: make you sure that it is required to distribute
        participantLiquidity and not payoutValue instead {is there any tests for this difference?} *)
    const liquidityPerEvent = participantLiquidity / store.maxActiveEvents;

    (* TODO: is it possible to have liquidityPerEvent > store.nextEventLiquidity ? *)
    store.nextEventLiquidity :=
        absPositive(store.nextEventLiquidity - liquidityPerEvent);

    (* TODO: assert that store.totalShares > shares? this case should be
        impossible, but feels like this is good to have this check? *)
    store.totalShares := abs(store.totalShares - params.shares);

    (* TODO: is it possible to have store.activeLiquidity < providedLiquiditySum? *)
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

        (* TODO: is it required to record totalShares in claim or it is enough
            to have this totalShares in the event ledger? *)
        const eventReward = eventResult * claim.shares / claim.totalShares;

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

        (* TODO: assert that store.withdrawableLiquidity <= payout ? *)
        (* TODO: need to find this test cases if it is possible or find some proof that it is not *)
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

    const claimedLiquidity = event.provided * event.lockedShares / event.totalShares;
    const remainedLiquidity = event.provided - claimedLiquidity;
    (* TODO: assert that remainedLiquidity >= store.activeLiquidity *)
    (* TODO: why does only remainedLiquidity excluded from activeLiquidity and
        not all event.provided? was claimedLiquidity already excluded during claim?
        looks like it is. Would it better to exclude all event.provided here and
        not split it in two parts? Need to understand make this logic more clear *)
    store.activeLiquidity := abs(store.activeLiquidity - remainedLiquidity);
    const profitLossPerEvent = (reward - event.provided) / store.maxActiveEvents;

    (* TODO: is it possible to make newNextEventLiquidity < 0? when liquidity withdrawn
        for example and then failed event? Its good to be sure that it is impossible *)
    (* TODO: need to find this test cases if it is possible or find some proof that it is not *)
    store.nextEventLiquidity :=
        absPositive(store.nextEventLiquidity + profitLossPerEvent);
    (* TODO: is it better to have failwith here? don't want to have possibility
        to block contract communications *)

} with ((nil: list(operation)), store)


(* TODO: need to use Juster newEventParams and provideLiquidityParams instead
    having this copies here *)
type newEventParams is record [
    currencyPair : string;
    targetDynamics : nat;
    betsCloseTime : timestamp;
    measurePeriod : nat;
    liquidityPercent : nat;
]

type provideLiquidityParams is record [
    eventId : nat;
    expectedRatioAboveEq : nat;
    expectedRatioBelow : nat;
    maxSlippage : nat;
]


function createEvent(
    const lineId : nat;
    var store : storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    const freeEventSlots = store.maxActiveEvents - Map.size(store.activeEvents);
    if freeEventSlots <= 0 then failwith("Max active events limit reached")
    else skip;

    var line := case Map.find_opt(lineId, store.lines) of
    | Some(line) -> line
    | None -> (failwith("Line is not found") : lineType)
    end;

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

    var liquidityAmount := store.nextEventLiquidity - store.newEventFee/1mutez;

    const freeLiquidity = (
        Tezos.balance/1mutez
        - store.withdrawableLiquidity
        - store.entryLiquidity
        - abs(freeEventSlots)*store.newEventFee/1mutez);

    (* TODO: is it really required to remove all freeEventSlots newEventFees or it
        will be enough to just remove it once? *)

    if freeLiquidity < liquidityAmount then liquidityAmount := freeLiquidity
    else skip;

    (* TODO: is this case with 0 liquidity presented in tests? *)
    if liquidityAmount <= 0 then failwith("Not enough liquidity to run event")
    else skip;

    const liquidityPayout = abs(liquidityAmount) * 1mutez;
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
end

[@view] function getBalance (const _ : unit ; const _s: storage) : tez is Tezos.balance

