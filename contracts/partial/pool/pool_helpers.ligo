function calcFreeLiquidity(const store : storage) : int is
    Tezos.balance/1mutez
    - store.withdrawableLiquidity
    - store.entryLiquidity

function checkIsEnoughLiquidity(const store : storage) : unit is
    if calcFreeLiquidity(store) < int(store.nextLiquidity / store.precision)
    then failwith(PoolErrors.noLiquidity)
    else unit;

function calcLiquidityPayout(const store : storage) : tez is
    block {
        checkIsEnoughLiquidity(store);

        var liquidityAmount :=
            store.nextLiquidity / store.precision
            - store.newEventFee/1mutez;

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
    if line.maxEvents = 0n
    then failwith(PoolErrors.emptyLine)
    else unit

function checkDepositIsNotPaused(const store : storage) is
    if store.isDepositPaused
    then failwith(PoolErrors.depositIsPaused)
    else unit

function getNewEventEntry(const justerAddress : address) is
    case (Tezos.get_entrypoint_opt("%newEvent", justerAddress)
          : option(contract(newEventParams))) of
    | None -> (failwith(PoolErrors.justerNewEventNotFound) : contract(newEventParams))
    | Some(entry) -> entry
    end

function getNextEventId(const justerAddress : address) is
    case (Tezos.call_view("getNextEventId", Unit, justerAddress) : option(nat)) of
    | Some(id) -> id
    | None -> (failwith(PoolErrors.justerGetNextEventIdNotFound) : nat)
    end

function getProvideLiquidityEntry(const justerAddress : address) is
    case (Tezos.get_entrypoint_opt("%provideLiquidity", justerAddress)
          : option(contract(provideLiquidityParams))) of
    | None -> (failwith(PoolErrors.justerProvideLiquidityNotFound) : contract(provideLiquidityParams))
    | Some(con) -> con
    end

function getLineIdByEventId(const eventId : nat; const store : storage) is
    case Map.find_opt(eventId, store.activeEvents) of
    | Some(id) -> id
    | None -> (failwith(PoolErrors.activeNotFound) : nat)
    end

function checkHaveNoEvent(const eventId : nat; const store : storage) is
    if Big_map.mem(eventId, store.events)
    then failwith(PoolErrors.eventIdTaken)
    else unit

