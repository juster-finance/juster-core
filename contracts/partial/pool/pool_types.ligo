type lineIdT is nat;
type eventIdT is nat;
type positionIdT is nat;
type entryIdT is nat;

type lineType is record [
    currencyPair : string;
    targetDynamics : nat;
    liquidityPercent : nat;
    rateAboveEq : nat;
    rateBelow : nat;
    measurePeriod : nat;
    betsPeriod : nat;
    lastBetsCloseTime : timestamp;
    maxEvents : nat;
    isPaused : bool;
    juster : address;
    minBettingPeriod : nat;
    advanceTime : nat;
]

type positionType is record [
    provider : address;
    shares : nat;
    (* TODO: is it possible to change entry liquidity units logic to comply with
        new pool logic? *)
    entryLiquidityUnits : nat;
]

type eventType is record [
    result : option(nat);
    (* TODO: consider having isFinished : bool field? Or result as an option
        is enough? *)
    provided : nat;
    claimed : nat;
]

type claimKey is record [
    eventId : eventIdT;
    (* TODO: if position became only shares map(address, nat)
        then claimKey can be eventId + providerAddress
        then claimParams can be simple amount *)
    positionId : positionIdT;
]

(*  entry is not accepted yet position including provider address,
    timestamp when liquidity can be accepted and amount of this liquidity *)
type entryType is record [
    provider : address;
    acceptAfter : timestamp;
    amount : nat;
]

type withdrawalType is record [
    liquidityUnits : nat;
    positionId : nat;
    shares : nat;
    (* TODO: consider adding:
        - added/withdrawn block/time?
        - createdEventsCount?
    *)
]

(*
    lines - is ledger with all possible event lines that can be created
    activeEvents - is mapping between eventId and lineId
    activeLiquidity - aggregates all liquidity that are in activeEvents,
        it is needed to calculate new share amount for new positions
    entryLiquidity - is added liquidity that not recognized yet
    entryLockPeriod - is amount of time before liquidity can be recognized
    maxEvents - is aggregated max active events required to calculate liquidity amount

    counter - As far as liquidity can be added in the same block as a new event created
        it is required to understand if this liquidity was added before or
        after event creation. There is why special counter used instead of
        using time/level
    liquidityUnits - is amount of liquidity provided multiplied by locked time per share
    TODO: add description to other fields or remove it to docs

*)
(* TODO: consider moving `entryLockPeriod` to `configs` and having configs ledger *)

type storage is record [
    nextLineId: lineIdT;
    lines : big_map(lineIdT, lineType);
    activeEvents : map(eventIdT, lineIdT);
    events : big_map(eventIdT, eventType);
    positions : big_map(positionIdT, positionType);
    nextPositionId : positionIdT;
    totalShares : nat;
    activeLiquidityF : nat;
    withdrawableLiquidityF : nat;
    entryLiquidityF : nat;
    entryLockPeriod : nat;
    entries : big_map(entryIdT, entryType);
    nextEntryId : entryIdT;
    claims : big_map(claimKey, nat);
    manager : address;
    maxEvents : nat;
    isDepositPaused : bool;
    metadata : big_map (string, bytes);
    precision : nat;
    proposedManager : address;
    liquidityUnits : nat;
    withdrawals : big_map (nat, withdrawalType);
    nextWithdrawalId : nat;
    isDisbandAllow : bool;
]


type claimLiquidityParams is record [
    positionId : positionIdT;
    shares : nat;
]

type withdrawLiquidityParams is list(claimKey)

