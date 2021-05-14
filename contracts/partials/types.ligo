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
| For of unit
| Against of unit

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
type newEventConfigType is record [

    (* Fees, that should be provided during contract origination *)
    measureStartFee : tez;
    expirationFee : tez;

    (* Fees, that taken from participants if they doesn't withdraw in time *)
    rewardCallFee : tez;

    (* oracle in florencenet: KT1SUP27JhX24Kvr11oUdWswk7FnCW78ZyUn *)
    (* oracle in edo2net:     KT1RCNpUEDjZAYhabjzgz1ZfxQijCDVMEaTZ *)
    oracleAddress : address;

    targetDynamicsPrecision : nat;
    sharePrecision : nat;
    liquidityPrecision : nat;
    (* Precision used in ratio calculations *)
    ratioPrecision : nat;

    minMeasurePeriod : nat;
    maxMeasurePeriod : nat;

    (* min/max allowed window that limits betsCloseTime *)
    minPeriodToBetsClose : nat;
    maxPeriodToBetsClose : nat;

    (* TODO: maybe control min/max liquidity percent and allow events
        with different percents? (the way measurePeriod is setted) *)
    liquidityPercent : nat;

    (* Maximal amplitude that affects ratio in one bet: *)
    (* TODO:? maxRatioChange : nat; -need to be added to eventType *)

    (* Minimal value in tez that should be keept in pool *)
    minPoolSize : tez;

    (* Time window when startMeasurement / close should be called
        (or it would considered as Force Majeure) *)
    maxAllowedMeasureLag : nat;

    (* Time, used for filling timestamp values while they have no
        meaning value:
        TODO: maybe it is better to use option(timestamp) ? *)
    defaultTime : timestamp;
]

type updateConfigParam is newEventConfigType -> newEventConfigType

type eventType is record [
    currencyPair : string;
    createdTime : timestamp;

    (* targetDynamics is natural number in grades of targetDynamicsPrecision
        more than targetDynamicsPrecision means price is increased,
        less targetDynamicsPrecision mean price is decreased *)
    targetDynamics : nat;
    targetDynamicsPrecision : nat;

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
    isBetsForWin : bool;

    (* Current liquidity in for and against pools, this is used to calculate current ratio: *)
    poolFor : tez;
    poolAgainst : tez;

    totalLiquidityShares : nat;
    sharePrecision : nat;

    (* Liquidity provider bonus: numerator & denominator *)
    liquidityPercent : nat;
    liquidityPrecision : nat;

    measureStartFee : tez;
    expirationFee : tez;
    rewardCallFee : tez;

    ratioPrecision : nat;
    oracleAddress : address;

    minPoolSize : tez;
    maxAllowedMeasureLag : nat;
]


type newEventParams is record [
    currencyPair : string;
    targetDynamics : nat;
    betsCloseTime : timestamp;
    measurePeriod : nat;
]


type provideLiquidityParams is record [
    eventId : nat;

    (* Expected distribution / ratio of the event *)
    expectedRatioFor : nat;
    expectedRatioAgainst : nat;

    (* Max Slippage value in ratioPrecision. if 0n - ratio should be equal to expected,
        if equals K*ratioPrecision, ratio can diff not more than in (K-1) times *)
    maxSlippage : nat;
]


type action is
| NewEvent of newEventParams
| ProvideLiquidity of provideLiquidityParams
| Bet of betParams
| StartMeasurement of nat
| StartMeasurementCallback of callbackReturnedValueMichelson
| Close of nat
| CloseCallback of callbackReturnedValueMichelson
| Withdraw of nat
| UpdateConfig of updateConfigParam


type storage is record [
    events : big_map(nat, eventType);

    (* Ledgers with winning amounts for participants if For/Against wins: *)
    betsFor : ledgerType;
    betsAgainst : ledgerType;

    (* There are two ledgers used to manage liquidity:
        - two with total provided liquidity in for/against pools,
        - and one with LP share used to calculate how winning pool
            would be distributed *)
    providedLiquidityFor : ledgerType;
    providedLiquidityAgainst : ledgerType;
    liquidityShares : ledgerNatType;

    (* Keeping all provided bets for the Force Majeure, in case if
        they needed to be returned *)
    depositedBets : ledgerType;

    lastEventId : nat;
    closeCallId : eventIdType;
    measurementStartCallId : eventIdType;

    newEventConfig : newEventConfigType;

    (* Manager is the one who can change config *)
    manager : address;
]
