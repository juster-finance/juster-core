type lineIdT is nat;
type eventIdT is nat;
type entryIdT is nat;

type lineT is record [
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

type eventT is record [
    result : option(nat);
    (* TODO: consider having isFinished : bool field? Or result as an option
        is enough? *)
    provided : nat;
    claimed : nat;
]

type claimKeyT is record [
    eventId : eventIdT;
    provider : address;
]

(*  entry is not accepted yet position including provider address,
    timestamp when liquidity can be accepted and amount of this liquidity *)
type entryT is record [
    provider : address;
    acceptAfter : timestamp;
    amount : nat;
]

(* durationPoints is integrated amount of shares holded by providers *)
type durationPointsT is record [
    amount : nat;
    updateLevel : nat;
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

type storageT is record [
    nextLineId: lineIdT;
    lines : big_map(lineIdT, lineT);
    activeEvents : map(eventIdT, lineIdT);
    events : big_map(eventIdT, eventT);
    shares : big_map(address, nat);
    totalShares : nat;
    activeLiquidityF : nat;
    withdrawableLiquidityF : nat;
    entryLiquidityF : nat;
    entryLockPeriod : nat;
    entries : big_map(entryIdT, entryT);
    nextEntryId : entryIdT;
    claims : big_map(claimKeyT, nat);
    manager : address;
    maxEvents : nat;
    isDepositPaused : bool;
    metadata : big_map (string, bytes);
    precision : nat;
    proposedManager : address;
    isDisbandAllow : bool;
    durationPoints : big_map(address, durationPointsT);
    totalDurationPoints : nat;
]


type claimLiquidityParamsT is record [
    provider : address;
    shares : nat;
]

type withdrawClaimsParamsT is list(claimKeyT)

type returnT is (list(operation) * storageT)
