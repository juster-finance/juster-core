function calcFreeLiquidity(const store : storage) : int is
    Tezos.balance/1mutez
    - store.withdrawableLiquidity
    - store.entryLiquidity

function checkIsEnoughLiquidity(const store : storage) : unit is
    if calcFreeLiquidity(store) < int(store.nextLiquidity / store.precision)
    then failwith(PoolErrors.noLiquidity)
    else unit;

function calcLiquidityPayout(const store : storage; const newEventFee : tez) : tez is
    block {

        const maxLiquidity = int(store.nextLiquidity / store.precision);
        const freeLiquidity = calcFreeLiquidity(store);

        var liquidityAmount := if maxLiquidity > freeLiquidity
            then freeLiquidity
            else maxLiquidity;

        var liquidityAmount := liquidityAmount - newEventFee/1mutez;

        if liquidityAmount <= 0
        then failwith(PoolErrors.noLiquidity)
        else skip;

    } with abs(liquidityAmount) * 1mutez

function getEntry(const entryId : nat; const store : storage) : entryType is
    getOrFail(entryId, store.entries, PoolErrors.entryNotFound)

function getPosition(const positionId : nat; const store : storage) : positionType is
    getOrFail(positionId, store.positions, PoolErrors.positionNotFound)

function getEvent(const eventId : nat; const store : storage) : eventType is
    getOrFail(eventId, store.events, PoolErrors.eventNotFound)

function getLine(const lineId : nat; const store : storage) : lineType is
    getOrFail(lineId, store.lines, PoolErrors.lineNotFound)

function getClaim(const key : claimKey; const store : storage) : claimParams is
    getOrFail(key, store.claims, PoolErrors.claimNotFound)

function checkHasActiveEvents(const store : storage) : unit is
    if store.maxEvents = 0n
    then failwith(PoolErrors.noActiveEvents)
    else unit;

function calcTotalLiquidity(const store : storage) : int is
    Tezos.balance/1mutez
    - store.withdrawableLiquidity
    - store.entryLiquidity
    + store.activeLiquidity;

function absPositive(const value : int) is if value >= 0 then abs(value) else 0n

function calcFreeEventSlots(const store : storage) is
    store.maxEvents - Map.size(store.activeEvents)

function checkHaveFreeEventSlots(const store : storage) is
    if calcFreeEventSlots(store) <= 0
    then failwith(PoolErrors.noFreeEventSlots)
    else unit;

function increaseMaxActiveEvents(const count : nat; var store : storage) is
block {
    const newMaxActiveEvents = store.maxEvents + count;
    store.nextLiquidity :=
        store.nextLiquidity * store.maxEvents / newMaxActiveEvents;
    store.maxEvents := newMaxActiveEvents;
} with store

function decreaseMaxActiveEvents(const count : nat; var store : storage) is
block {
    if count >= store.maxEvents
    then failwith(PoolErrors.noActiveEvents)
    else skip;

    const newMaxActiveEvents = abs(store.maxEvents - count);

    store.nextLiquidity :=
        store.nextLiquidity * store.maxEvents / newMaxActiveEvents;
    store.maxEvents := newMaxActiveEvents;
} with store

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
    if Tezos.now < line.lastBetsCloseTime - int(line.advanceTime)
    then failwith(PoolErrors.eventNotReady)
    else unit;

function calcBetsCloseTime(const line : lineType) is
block {
    var periods := (Tezos.now - line.lastBetsCloseTime) / line.betsPeriod + 1n;

    (* Case when event runs in advance: *)
    if Tezos.now < line.lastBetsCloseTime
    then periods := periods + 1n
    else skip;

    var nextBetsCloseTime := line.lastBetsCloseTime + line.betsPeriod*periods;
    const timeToEvent = nextBetsCloseTime - Tezos.now;

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
        - Tezos.now;

    if duration <= 0
    then failwith(PoolErrors.wrongState)
    else skip;
} with abs(duration);

function getNewEventFee(const justerAddress : address) is
block {
    const config = getConfig(justerAddress);
} with config.expirationFee + config.measureStartFee

function getClaimedShares(const key : claimKey; const store : storage) is
    case Big_map.find_opt(key, store.claims) of [
    | Some(claim) -> claim.shares
    | None -> 0n
    ];

(* event provided calculation is rounded up: *)
function calcEventProvided(const shares : nat; const event : eventType) is
    case ediv(shares * event.provided, event.totalShares) of [
    | Some(quotient, remainder) -> if remainder > 1n
        then quotient + 1n
        else quotient
    | None -> failwith("DIV/0")
    ];

function increaseLocked(const shares : nat; const event : eventType) is
block {
    const newLockedShares = event.lockedShares + shares;
    if newLockedShares > event.totalShares
    then failwith(PoolErrors.wrongState)
    else skip;
} with event with record [
    lockedShares = newLockedShares;
];

function getEventResult(const event : eventType) is
    case event.result of [
    | Some(result) -> result
    | None -> (failwith(PoolErrors.eventNotFinished) : nat)
    ];

