function calcFreeLiquidityF(const store : storage) : int is
    Tezos.get_balance()/1mutez * store.precision
    - store.withdrawableLiquidityF
    - store.entryLiquidityF

function calcTotalLiquidityF(const store : storage) : int is
    calcFreeLiquidityF(store) + store.activeLiquidityF;

function calcLiquidityPayout(const store : storage) is
    block {

        const maxLiquidityF = calcTotalLiquidityF(store) / store.maxEvents;
        const freeLiquidityF = calcFreeLiquidityF(store);

        const liquidityAmountF = if maxLiquidityF > freeLiquidityF
            then freeLiquidityF
            else maxLiquidityF;

    } with abs(liquidityAmountF / store.precision)

function excludeFee(const liquidityAmount : nat; const newEventFee : nat) is
    if liquidityAmount > newEventFee
    then abs(liquidityAmount - newEventFee)
    else (failwith(PoolErrors.noLiquidity) : nat)

function getEntry(const entryId : nat; const store : storage) : entryType is
    getOrFail(entryId, store.entries, PoolErrors.entryNotFound)

function getPosition(const positionId : nat; const store : storage) : positionType is
    getOrFail(positionId, store.positions, PoolErrors.positionNotFound)

function getEvent(const eventId : nat; const store : storage) : eventType is
    getOrFail(eventId, store.events, PoolErrors.eventNotFound)

function getLine(const lineId : nat; const store : storage) : lineType is
    getOrFail(lineId, store.lines, PoolErrors.lineNotFound)

function getClaim(const key : claimKey; const store : storage) : nat is
    getOrFail(key, store.claims, PoolErrors.claimNotFound)

(* TODO: replace with absOr(const value : int; const default : nat) ? *)
function absPositive(const value : int) is if value >= 0 then abs(value) else 0n

function absOrFail(const value : int; const msg : string) is
    if value >= 0 then abs(value) else (failwith(msg) : nat)

function calcFreeEventSlots(const store : storage) is
    store.maxEvents - Map.size(store.activeEvents)

function checkHaveFreeEventSlots(const store : storage) is
    if calcFreeEventSlots(store) <= 0
    then failwith(PoolErrors.noFreeEventSlots)
    else unit;

function checkLineIsNotPaused(const line : lineType) is
    if line.isPaused
    then failwith(PoolErrors.lineIsPaused)
    else unit

function checkLineValid(const line : lineType) is
    (* TODO: add check that betsPeriod > 0? *)
    (* TODO: check that advanceTime < minBettingPeriod? *)
    if line.maxEvents = 0n
    then failwith(PoolErrors.emptyLine)
    else unit

function checkDepositIsNotPaused(const store : storage) is
    if store.isDepositPaused
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

function getLineIdByEventId(const eventId : nat; const store : storage) is
    case Map.find_opt(eventId, store.activeEvents) of [
    | Some(id) -> id
    | None -> (failwith(PoolErrors.activeNotFound) : nat)
    ]

function checkEventNotDuplicated(const eventId : nat; const store : storage) is
    if Big_map.mem(eventId, store.events)
    then failwith(PoolErrors.eventIdTaken)
    else unit

function checkLineHaveFreeSlots(
    const lineId : nat;
    const line : lineType;
    const store : storage) is
block {
    function countEvents (const count : nat; const ids : nat*nat) : nat is
        if ids.1 = lineId then count + 1n else count;
    const activeEventsInLine = Map.fold(countEvents, store.activeEvents, 0n);
} with if activeEventsInLine > line.maxEvents
    then failwith(PoolErrors.noFreeEventSlots)
    else unit;

function checkReadyToEmitEvent(const line : lineType) is
    if Tezos.get_now() < line.lastBetsCloseTime - int(line.advanceTime)
    then failwith(PoolErrors.eventNotReady)
    else unit;

function calcBetsCloseTime(const line : lineType) is
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

function calcDuration(const line : lineType) is
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

function getClaimedAmountOrZero(const key : claimKey; const store : storage) is
    case Big_map.find_opt(key, store.claims) of [
    | Some(claimAmount) -> claimAmount
    | None -> 0n
    ];

function getEventResult(const event : eventType) is
    case event.result of [
    | Some(result) -> result
    | None -> (failwith(PoolErrors.eventNotFinished) : nat)
    ];

function ceilDiv(const num: nat; const denom: nat) is
    case ediv(num, denom) of [
    | Some(result, remainder) -> if remainder > 0n then result + 1n else result
    | None -> (failwith("DIV / 0"): nat)
    ];
