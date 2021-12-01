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
]

type positionType is record [
    provider : address;
    shares : nat;

    (* TODO: consider addedCounter & eventLine.lastEventCreatedTimeCounter
        instead of time? This can resolve problems when liquidity added in the
        same block when event is created *)
    addedTime : timestamp;
]

type eventType is record [
    createdTime : timestamp;
    totalShares : nat;

    (* TODO: do I need to have this isFinished status? *)
    isFinished : bool;
    lockedShares : nat;
    result : option(nat);
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

type storage is record [
    nextLineId: nat;

    (* lines is ledger with all possible event lines that can be created *)
    (* TODO: consider type big_map, but then it would not be possible to
        all lines in the cycle *)
    (* TODO: consider type list(lineType): then this would not required to have nextLineId *)
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

    (* claims is liquidity, that can be withdrawn by providers,
        key: eventId*positionId
        value: shares
    *)

    claims : big_map(claimKey, claimParams);

    manager : address;
    (* TODO: lockedShares: nat; ?*)

    juster : address;
    newEventFee : tez;
    maxActiveEvents : nat;
]


type claimLiquidityParams is record [
    positionId : nat;
    shares : nat;
]

type withdrawLiquidityParams is list(claimKey)

type action is
| AddLine of lineType
| DepositLiquidity of unit

(* claiming liquidity with value of shares count allows to withdraw this shares
    from all current events *)
| ClaimLiquidity of claimLiquidityParams

(* withdrawing claimed events, parameter is list of event ids with position ids *)
| WithdrawLiquidity of withdrawLiquidityParams

(* receiving reward from Juster, nat is eventId *)
| PayReward of nat
(* TODO: removeLine? *)
(* TODO: updateLine? to change ratios for example, only manager can call *)
(* TODO: updateNewEventFee if it changed in Juster, only manager can call *)
// | CreateEvents of list(nat)
| CreateEvent of nat


function addLine(
    const line : lineType;
    var store : storage) : (list(operation) * storage) is
block {
    (* TODO: assert no tez provided *)
    (* TODO: assert that Tezos.sender is manager *)

    (* TODO: consider lines to be list *)
    store.lines[store.nextLineId] := line;
    store.nextLineId := store.nextLineId + 1n;
    store.maxActiveEvents := store.maxActiveEvents + line.maxActiveEvents;

} with ((nil: list(operation)), store)


function depositLiquidity(
    var store : storage) : (list(operation) * storage) is
block {

    (* calculating shares *)
    const provided = Tezos.amount/1mutez;
    const totalLiquidity = store.activeLiquidity + Tezos.balance/1mutez;
    const shares = if store.totalShares = 0n
        then provided
        else provided * store.totalShares / totalLiquidity;

    const newPosition = record [
        provider = Tezos.sender;
        shares = shares;
        addedTime = Tezos.now;
    ];

    store.positions[store.nextPositionId] := newPosition;
    store.nextPositionId := store.nextPositionId + 1n;
    store.totalShares := store.totalShares + shares;

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

    (* TODO: maybe this is enough to have set of eventIds instead of mapping *)
    for eventId -> lineId in map store.activeEvents block {
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

        (* TODO: what happens if positon added in the same block when event was
            created? Is it possible to check what was before and what was after?
            MAYBE: maybe it is better to have some kind of internal counter instead
            of time?
        *)

        if position.addedTime < event.createdTime then
            store.claims := Big_map.update(key, Some(updatedClaim), store.claims)
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
        addedTime = position.addedTime;
    ];
    store.positions := Big_map.update(
        params.positionId, Some(updatedPosition), store.positions);
    (* TODO: consider Big_map.remove if leftShares == 0n? *)

    (* calculating free liquidity that can be withdrawn. This calculation
        differs from freeLiquidity that calculated when new event created, this
        is because newEventFee amount can be removed here
        TODO: consider making this calculation the same in both places?
    *)

    (* TODO: assert that store.withdrawableLiquidity < Tezos.balance/1mutez?
        but if this happens: it would mean that things went very wrong
        somewhere else *)
    const freeLiquidity = abs(
        Tezos.balance/1mutez
        - store.withdrawableLiquidity);

    const payout = params.shares * freeLiquidity / store.totalShares * 1mutez;

    (* TODO: assert that store.totalShares > shares? this case should be
        impossible, but feels like this is good to have this check? *)
    store.totalShares := abs(store.totalShares - params.shares);

    const operations = if payout > 0tez then
        list[prepareOperation(Tezos.sender, payout)]
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
    store.withdrawableLiquidity := abs(store.withdrawableLiquidity - withdrawSum);
} with (operations, store)


function payReward(
    const eventId : nat;
    var store : storage) : (list(operation) * storage) is
block {
    (* TODO: assert that Tezos.sender is store.juster *)
    (* NOTE: this method based on assumption that getReward only called by
        Juster when event is finished / canceled *)

    (* adding event result *)
    const reward = Tezos.amount / 1mutez;
    var event := getEvent(store, eventId);
    event.result := Some(reward);

    (* TODO: is this field isFinished required anywhere? *)
    event.isFinished := True;
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

    (* TODO: assert that event.provided >= store.activeLiquidity *)
    store.activeLiquidity := abs(store.activeLiquidity - event.provided);

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

    (* TODO: is it possible to calculate how much events runned in each line
        and failwith if there are already too many events in the line? *)

    const freeEventSlots = store.maxActiveEvents - Map.size(store.activeEvents);
    if freeEventSlots <= 0 then failwith("Max active events limit reached")
    else skip;

    var line := case Map.find_opt(lineId, store.lines) of
    | Some(line) -> line
    | None -> (failwith("Line is not found") : lineType)
    end;

    (* checking that event can be created *)
    (* only one event in line can be opened for bets *)
    (* TODO: consider having some 1-5 min advance for event creation? *)
    if Tezos.now < line.lastBetsCloseTime then
        failwith("Event cannot be created until previous event betsCloseTime")
    else skip;

    (* If there was some missed events, need to adjust nextBetsCloseTime *)
    const periods = (Tezos.now - line.lastBetsCloseTime) / line.betsPeriod + 1n;
    const nextBetsCloseTime = line.lastBetsCloseTime + line.betsPeriod*periods;

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

    const freeLiquidity = (
        Tezos.balance/1mutez
        - store.withdrawableLiquidity
        - abs(freeEventSlots)*store.newEventFee/1mutez);

    if freeLiquidity <= 0 then failwith("Not enough liquidity to run event")
    else skip;

    const expectedEvents = store.maxActiveEvents - Map.size(store.activeEvents);
    const liquidityAmount = abs(freeLiquidity / expectedEvents) * 1mutez;

    const provideLiquidityOperation = Tezos.transaction(
        provideLiquidity, liquidityAmount, provideLiquidityEntrypoint);

    const operations = list[newEventOperation; provideLiquidityOperation];

    (* adding new activeEvent: *)
    const event = record [
        createdTime = Tezos.now;
        totalShares = store.totalShares;
        isFinished = False;
        lockedShares = 0n;
        result = (None : option(nat));
        provided = liquidityAmount/1mutez;
    ];
    store.events[nextEventId] := event;
    store.activeEvents := Big_map.add(nextEventId, lineId, store.activeEvents);
    store.activeLiquidity := store.activeLiquidity + liquidityAmount/1mutez;

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
| ClaimLiquidity(p) -> claimLiquidity(p, s)
| WithdrawLiquidity(p) -> withdrawLiquidity(p, s)
| PayReward(p) -> payReward(p, s)
| CreateEvent(p) -> createEvent(p, s)
end

[@view] function getBalance (const _ : unit ; const _s: storage) : tez is Tezos.balance

