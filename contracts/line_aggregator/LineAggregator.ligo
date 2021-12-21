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
        lastBetsCloseTime *)
    (* TODO: consider having min time delta before next betsCloseTime to prevent
        possibility of event creation with very small period until betsClose *)
]

type positionType is record [
    provider : address;
    shares : nat;

    (* TODO: consider addedCounter & eventLine.lastEventCreatedTimeCounter
        instead of time? This can resolve problems when liquidity added in the
        same block when event is created *)
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
    (* TODO: do I need to have this totalShares in claim params? need to figure out *)
    totalShares : nat;
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
    (* TODO: consider type big_map, but then it would not be possible to
        all lines in the cycle *)
    (* TODO: consider type list(lineType): then this would not required to have nextLineId *)
    lines : map(nat, lineType);

    (* active lines is mapping between eventId and lineId *)
    (* TODO: make this set(nat) ? *)
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

    entryPositions : big_map(nat, entryPositionType);
    nextEntryPositionId : nat;

    claims : big_map(claimKey, claimParams);
    // shareClaims : big_map(claimKey, claimParams);

    manager : address;
    (* TODO: lockedShares: nat; ?*)

    juster : address;
    newEventFee : tez;

    (* aggregated max active events required to calculate liquidity amount *)
    maxActiveEvents : nat;

    (* As far as liquidity can be added in the same block as a new event created
        it is required to understand if this liquidity was added before or
        after event creation. There is why special counter used instead of
        using time/level *)
    counter : nat;

    nextEventLiquidity : nat;
]


type claimLiquidityParams is record [
    positionId : nat;
    shares : nat;
]

type withdrawLiquidityParams is list(claimKey)

type action is
| AddLine of lineType
| DepositLiquidity of unit
(* TODO: how to cancel deposited but not approved liquidity?
    only thorough approve process? Or there should be special entrypoint to do this?
    Is it possible that approveLiquidity will be blocked and liquidity will be locked? *)
| ApproveLiquidity of nat

(* claiming liquidity with value of shares count allows to withdraw this shares
    from all current events *)
| ClaimLiquidity of claimLiquidityParams

(* withdrawing claimed events, parameter is list of event ids with position ids *)
| WithdrawLiquidity of withdrawLiquidityParams

(* receiving reward from Juster, nat is eventId *)
| PayReward of nat
(* TODO: removeLine? [consider to have at least one line to support nextEventLiquidity] *)
(* TODO: updateLine? to change ratios for example, only manager can call *)
(* TODO: updateNewEventFee if it changed in Juster, only manager can call *)
// | CreateEvents of list(nat)
| CreateEvent of nat
(* TODO: updateEntryLockPeriod *)
(* TODO: pauseEvents *)
(* TODO: pauseDepositLiquidity *)
(* TODO: views: getLineOfEvent, getNextEventLiquidity, getWithdrawableLiquidity,
    getNextPositionId, getNextEntryPositionId, getNextClaimId ... etc *)


function addLine(
    const line : lineType;
    var store : storage) : (list(operation) * storage) is
block {
    (* TODO: assert no tez provided *)
    (* TODO: assert that Tezos.sender is manager *)

    (* TODO: consider lines to be list *)
    (* TODO: assert that this line is not repeating another one? *)

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
    const newEntryPosition = record[
        provider = Tezos.sender;
        acceptAfter = Tezos.now + int(store.entryLockPeriod);
        amount = providedAmount;
    ];
    store.entryPositions[store.nextEntryPositionId] := newEntryPosition;
    store.nextEntryPositionId := store.nextEntryPositionId + 1n;
    store.entryLiquidity := store.entryLiquidity + providedAmount;

} with ((nil: list(operation)), store)


function getOrFail(
    const key : _key;
    const ledger : big_map(_key, _value);
    const failwithMsg : string) : _value is
case Big_map.find_opt(key, ledger) of
| Some(value) -> value
| None -> (failwith(failwithMsg) : _value)
end;


function approveLiquidity(
    const entryPositionId : nat; var store : storage) : (list(operation) * storage) is
