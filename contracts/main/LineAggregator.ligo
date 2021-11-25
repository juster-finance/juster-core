type lineType is record [
    currencyPair : string;
    targetDynamics : nat;
    liquidityPercent : nat;
    rateAboveEq : nat;
    rateBelow : nat;
    (* TODO: maybe this is good to have both betsPeriod and measurePeriod *)
    period : nat;

    (* parameters used to control events flow *)
    lastBetsCloseTime : timestamp;

    (* TODO: consider having maxEvents amount that run in parallel for the line? *)
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
]

type claimKey is record [
    eventId : nat;
    positionId : nat;
]

type claimParams is record [
    shares : nat;
    totalShares : nat;
]

type storage is record [
    nextLineId: nat;

    (* lines is ledger with all possible event lines that can be created *)
    (* TODO: consider type big_map, but then it would not be possible to
        all lines in the cycle *)
    (* TODO: consider type list(lineType) *)
    lines : map(nat, lineType);

    (* active lines is mapping between eventId and lineId *)
    activeLines : map(nat, nat);
    events : big_map(nat, eventType);

    // events : big_map(nat, eventType);
    positions : big_map(nat, positionType);
    nextPositionId : nat;
    totalShares : nat;

    withdrawableLiquidity : nat;

    (* claims is liquidity, that can be withdrawn by providers,
        key: eventId*positionId
        value: shares
    *)

    claims : big_map(claimKey, claimParams);

    manager : address;
    (* TODO: lockedShares: nat; ?*)

    juster : address;
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
| CreateEvents of list(nat)


function addLine(
    const lineParams : lineType;
    var store : storage) : (list(operation) * storage) is
block {
    skip;
} with ((nil: list(operation)), store)


function depositLiquidity(
    var store : storage) : (list(operation) * storage) is
block {
    skip;
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


function claimLiquidity(
    const params : claimLiquidityParams;
    var store : storage) : (list(operation) * storage) is
block {

    const position = getPosition(store, params.positionId);
    checkPositionProviderIsSender(position);

    if params.shares > position.shares then
        failwith("Claim shares is exceed position shares")
    else skip;
    const leftShares = abs(position.shares - params.shares);

    (* TODO: maybe this is enough to have set of eventIds instead of mapping *)
    for eventId -> lineId in map store.activeLines block {
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

        if position.addedTime > event.createdTime then
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

    (* TODO: assert that store.totalShares > shares? this case should be
        impossible, but feels like this is good to have this check? *)
    store.totalShares := abs(store.totalShares - params.shares);

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


function withdrawLiquidity(
    const withdrawRequests : withdrawLiquidityParams;
    var store : storage) : (list(operation) * storage) is
block {

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
    store.activeLines := Map.remove(eventId, store.activeLines);

    (* adding withdrawable liquidity to the pool: *)
    const newWithdrawable = reward * event.lockedShares / event.totalShares;

    store.withdrawableLiquidity := store.withdrawableLiquidity + newWithdrawable;

    (* TODO: is it possible that this withdrawableLiquidity would be less than
        the sum of the claims because of the nat divison?
        for example totalShares == 3, liquidity amount is 100 mutez, two
        claims for 1 share (each for 33 mutez), total 66... looks OK, but need
        to make sure
    *)

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
    var store : storage) : (operation * operation * storage) is
block {
    (* checking that event can be created *)

    (*
    (* newEvent transaction *)
    const newEventEntrypoint =
        case (Tezos.get_entrypoint_opt("%newEvent", store.juster) : option(contract(newEventParams))) of
        | None -> (failwith("Juster is not found") : contract(newEventParams))
        | Some(con) -> con
        end;

    const newEvent = record [
        currencyPair : string;
        targetDynamics : nat;
        betsCloseTime : timestamp;
        measurePeriod : nat;
        liquidityPercent : nat;
    ]

    (* TODO: need to transfer some xtz to create new events! *)
    const callback : operation = Tezos.transaction(
        (event.currencyPair, entrypoint),
        0tez,
        newEventEntrypoint);
    const operations = makeCallToOracle(
        eventId, store, (Tezos.self("%closeCallback") : callbackEntrypoint));
    store.closeCallId := Some(eventId);

    *)

    const newEventOperation = Tezos.transaction(unit, 0tez, getReceiver(store.juster));
    const provideLiquidityOperation = Tezos.transaction(unit, 0tez, getReceiver(store.juster));

    (* provideLiquidity transaction *)
} with (newEventOperation, provideLiquidityOperation, store)


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


function main (const params : action; var s : storage) : (list(operation) * storage) is
case params of
| AddLine(p) -> addLine(p, s)
| DepositLiquidity(p) -> depositLiquidity(s)
| ClaimLiquidity(p) -> claimLiquidity(p, s)
| WithdrawLiquidity(p) -> withdrawLiquidity(p, s)
| PayReward(p) -> payReward(p, s)
| CreateEvents(p) -> createEvents(p, s)
end

