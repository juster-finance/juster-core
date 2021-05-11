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
    eventId : eventIdType;
    bet : betType;
    minimalWinAmount : tez;
]

type ledgerKey is (address*eventIdType)

(* ledger key is address and event ID *)
type ledgerType is big_map(ledgerKey, tez)

(* another ledgers, used to calculate profit/losses at entry. Can be negative: *)
type diffLedgerType is big_map(ledgerKey, int)

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

    (* Expected payments for LP if one of the pool wins calculated per one share,
        can be positive (LPs in +) or negative (LPs in -) *)
    forProfit : int;
    againstProfit : int;
    (* TODO: if there would be only one liquidity pool name it: profitPerShare *)

    sharePrecision : nat;

    (* Liquidity shares calculated separately for two pools and then distributed
        using pool with participants that did not win *)
    (* TODO: maybe it is complicated and use one ledger for liquidity shares?
        this idea with two ledgers was implemented to equilize balance between different
        liquidity providers, before new model with fixing LP profit/loss at entry was
        implemented.
        ALSO: maybe I should change the type to nat because it is frequently converted
        to int in calculations *)
    totalLiquidityForShares : tez;
    totalLiquidityAgainstShares : tez;

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
    eventId : eventIdType;

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
| StartMeasurement of eventIdType
| StartMeasurementCallback of callbackReturnedValueMichelson
| Close of eventIdType
| CloseCallback of callbackReturnedValueMichelson
| Withdraw of eventIdType


type storage is record [
    events : big_map(eventIdType, eventType);

    (* Ledgers with winning amounts for participants if For/Against wins: *)
    betsFor : ledgerType;
    betsAgainst : ledgerType;

    (* There are three ledgers used to manage liquidity:
        - one with total provided value needed to return in withdrawal,
        - and two with liquidity bonus, that used to calculate share of profits / losses *)
    providedLiquidity : ledgerType;
    liquidityForShares : ledgerType;
    liquidityAgainstShares : ledgerType;

    (* Liquidity providers profits/losses that excluded from calculation
        (used to exclude all expected profit/loss formed before providing new liquidity) *)
    forProfitDiff : diffLedgerType;
    againstProfitDiff : diffLedgerType;

    (* Keeping all provided bets for the Force Majeure, in case if
        they needed to be returned *)
    depositedBets : ledgerType;

    lastEventId : eventIdType;
    closeCallId : eventIdType;
    measurementStartCallId : eventIdType;
]
