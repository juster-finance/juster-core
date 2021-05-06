function newEvent(var eventParams : newEventParams; var s : storage) : (list(operation) * storage) is
block {
    (* TODO: Checking that betsCloseTime of this event is in the future
        (maybe check that there are some minimal time to make bets, that can be controlled by manager) *)
    (* TODO: Checking that measurePeriod is more than some minimal amount and maybe less than amount *)
    (* TODO: Check that liquidityPercent is less than 1_000_000 *)
    (* TODO: Check that measureStartFee and expirationFee is equal to Tezos.amount *)

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

        (* TODO: control measurePeriod, time to betsCloseTime min|max from Manager *)
        measurePeriod = eventParams.measurePeriod;
        isClosed = False;
        closedOracleTime = ("2018-06-30T07:07:32Z" : timestamp);
        closedRate = 0n;
        closedDynamics = 0n;
        isBetsForWin = False;
        oracleAddress = eventParams.oracleAddress;
        betsForLiquidityPoolSum = 0tez;
        betsAgainstLiquidityPoolSum = 0tez;
        firstProviderForSharesSum = 0tez;
        firstProviderAgainstSharesSum = 0tez;
        totalLiquidityForSharesSum = 0tez;
        totalLiquidityAgainstSharesSum = 0tez;
        totalLiquidityProvided = 0tez;

        (* TODO: control liquidityPrecision, liquidityPercent min|max from Manager *)
        liquidityPercent = eventParams.liquidityPercent;
        liquidityPrecision = 1_000_000n;
        measureStartFee = eventParams.measureStartFee;
        expirationFee = eventParams.expirationFee;
        (* TODO: control rewardCallFee from Manager *)
        rewardCallFee = 100_000mutez;

        (* TODO: control new event ratioPrecision from Manager *)
        ratioPrecision = 100_000_000n;
        winForProfitLossPerShare = 0;
        winAgainstProfitLossPerShare = 0;
        sharePrecision = 100_000_000n;
    ];

    s.events[s.lastEventId] := newEvent;

    (* NOTE: This is strange construction, but I do not understand how to
        assign value to option(nat) variable, maybe it should be changed *)
    case s.lastEventId of
    | Some(eventId) -> s.lastEventId := Some(eventId + 1n)
    | None -> failwith("s.lastEventId is None, should not be here")
    end;
} with ((nil: list(operation)), s)
