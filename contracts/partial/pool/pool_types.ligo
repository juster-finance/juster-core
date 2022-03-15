
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
        lastBetsCloseTime
        {2022-03-11: but this is not very effective liquidity use} *)
    (* TODO: consider having min time delta before next betsCloseTime to prevent
        possibility of event creation with very small period until betsClose *)

    (* TODO: consider having isPaused field *)
    (* TODO: consider having Juster address in line instead of storage
        (easier to update and possibility to have multiple juster contracts) *)
]

type positionType is record [
    (* TODO: replace provider with NFT token_id that represents this position? *)
    provider : address;
    shares : nat;
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
    provider : address;
]

(*  entry is not accepted yet position including provider address,
    timestamp when liquidity can be accepted and amount of this liquidity *)
type entryType is record [
    provider : address;
    acceptAfter : timestamp;
    amount : nat;
]

type storage is record [
    nextLineId: nat;

    (* lines is ledger with all possible event lines that can be created *)
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

    (* added liquidity that not recognized yet *)
    entryLiquidity : nat;

    (* amount of time before liquidity can be recognized *)
    entryLockPeriod : nat;
    (* TODO: ^^ consider moving this to `configs` and having configs ledger *)

    entries : big_map(nat, entryType);
    nextEntryId : nat;

    claims : big_map(claimKey, claimParams);

    manager : address;

    juster : address;

    (* TODO: remove newEventFee and use config view instead
            (require Juster redeploying in hangzhounet) *)
    newEventFee : tez;

    (* aggregated max active events required to calculate liquidity amount *)
    maxActiveEvents : nat;

    (* As far as liquidity can be added in the same block as a new event created
        it is required to understand if this liquidity was added before or
        after event creation. There is why special counter used instead of
        using time/level *)
    counter : nat;

    nextEventLiquidity : nat;

    (* TODO: condider having withdrawStats ledger with some data that can be
        used in reward programs *)
    (* TODO: to calculate withdrawalStats it might be good to have
        - createdEventsCount
        - providedPerShare
        - maybe something else
        - it might be in some kind of stats record
    *)
]


type claimLiquidityParams is record [
    positionId : nat;
    shares : nat;
]

type withdrawLiquidityParams is list(claimKey)

(* entrypoints:
    - addLine: adding new line of typical events, only manager can add new lines
    - depositLiquidity: creating request for adding new liquidity
    - approveLiquidity: adds requested liquidity to the aggregator
    - cancelLiquidity: cancels request for adding new liquidity
    - claimLiquidity: creates request for withdraw liquidity from all current events
    - withdrawLiquidity: withdraws claimed events
    - payReward: callback that receives withdraws from Juster
    - createEvent: creates new event in line, anyone can call this
*)

type action is
| AddLine of lineType
| DepositLiquidity of unit
| ApproveLiquidity of nat
| CancelLiquidity of nat
| ClaimLiquidity of claimLiquidityParams
| WithdrawLiquidity of withdrawLiquidityParams
| PayReward of nat
| CreateEvent of nat
(* TODO: consider having CreateEvents of list(nat) *)
(* TODO: removeLine?
        1) consider to have at least one line to support nextEventLiquidity
        2) it is better to stopLine / pauseLine / triggerPauseLine instead so the info can be used in views later
*)
(* TODO: updateLine? to change ratios for example, only manager can call
        2022-03-11: it is better to have just stopLine/pauseLine + addLine so any updates would
            require both removing and adding line (this will allow use this data in the
            reward programs in the future, updating lines will remove info about this lines
*)
(* TODO: updateNewEventFee if it changed in Juster, only manager can call
    - it is better read config from Juster views
    - maybe it would be good to have here some kind of config too (with juster address etc)
    - and lines can be binded to different configs
*)
(* TODO: updateEntryLockPeriod {or move this to updateConfig} *)
(* TODO: pauseEvents *)
(* TODO: pauseDepositLiquidity *)
(* TODO: views: getLineOfEvent, getNextEventLiquidity, getWithdrawableLiquidity,
    getNextPositionId, getNextEntryPositionId, getNextClaimId,
    getConfig, getWithdrawalStat ... etc *)
(* TODO: views: getPosition(id), getClaim(id), getEvent? *)
(* TODO: default entrypoint for baking rewards *)
(* TODO: entrypoint to change delegator
        - reuse Juster code
*)
(* TODO: change manager entrypoints handshake
        - reuse Juster code
*)


