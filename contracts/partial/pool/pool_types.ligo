
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
    (* TODO: replace provider with NFT token_id that represents this position? *)
    provider : address;
    shares : nat;
    addedCounter : nat;
    entryLiquidityUnits : nat;
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
    provider : address;
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

type storage is record [
    nextLineId: nat;

    (* lines is ledger with all possible event lines that can be created *)
    lines : big_map(nat, lineType);

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

    entries : big_map(nat, entryType);
    nextEntryId : nat;

    claims : big_map(claimKey, claimParams);

    manager : address;

    (* aggregated max active events required to calculate liquidity amount *)
    maxEvents : nat;

    (* As far as liquidity can be added in the same block as a new event created
        it is required to understand if this liquidity was added before or
        after event creation. There is why special counter used instead of
        using time/level *)
    counter : nat;

    nextLiquidity : nat;

    isDepositPaused : bool;

    metadata : big_map (string, bytes);
    precision : nat;

    proposedManager : address;

    (* liquidityUnits is amount of liquidity provided multiplied by locked time per share: *)
    liquidityUnits : nat;
    withdrawals : big_map (nat, withdrawalType);
    nextWithdrawalId : nat;
]


type claimLiquidityParams is record [
    positionId : nat;
    shares : nat;
]

type withdrawLiquidityParams is list(claimKey)

