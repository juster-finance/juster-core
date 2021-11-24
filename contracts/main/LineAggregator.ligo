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

    eventResults : big_map(nat, tez);
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

    (* TODO: assert that shares < providerAddress shares in ledger *)

    for lineId -> lineParams in map store.lines block {
        store.claims := case lineParams.currentEventId of
        | Some(eventId) -> Big_map.add(
            (eventId, providerAddress),
            (providerShares, store.totalShares),
            store.claims
        )
        | None -> store.claims
        end;
    }
} with ((nil: list(operation)), store)


function withdrawLiquidity(
    const eventIds : list(nat);
    var store : storage) : (list(operation) * storage) is
block {
    skip;
} with ((nil: list(operation)), store)


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

