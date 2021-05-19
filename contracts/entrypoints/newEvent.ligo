function newEvent(
    var eventParams : newEventParams;
    var store : storage) : (list(operation) * storage) is
block {
    (* TODO: Checking that betsCloseTime of this event is in the future
        (maybe check that there are some minimal time to make bets,
            that can be controlled by manager) *)
    (* TODO: Checking that measurePeriod is more than some minimal amount
        and maybe less than amount *)
    (* TODO: Check that liquidityPercent is less than 1_000_000 *)

    const config : newEventConfigType = store.newEventConfig;
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

    const newEvent : eventType = record[
        currencyPair = eventParams.currencyPair;
        createdTime = Tezos.now;
        targetDynamics = eventParams.targetDynamics;
        betsCloseTime = eventParams.betsCloseTime;
        measureOracleStartTime = config.defaultTime;
        isMeasurementStarted = False;
        startRate = 0n;
        measurePeriod = eventParams.measurePeriod;
        isClosed = False;
        closedOracleTime = config.defaultTime;
        closedRate = 0n;
        closedDynamics = 0n;
        isBetsForWin = False;
        poolFor = 0tez;
        poolAgainst = 0tez;
        totalLiquidityShares = 0n;
        liquidityPercent = config.liquidityPercent;
        measureStartFee = config.measureStartFee;
        expirationFee = config.expirationFee;
        rewardCallFee = config.rewardCallFee;
        oracleAddress = config.oracleAddress;
        maxAllowedMeasureLag = config.maxAllowedMeasureLag;
        minPoolSize = config.minPoolSize;
    ];

    store.events[store.lastEventId] := newEvent;
    store.lastEventId := store.lastEventId + 1n;

} with ((nil: list(operation)), store)
