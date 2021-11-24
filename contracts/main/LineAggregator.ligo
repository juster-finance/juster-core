type lineType is record [
    lastBetsCloseTime : timestamp;
    currencyPair : string;
    targetDynamics : nat;
    liquidityPercent : nat;
    rateAboveEq : nat;
    rateBelow : nat;
]

type providerType is record [
    shares : nat;
    (* withdrawable events is events where provider can get his share,
        key: eventId
        value: sharesCount
    *)
    withdrawableEvents : map(nat, nat);
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
        key: eventId
        value: shares*totalShares
    *)
    claims : big_map(nat, nat*nat);

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
    skip;
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

