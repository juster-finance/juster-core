function startMeasurementCallback(
    var p : callbackReturnedValueMichelson;
    var s : storage) : (list(operation) * storage) is
block {
    const param : callbackReturnedValue = Layout.convert_from_right_comb(p);

    const eventId : eventIdType = s.measurementStartCallId;

    (* TODO: Check that current time is not far away from betsCloseTime,
        if it is, run Force Majeure. Give Manager ability to control
        this timedelta *)
    case eventId of
    | Some(measurementStartCallId) -> skip
    | None -> failwith("measurementStartCallId is empty")
    end;

    const event : eventType = getEvent(s, eventId);

    (* Check that callback runs from right address and with right
        currency pair: *)
    if Tezos.sender =/= event.oracleAddress
    then failwith("Unknown sender") else skip;
    if param.currencyPair =/= event.currencyPair
    then failwith("Unexpected currency pair") else skip;
    if event.isMeasurementStarted
    then failwith("Measurement period already started") else skip;
    if event.betsCloseTime > param.lastUpdate
    then failwith("Can't start measurement untill oracle time > betsCloseTime")
    else skip;
    (* TODO: what should be done if time is very late?
        (i.e. cancel event and allow withdrawals?) *)

    (* Starting measurement: *)
    event.measureOracleStartTime := param.lastUpdate;
    event.startRate := param.rate;
    event.isMeasurementStarted := True;

    (* Paying measureStartFee for this method initiator: *)
    const receiver : contract(unit) = getReceiver(Tezos.source);
    const payoutOperation : operation =
        Tezos.transaction(unit, event.measureStartFee, receiver);

    s.events[eventId] := event;

    (* Cleaning up event ID: *)
    s.measurementStartCallId := (None : eventIdType);

    (* TODO: this close/measurement callbacks have a lot similarities, maybe
        there are some code that can be moved in separate function *)

} with (list[payoutOperation], s)
