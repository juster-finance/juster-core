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
type profitLossLedgerType is big_map(ledgerKey, int)

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
    betsForLiquidityPoolSum : tez;
    betsAgainstLiquidityPoolSum : tez;

    (* Expected payments for LP if one of the pool wins,
        can be positive (LP in +) or negative (LP in -),
        calculated per one share (): *)
    winForProfitLossPerShare : int;
    winAgainstProfitLossPerShare : int;
    sharePrecision : nat;

    (* This is total liquidity provided through provideLiquidity method, it is
        used to calculate profits *)
    totalLiquidityProvided : tez;

    (* FirstProviderForSharesSum & FirstProviderAgainstSharesSum is the size of one share of LP.
        They are setted up when first liquidity provided and then used to calculate additional
        share emissions for another LP. So the first LP always have 100% of the shares and for
        all new providers new shares is emitted.

        These shares included reduced in time multiplicator and could also include another bonus distribution multiplicators.
        At the withdeaw this shares used in combination with winForProfitLossPerShare / winAgainstProfitLossPerShare to
        calculate LP return
    *)
    firstProviderForSharesSum : tez;
    firstProviderAgainstSharesSum : tez;

    totalLiquidityForSharesSum : tez;
    totalLiquidityAgainstSharesSum : tez;

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

    (* Ledger with winning amounts for participants if "For" wins: *)
    betsForWinningLedger : ledgerType;

    (* Ledger with winning amounts for participants if "Against" wins: *)
    betsAgainstWinningLedger : ledgerType;

    (* There are three ledgers used to manage liquidity:
        - one with total provided value needed to return in withdrawal,
        - and two with liquidity bonus, that used to calculate share of profits / losses *)
    providedLiquidityLedger : ledgerType;
    liquidityForSharesLedger : ledgerType;
    liquidityAgainstSharesLedger : ledgerType;

    (* Profit / loss entrypoint of LPs, used to calculate their profits / losses without including
        p/l that was formed before they provided liquidity *)
    winForProfitLossPerShareAtEntry : profitLossLedgerType;
    winAgainstProfitLossPerShareAtEntry : profitLossLedgerType;
    (* TODO: do it really needed to have this long names?
        maybe there are the good ideas how to reduce them to 3-4 words? *)

    (* Keeping all provided bets for the Force Majeure, in case if
        they needed to be returned *)
    depositedBets : ledgerType;

    lastEventId : eventIdType;
    closeCallEventId : eventIdType;
    measurementStartCallEventId : eventIdType;
]
