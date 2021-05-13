function newEvent(
    var eventParams : newEventParams;
    var s : storage) : (list(operation) * storage) is
block {
    (* TODO: Checking that betsCloseTime of this event is in the future
        (maybe check that there are some minimal time to make bets,
            that can be controlled by manager) *)
    (* TODO: Checking that measurePeriod is more than some minimal amount
        and maybe less than amount *)
    (* TODO: Check that liquidityPercent is less than 1_000_000 *)

    const fees : tez = eventParams.measureStartFee + eventParams.expirationFee;
    if fees =/= Tezos.amount then
        failwith("measureStartFee and expirationFee should be provided")
    else skip;

    (* TODO: separate method to add liquidity *)
    const newEvent : eventType = record[
        currencyPair = eventParams.currencyPair;
        createdTime = Tezos.now;
        targetDynamics = eventParams.targetDynamics;
        targetDynamicsPrecision = 1_000_000n;
        betsCloseTime = eventParams.betsCloseTime;
        measureOracleStartTime = ("2018-06-30T07:07:32Z" : timestamp);
        isMeasurementStarted = False;
        startRate = 0n;

        (* TODO: control measurePeriod, time to betsCloseTime
            min|max from Manager *)
        measurePeriod = eventParams.measurePeriod;
        isClosed = False;
        closedOracleTime = ("2018-06-30T07:07:32Z" : timestamp);
        closedRate = 0n;
        closedDynamics = 0n;
        isBetsForWin = False;
        poolFor = 0tez;
        poolAgainst = 0tez;
        totalLiquidityShares = 0n;
        sharePrecision = 100_000_000n;

        (* TODO: control liquidityPrecision, liquidityPercent
            min|max from Manager *)
        liquidityPercent = eventParams.liquidityPercent;
        liquidityPrecision = 1_000_000n;
        measureStartFee = eventParams.measureStartFee;
        expirationFee = eventParams.expirationFee;
        (* TODO: control rewardCallFee from Manager *)
        rewardCallFee = 100_000mutez;

        (* TODO: control new event ratioPrecision from Manager *)
        ratioPrecision = 100_000_000n;
    ];

    s.events[s.lastEventId] := newEvent;
    s.lastEventId := s.lastEventId + 1n;

} with ((nil: list(operation)), s)
