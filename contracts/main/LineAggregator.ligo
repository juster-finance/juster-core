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

    (* parameters used in claims: *)
    isRunning : bool;
    (* TODO: as far as eventId == 0 is valid option, maybe this is better to have  option(nat) *)
    lastEventId : nat;
    lastEventCreatedTime : timestamp;
    lastTotalShares : nat;
    lockedShares : nat;
]

type positionType is record [
    provider : address;
    shares : nat;

    (* TODO: consider addedCounter & eventLine.lastEventCreatedTimeCounter
        instead of time? This can resolve problems when liquidity added in the
        same block when event is created *)
    addedTime : timestamp;
]

(*
type eventType is record [
    // createdTime : timestamp;
    // totalShares : nat;
    // isFinished : bool;
    (* TODO: why do I need this provided amount? is it some kind of totalShares? *)
    // provided : nat;

    (* TODO: maybe this would be enought to have only event results registry? *)
    result : option(nat);
]
*)

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

    (* received results of each events: *)
    eventResults : big_map(nat, nat);

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

    (* TODO: consider to iterate over activeLines instead: this is map(evendId, lineId); *)
    for lineId -> line in map store.lines block {
        (* TODO: consider possibility to have lastEventId None?
            or this will be always with isRunning == False so this is not important?
        *)
        const key = record [
            eventId = line.lastEventId;
            positionId = params.positionId;
        ];

        (* checking if this claim already have some shares: *)
        const alreadyClaimedShares = case Big_map.find_opt(key, store.claims) of
        | Some(claim) -> claim.shares
        | None -> 0n
        end;

        const updatedClaim = record [
            shares = alreadyClaimedShares + params.shares;
            totalShares = line.lastTotalShares;
        ];

        (* TODO: what happens if positon added in the same block when event was
            created? Is it possible to check what was before and what was after?
            MAYBE: maybe it is better to have some kind of internal counter instead
            of time?
        *)

        const isPositionActive = position.addedTime > line.lastEventCreatedTime;
        if line.isRunning and isPositionActive then
            store.claims := Big_map.update(key, Some(updatedClaim), store.claims)
        else skip;

        (* TODO: what happen if user claimed 50% of his position during line
            was runned and then line was finished? He should be able to receive
            his remaining 50% from current liquidity pool *)

        line.lockedShares := line.lockedShares + params.shares;
        store.lines := Map.update(lineId, Some(line), store.lines);
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

        const eventResult = case Big_map.find_opt(key.eventId, store.eventResults) of
        | Some(result) -> result
        | None -> (failwith("Event result is not found") : nat)
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
    store.eventResults := Big_map.add(eventId, reward, store.eventResults);

    (* updating lines *)
    const lineId = case Map.find_opt(eventId, store.activeLines) of
    | Some(id) -> id
    | None -> (failwith("Wrong Juster state: event id not in lines") : nat)
    end;
    store.activeLines := Map.remove(eventId, store.activeLines);

    var line := case Map.find_opt(lineId, store.lines) of
    | Some(id) -> id
    | None -> (failwith("Wrong Juster state: line is not found") : lineType)
    end;
    line.isRunning := False;
    store.lines := Map.update(lineId, Some(line), store.lines);

    (* adding withdrawable liquidity to the pool: *)
    const newWithdrawable = reward * line.lockedShares / line.lastTotalShares;

    store.withdrawableLiquidity := store.withdrawableLiquidity + newWithdrawable;

    (* TODO: is it possible that this withdrawableLiquidity would be less than
        the sum of the claims because of the nat divison?
        for example totalShares == 3, liquidity amount is 100 mutez, two
        claims for 1 share (each for 33 mutez), total 66... looks OK, but need
        to make sure
    *)

} with ((nil: list(operation)), store)


function createEvents(
    const lineIds : list(nat);
    var store : storage) : (list(operation) * storage) is
block {
    skip;
} with ((nil: list(operation)), store)


function main (const params : action; var s : storage) : (list(operation) * storage) is
case params of
| AddLine(p) -> addLine(p, s)
| DepositLiquidity(p) -> depositLiquidity(s)
| ClaimLiquidity(p) -> claimLiquidity(p, s)
| WithdrawLiquidity(p) -> withdrawLiquidity(p, s)
| PayReward(p) -> payReward(p, s)
| CreateEvents(p) -> createEvents(p, s)
end

