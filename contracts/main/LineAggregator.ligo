type lineType is record [
    currentEventId : option(nat);
    lastBetsCloseTime : timestamp;
    currencyPair : string;
    targetDynamics : nat;
    liquidityPercent : nat;
    rateAboveEq : nat;
    rateBelow : nat;
]

type storage is record [
    nextLineId: nat;

    (* lines is ledger with all possible event lines that can be created *)
    (* TODO: consider type big_map, but then it would not be possible to
        all lines in the cycle *)
    lines : map(nat, lineType);
    activeLines : nat;

    shares : big_map(address, nat);
    totalShares : nat;

    eventResults : big_map(nat, nat);
    withdrawableLiquidity : tez;

    (* claims is liquidity, that can be withdrawn by providers,
        key: eventId*providerAddress
        value: shares*totalShares
    *)

    claims : big_map(nat*address, nat*nat);
    (* TODO: alternative way is to have big_map with
        key: providerAddress
        value: map(eventId, shares*totalShares)
        then it would be possible to iterate onchain (but maybe this is bad idea)
            - anyway this is required to iterate over lines to create this claim

        ALSO can be done with:
        key: claimId
        value: providerAddress*shares*totalShares*list(eventId)
        claims : big_map(nat, nat*nat);
        nextClaimId : nat;
    *)

    manager : address;
    (* TODO: lockedShares: nat; ?*)

    juster : address;
]


type action is
| AddLine of lineType
| DepositLiquidity of unit

(* claiming liquidity with value of shares count allows to withdraw this shares
    from all current events *)
| ClaimLiquidity of nat

(* withdrawing claimed events, parameter is list of event ids *)
| WithdrawLiquidity of list(nat)

(* receiving reward from Juster *)
| GetReward of nat
(* TODO: removeLine? *)


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


function claimLiquidity(
    const shares : nat;
    var store : storage) : (list(operation) * storage) is
block {
    const providerAddress = Tezos.sender;
    const providerSharesOption = Big_map.find_opt(providerAddress, store.shares);
    const providerShares = case providerSharesOption of
    | Some(shares) -> shares
    | None -> (failwith("No provided liquidity") : nat)
    end;

    if shares > providerShares then failwith("Not enough shares") else skip;
    const leftShares = abs(providerShares - shares);

    (* TODO: what happens if provider already requested withdraw for a given
        eventId? For example he requested 50/100 shares and then 50 more.
        There should be possibility to add this shares to the claims:

        need to have addClaim function where either new value added to big map
        either if big map already have some claim for the particiant*eventId
        then it should be increased
    *)

    for lineId -> lineParams in map store.lines block {
        store.claims := case lineParams.currentEventId of
        | Some(eventId) -> Big_map.add(
            (eventId, providerAddress),
            (providerShares, store.totalShares),
            store.claims
        )
        | None -> store.claims
        end;
    };

    store.shares := Big_map.update(providerAddress, Some(leftShares), store.shares);
    (* TODO: Big_map.remove if leftShares == 0n? or this is not important? *)

    (* TODO: assert that store.totalShares > shares? this case should be
        impossible, but feels like this is good to have this check? *)
    store.totalShares := abs(store.totalShares - shares);

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
    const eventIds : list(nat);
    var store : storage) : (list(operation) * storage) is
block {

    const providerAddress = Tezos.sender;

    var withdrawSum := 0n;
    for eventId in list eventIds block {
        const eventResult = case Big_map.find_opt(eventId, store.eventResults) of
        | Some(result) -> result
        | None -> 0n
        end;

        const key = (eventId, providerAddress);
        const eventReward = case Big_map.find_opt(key, store.claims) of
        | Some(claim) -> eventResult * claim.0 / claim.1
        | None -> 0n
        end;

        withdrawSum := withdrawSum + eventReward;
        store.claims := Big_map.remove(key, store.claims);
    };

    const payout = withdrawSum * 1mutez;
    const operations = if payout > 0tez then
        list[prepareOperation(providerAddress, payout)]
    else (nil: list(operation));

} with (operations, store)


function getReward(
    const eventId : nat;
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
| GetReward(p) -> getReward(p, s)
end

