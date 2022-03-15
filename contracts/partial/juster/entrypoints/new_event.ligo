function newEvent(
    const eventParams : newEventParams;
    var store : storage) : (list(operation) * storage) is
block {

    const config : configType = store.config;
    const fees : tez = config.measureStartFee + config.expirationFee;

    if fees =/= Tezos.amount then
        failwith("measureStartFee and expirationFee should be provided")
    else skip;

    if eventParams.measurePeriod > config.maxMeasurePeriod then
        failwith("measurePeriod is exceed maximum value")
    else skip;

    if eventParams.measurePeriod < config.minMeasurePeriod then
        failwith("measurePeriod is less than minimal value")
    else skip;

    const periodToBetsClose : int = eventParams.betsCloseTime - Tezos.now;
    if periodToBetsClose <= 0 then
        failwith("betsCloseTime should be in the future")
    else skip;

    if abs(periodToBetsClose) > config.maxPeriodToBetsClose then
        failwith("betsCloseTime is exceed maximum allowed period")
    else skip;

    if abs(periodToBetsClose) < config.minPeriodToBetsClose then
        failwith("betsCloseTime is less than minimal allowed period")
    else skip;

    if eventParams.liquidityPercent > config.maxLiquidityPercent then
        failwith("liquidityPercent is exceed maximum value")
    else skip;

    if eventParams.liquidityPercent < config.minLiquidityPercent then
        failwith("liquidityPercent is less than minimal value")
    else skip;

    if config.isEventCreationPaused then
        failwith("Event creation is paused")
    else skip;

    const newEvent : eventType = record[
        currencyPair = eventParams.currencyPair;
        createdTime = Tezos.now;
        targetDynamics = eventParams.targetDynamics;
        betsCloseTime = eventParams.betsCloseTime;
        measureOracleStartTime = (None : option(timestamp));
        startRate = (None : option(nat));
        measurePeriod = eventParams.measurePeriod;
        isClosed = False;
        closedOracleTime = (None : option(timestamp));
        closedRate = (None : option(nat));
        closedDynamics = (None : option(nat));
        isBetsAboveEqWin = (None : option(bool));
        poolAboveEq = 0tez;
        poolBelow = 0tez;
        totalLiquidityShares = 0n;
        liquidityPercent = eventParams.liquidityPercent;
        measureStartFee = config.measureStartFee;
        expirationFee = config.expirationFee;
        rewardCallFee = config.rewardCallFee;
        oracleAddress = config.oracleAddress;
        maxAllowedMeasureLag = config.maxAllowedMeasureLag;
        isForceMajeure = False;
        creator = Tezos.sender;
    ];

    store.events[store.nextEventId] := newEvent;
    store.nextEventId := store.nextEventId + 1n;

} with ((nil: list(operation)), store)