block {

    const entryPosition = getOrFail(
        entryPositionId, store.entryPositions, "Entry position is not found");

    if Tezos.now < entryPosition.acceptAfter
        then failwith("Cannot approve liquidity before acceptAfter") else skip;

    (* TODO: is it possible to have store.entryLiquidity < entryPosition.amount?
        maybe need to check & failwith then? *)
    store.entryLiquidity := abs(store.entryLiquidity - entryPosition.amount);

    (* if there are no lines, then it is impossible to calculate providedPerEvent
        and there would be DIV/0 error *)
    if store.maxActiveEvents = 0n
        then failwith("Need to have at least one line") else skip;

    (* calculating shares *)
    const provided = entryPosition.amount;
    const totalLiquidity =
        store.activeLiquidity + Tezos.balance/1mutez - store.entryLiquidity;
    (* TODO: is it possible to have totalLiquidity < 0? *)

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


function getPosition(const store : storage; const positionId : nat) : positionType is
case Big_map.find_opt(positionId, store.positions) of
| Some(pos) -> pos
| None -> (failwith("Position is not found") : positionType)
end;


function checkPositionProviderIsSender(const position : positionType) : unit is
if (position.provider =/= Tezos.sender) then failwith("Not position owner")
else Unit;


function getEvent(const store : storage; const eventId : nat) : eventType is
case Big_map.find_opt(eventId, store.events) of
| Some(event) -> event
| None -> (failwith("Event is not found") : eventType)
end;


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


function absPositive(const value : int) is if value >= 0 then abs(value) else 0n


function claimLiquidity(
    const params : claimLiquidityParams;
    var store : storage) : (list(operation) * storage) is
block {
    (* TODO: assert no tez provided *)

    const position = getPosition(store, params.positionId);
    checkPositionProviderIsSender(position);

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

        var event := getEvent(store, eventId);

        (* checking if this claim already have some shares: *)
        const alreadyClaimedShares = case Big_map.find_opt(key, store.claims) of
        | Some(claim) -> claim.shares
        | None -> 0n
        end;

        const updatedClaim = record [
            shares = alreadyClaimedShares + params.shares;
            totalShares = event.totalShares;
        ];

        if position.addedCounter < event.createdCounter then block {
            store.claims := Big_map.update(key, Some(updatedClaim), store.claims);
            const providedLiquidity = params.shares * event.provided / event.totalShares;
            providedLiquiditySum := providedLiquiditySum + providedLiquidity;
        }
        else skip;

        (* TODO: what happen if user claimed 50% of his position during line
            was runned and then line was finished? He should be able to receive
            his remaining 50% from current liquidity pool *)

        event.lockedShares := event.lockedShares + params.shares;
        store.events := Big_map.update(eventId, Some(event), store.events);
    };

    const updatedPosition = record [
        provider = position.provider;
        shares = leftShares;
        addedCounter = position.addedCounter;
    ];
    store.positions := Big_map.update(
        params.positionId, Some(updatedPosition), store.positions);
    (* TODO: consider Big_map.remove if leftShares == 0n? *)

    (* TODO: assert that store.withdrawableLiquidity < Tezos.balance/1mutez?
        but if this happens: it would mean that things went very wrong
        somewhere else *)
    const totalLiquidity = abs(
        Tezos.balance/1mutez
        - store.withdrawableLiquidity
        - store.entryLiquidity
        + store.activeLiquidity);

    const participantLiquidity = params.shares * totalLiquidity / store.totalShares;
    const payoutValue = participantLiquidity - providedLiquiditySum;
    (* TODO: check that payoutValue > 0 (is it possible to have it < 0?) *)

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

} with (operations, store)


function withdrawLiquidity(
    const withdrawRequests : withdrawLiquidityParams;
    var store : storage) : (list(operation) * storage) is
block {
    (* TODO: assert no tez provided *)

    var withdrawSum := 0n;
    for key in list withdrawRequests block {
        const position = getPosition(store, key.positionId);
        checkPositionProviderIsSender(position);

        const event = getEvent(store, key.eventId);
        const eventResult = case event.result of
        | Some(result) -> result
        | None -> (failwith("Event result is not received yet") : nat)
        end;

        (* TODO: consider failwith if claim is not found? *)
        const eventReward = case Big_map.find_opt(key, store.claims) of
        | Some(claim) -> eventResult * claim.shares / claim.totalShares
        | None -> 0n
        end;

        withdrawSum := withdrawSum + eventReward;
        store.claims := Big_map.remove(key, store.claims);
    };

    const payout = withdrawSum * 1mutez;
    const operations = if payout > 0tez then
        (* Tezos.sender was checked for each position already *)
        list[prepareOperation(Tezos.sender, payout)]
    else (nil: list(operation));

    (* TODO: assert that store.withdrawableLiquidity <= payout ? *)
    (* TODO: need to find this test cases if it is possible or find some proof that it is not *)
    store.withdrawableLiquidity := abs(store.withdrawableLiquidity - withdrawSum);
    (* TODO: consider removing events when they are fully withdrawn?
        Alternative: moving event result to separate ledger and remove event
        when payReward received *)

} with (operations, store)


function payReward(
    const eventId : nat;
    var store : storage) : (list(operation) * storage) is
block {
    (* TODO: assert that Tezos.sender is store.juster *)
    (* NOTE: this method based on assumption that payReward only called by
        Juster when event is finished / canceled *)

    (* adding event result *)
    const reward = Tezos.amount / 1mutez;
    var event := getEvent(store, eventId);
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
    (* TODO: assert that leftLiquidity >= store.activeLiquidity *)
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
    (* TODO: assert no tez provided *)

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

    (* Updating line *)
    line.lastBetsCloseTime := nextBetsCloseTime;
    store.lines[lineId] := line;

    (* newEvent transaction *)
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

    if freeLiquidity < liquidityAmount then liquidityAmount := freeLiquidity
    else skip;

    if liquidityAmount <= 0 then failwith("Not enough liquidity to run event")
    else skip;

    const liquidityPayout = abs(liquidityAmount) * 1mutez;
    const provideLiquidityOperation = Tezos.transaction(
        provideLiquidity, liquidityPayout, provideLiquidityEntrypoint);

    const operations = list[newEventOperation; provideLiquidityOperation];

    (* adding new activeEvent: *)
    const event = record [
        createdCounter = store.counter;
        totalShares = store.totalShares;
        lockedShares = 0n;
        result = (None : option(nat));
        provided = liquidityPayout/1mutez;
    ];
    store.events[nextEventId] := event;
    store.activeEvents := Map.add(nextEventId, lineId, store.activeEvents);
    store.activeLiquidity := store.activeLiquidity + liquidityPayout/1mutez;
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
| ClaimLiquidity(p) -> claimLiquidity(p, s)
| WithdrawLiquidity(p) -> withdrawLiquidity(p, s)
| PayReward(p) -> payReward(p, s)
| CreateEvent(p) -> createEvent(p, s)
end

[@view] function getBalance (const _ : unit ; const _s: storage) : tez is Tezos.balance

