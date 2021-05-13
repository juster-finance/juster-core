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

    (* TODO: use entrypoint instead of address, example:
        https://github.com/atomex-me/atomex-fa12-ligo/blob/6e093b484d5cf1ddf66245a6eb9d8d11dfbb45da/src/atomex.ligo#L7 *)
    oracleAddress : address;

    (* Current liquidity in for and against pools, this is used to calculate current ratio: *)
    poolFor : tez;
    poolAgainst : tez;

    totalLiquidityShares : nat;
    sharePrecision : nat;

    (* Liquidity provider bonus: numerator & denominator *)
    liquidityPercent : nat;
    liquidityPrecision : nat;

    (* Fees, that should be provided during contract origination *)
    measureStartFee : tez;
    expirationFee : tez;

    (* Fees, that taken from participants *)
    rewardCallFee : tez;

    (* Precision used in ratio calculations *)
    ratioPrecision : nat;
]


type newEventParams is record [
    currencyPair : string;
    targetDynamics : nat;
    betsCloseTime : timestamp;
    measurePeriod : nat;
    oracleAddress :  address;
    liquidityPercent : nat;
    measureStartFee : tez;
    expirationFee : tez;
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
]
