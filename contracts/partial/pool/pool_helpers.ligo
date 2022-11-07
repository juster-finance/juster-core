function calcFreeLiquidityF(const s : storageT) : int is
    Tezos.get_balance()/1mutez * s.precision
    - s.withdrawableLiquidityF
    - s.entryLiquidityF

function calcTotalLiquidityF(const s : storageT) : int is
    calcFreeLiquidityF(s) + s.activeLiquidityF;

function calcLiquidityPayout(const s : storageT) is
    block {

        const maxLiquidityF = calcTotalLiquidityF(s) / s.maxEvents;
        const freeLiquidityF = calcFreeLiquidityF(s);

        const liquidityAmountF = if maxLiquidityF > freeLiquidityF
            then freeLiquidityF
            else maxLiquidityF;

    } with abs(liquidityAmountF / s.precision)

function excludeFee(const liquidityAmount : nat; const newEventFee : nat) is
    if liquidityAmount > newEventFee
    then abs(liquidityAmount - newEventFee)
    else (failwith(PoolErrors.noLiquidity) : nat)

function getEntry(const entryId : nat; const s : storageT) : entryT is
    getOrFail(entryId, s.entries, PoolErrors.entryNotFound)

function getShares(const provider : address; const s : storageT) : nat is
    getOrFail(provider, s.shares, PoolErrors.noSharesToClaim)

function getEvent(const eventId : nat; const s : storageT) : eventT is
    getOrFail(eventId, s.events, PoolErrors.eventNotFound)

function getLine(const lineId : nat; const s : storageT) : lineT is
    getOrFail(lineId, s.lines, PoolErrors.lineNotFound)

function getClaim(const key : claimKeyT; const s : storageT) : nat is
    getOrFail(key, s.claims, PoolErrors.claimNotFound)

(* TODO: replace with absOr(const value : int; const default : nat) ? *)
function absPositive(const value : int) is if value >= 0 then abs(value) else 0n

function absOrFail(const value : int; const msg : string) is
    if value >= 0 then abs(value) else (failwith(msg) : nat)

function calcFreeEventSlots(const s : storageT) is
    s.maxEvents - Map.size(s.activeEvents)

function checkHaveFreeEventSlots(const s : storageT) is
    if calcFreeEventSlots(s) <= 0
    then failwith(PoolErrors.noFreeEventSlots)
    else unit;

function checkLineIsNotPaused(const line : lineT) is
    if line.isPaused
    then failwith(PoolErrors.lineIsPaused)
    else unit

function checkLineValid(const line : lineT) is {
    if line.betsPeriod = 0n
    then failwith(PoolErrors.zeroBetsPeriod)
    else skip;

    if line.maxEvents = 0n
    then failwith(PoolErrors.emptyLine)
    else skip;
} with unit

function checkDepositIsNotPaused(const s : storageT) is
    if s.isDepositPaused
    then failwith(PoolErrors.depositIsPaused)
    else unit

function getNewEventEntry(const justerAddress : address) is
    case (Tezos.get_entrypoint_opt("%newEvent", justerAddress)
          : option(contract(newEventParams))) of [
    | None -> (failwith(PoolErrors.justerNewEventNotFound) : contract(newEventParams))
    | Some(entry) -> entry
    ]

function getNextEventId(const justerAddress : address) is
    case (Tezos.call_view("getNextEventId", Unit, justerAddress) : option(nat)) of [
    | Some(id) -> id
    | None -> (failwith(PoolErrors.justerGetNextEventIdNotFound) : nat)
    ]

function getConfig(const justerAddress : address) is
    case (Tezos.call_view("getConfig", Unit, justerAddress) : option(configType)) of [
    | Some(id) -> id
    | None -> (failwith(PoolErrors.justerGetConfigNotFound) : configType)
    ]

function getProvideLiquidityEntry(const justerAddress : address) is
    case (Tezos.get_entrypoint_opt("%provideLiquidity", justerAddress)
          : option(contract(provideLiquidityParams))) of [
    | None -> (failwith(PoolErrors.justerProvideLiquidityNotFound) : contract(provideLiquidityParams))
    | Some(con) -> con
    ]

function getLineIdByEventId(const eventId : nat; const s : storageT) is
    case Map.find_opt(eventId, s.activeEvents) of [
    | Some(id) -> id
    | None -> (failwith(PoolErrors.activeNotFound) : nat)
    ]

function checkEventNotDuplicated(const eventId : nat; const s : storageT) is
    if Big_map.mem(eventId, s.events)
    then failwith(PoolErrors.eventIdTaken)
    else unit

function checkLineHaveFreeSlots(
    const lineId : nat;
    const line : lineT;
    const s : storageT) is
block {
    function countEvents (const count : nat; const ids : nat*nat) : nat is
        if ids.1 = lineId then count + 1n else count;
    const activeEventsInLine = Map.fold(countEvents, s.activeEvents, 0n);
} with if activeEventsInLine > line.maxEvents
    then failwith(PoolErrors.noFreeEventSlots)
    else unit;

function checkReadyToEmitEvent(const line : lineT) is
    if Tezos.get_now() < line.lastBetsCloseTime - int(line.advanceTime)
    then failwith(PoolErrors.eventNotReady)
    else unit;

function calcBetsCloseTime(const line : lineT) is
block {
    var periods := (Tezos.get_now() - line.lastBetsCloseTime) / line.betsPeriod + 1n;

    (* Case when event runs in advance: *)
    if Tezos.get_now() < line.lastBetsCloseTime
    then periods := periods + 1n
    (* TODO: maybe replace this with `then periods := 1n`? *)
    else skip;

    var nextBetsCloseTime := line.lastBetsCloseTime + line.betsPeriod*periods;
    const timeToEvent = nextBetsCloseTime - Tezos.get_now();

    (* Case when event is late: *)
    if abs(timeToEvent) < line.minBettingPeriod
    then nextBetsCloseTime := nextBetsCloseTime + int(line.betsPeriod)
    else skip;
} with nextBetsCloseTime

(* TODO: consider removing this func as it is not used anymore *)
function calcDuration(const line : lineT) is
block {
    const duration =
        int(line.measurePeriod)
        + line.lastBetsCloseTime
        - Tezos.get_now();

    if duration <= 0
    then failwith(PoolWrongState.negativeDuration)
    else skip;
} with abs(duration);

function getNewEventFee(const justerAddress : address) is
block {
    const config = getConfig(justerAddress);
} with config.expirationFee + config.measureStartFee

function getClaimedAmountOrZero(const key : claimKeyT; const s : storageT) is
    getOrDefault(key, s.claims, 0n)

function getSharesOrZero(const provider : address; const s : storageT) : nat is
    getOrDefault(provider, s.shares, 0n)

function getEventResult(const event : eventT) is
    case event.result of [
    | Some(result) -> result
    | None -> (failwith(PoolErrors.eventNotFinished) : nat)
    ];

function ceilDiv(const num: nat; const denom: nat) is
    case ediv(num, denom) of [
    | Some(result, remainder) -> if remainder > 0n then result + 1n else result
    | None -> (failwith("DIV / 0"): nat)
    ];

function checkAcceptTime(const entry : entryT) is
    if Tezos.get_now() < entry.acceptAfter
    then failwith(PoolErrors.earlyApprove)
    else unit;

function checkCancelAllowed(const s : storageT) is
    (* cancel allowed only when deposit is paused *)
    if not s.isDepositPaused
    then failwith(PoolErrors.cancelIsNotAllowed)
    else unit;
