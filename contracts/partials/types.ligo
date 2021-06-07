type callbackReturnedValue is record [
    currencyPair : string;
    lastUpdate : timestamp;
    rate : nat
]

type callbackReturnedValueMichelson is michelson_pair_right_comb(callbackReturnedValue)

type callbackEntrypoint is contract(callbackReturnedValueMichelson)

type oracleParam is string * contract(callbackReturnedValueMichelson)

type eventIdType is option(nat)

type betType is
| AboveEq of unit
| Bellow of unit

type betParams is record [
    eventId : nat;
    bet : betType;
    minimalWinAmount : tez;
]

type ledgerKey is (address*nat)

(* ledger key is address and event ID *)
type ledgerType is big_map(ledgerKey, tez)

(* another ledger, used to calculate shares: *)
type ledgerNatType is big_map(ledgerKey, nat)


(* params that used in new event creation that can be configured by
    contract manager (changing this params would not affect existing events
    and would only applied to future events): *)
type configType is record [

    (* Fees, that should be provided during contract origination *)
    measureStartFee : tez;
    expirationFee : tez;

    (* Fees, that taken from participants if they doesn't withdraw in time *)
    rewardCallFee : tez;

    (* oracle in florencenet: KT1SUP27JhX24Kvr11oUdWswk7FnCW78ZyUn *)
    (* oracle in edo2net:     KT1RCNpUEDjZAYhabjzgz1ZfxQijCDVMEaTZ *)
    oracleAddress : address;

    minMeasurePeriod : nat;
    maxMeasurePeriod : nat;

    (* min/max allowed window that limits betsCloseTime *)
    minPeriodToBetsClose : nat;
    maxPeriodToBetsClose : nat;

    (* min/max allowed window that limits liquidityPercent *)
    minLiquidityPercent : nat;
    maxLiquidityPercent : nat;

    (* Time window when startMeasurement / close should be called
        (or it would considered as Force Majeure) *)
    maxAllowedMeasureLag : nat;

    (* Time, used for filling timestamp values while they have no
        meaning value:
        TODO: maybe it is better to use option(timestamp) ? *)
    defaultTime : timestamp;

    (* Period following the close in seconds after which rewardFee is activated *)
    rewardFeeSplitAfter : nat;

    (* Amount of profits that cutted from provider and that
        go to the community fond: *)
    providerProfitFee : nat;

    (* Flag that used to pause event creation: *)
    isEventCreationPaused : bool;
]

type updateConfigParam is configType -> configType

type eventType is record [
    currencyPair : string;
    createdTime : timestamp;

    (* targetDynamics is natural number in grades of targetDynamicsPrecision
        more than targetDynamicsPrecision means price is increased,
        less targetDynamicsPrecision mean price is decreased *)
    targetDynamics : nat;

    (* time since new bets would not be accepted *)
    betsCloseTime : timestamp;

    (* time that setted when recieved callback from startMeasurement *)
    measureOracleStartTime : timestamp;
    isMeasurementStarted : bool;

    (* the rate at the begining of the measurement *)
    startRate : nat;

    (* measurePeriod is amount of seconds from measureStartTime before 
        anyone can call close tp finish event *)
    measurePeriod : nat;

    isClosed : bool;
    closedOracleTime : timestamp;

    (* keeping closedRate for debugging purposes, it can be deleted after *)
    closedRate : nat;
    closedDynamics : nat;
    isBetsAboveEqWin : bool;

    (* Current liquidity in aboveEq and Bellow pools, this is used to calculate current ratio: *)
    poolAboveEq : tez;
    poolBellow : tez;

    totalLiquidityShares : nat;

    (* Liquidity provider bonus: numerator & denominator *)
    liquidityPercent : nat;

    measureStartFee : tez;
    expirationFee : tez;
    rewardCallFee : tez;

    oracleAddress : address;

    maxAllowedMeasureLag : nat;

    (* Flag that used to activate crash withdrawals *)
    isForceMajeure : bool;

    (* Calculating participants/providers count to remove them from events
        after all withdrawals completed: *)
    participants : nat;
]


type newEventParams is record [
    currencyPair : string;
    targetDynamics : nat;
    betsCloseTime : timestamp;
    measurePeriod : nat;
    liquidityPercent : nat;
]


type provideLiquidityParams is record [
    eventId : nat;

    (* Expected distribution / ratio of the event *)
    expectedRatioAboveEq : nat;
    expectedRatioBellow : nat;

    (* Max Slippage value in ratioPrecision. if 0n - ratio should be equal to expected,
        if equals K*ratioPrecision, ratio can diff not more than in (K-1) times *)
    maxSlippage : nat;
]


type withdrawParams is record [
    eventId : nat;
    participantAddress : address;
]


type action is
| NewEvent of newEventParams
| ProvideLiquidity of provideLiquidityParams
| Bet of betParams
| StartMeasurement of nat
| StartMeasurementCallback of callbackReturnedValueMichelson
| Close of nat
| CloseCallback of callbackReturnedValueMichelson
| Withdraw of withdrawParams
| UpdateConfig of updateConfigParam
| TriggerForceMajeure of nat
| SetDelegate of option (key_hash)
| Default of unit
| ClaimBakingRewards of unit
| ClaimRetainedProfits of unit


type storage is record [
    events : big_map(nat, eventType);

    (* Ledgers with winning amounts for participants if AboveEq/Bellow wins: *)
    betsAboveEq : ledgerType;
    betsBellow : ledgerType;

    (* There are two ledgers used to manage liquidity:
        - two with total provided liquidity in AboveEq/Bellow pools,
        - and one with LP share used to calculate how winning pool
            would be distributed *)
    providedLiquidityAboveEq : ledgerType;
    providedLiquidityBellow : ledgerType;
    liquidityShares : ledgerNatType;

    (* Keeping all provided bets for the Force Majeure, in case if
        they needed to be returned *)
    depositedBets : ledgerType;

    lastEventId : nat;
    closeCallId : eventIdType;
    measurementStartCallId : eventIdType;

    config : configType;

    (* Manager is the one who can change config *)
    manager : address;

    targetDynamicsPrecision : nat;
    sharePrecision : nat;
    liquidityPrecision : nat;
    ratioPrecision : nat;
    providerProfitFeePrecision : nat;

    bakingRewards : tez;
    retainedProfits : tez;
]
