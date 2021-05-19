function closeCallback(
    var p : callbackReturnedValueMichelson;
    var s : storage) : (list(operation) * storage) is
block {

    const eventId : nat = case s.closeCallId of
    | Some(closeCallId) -> closeCallId
    | None -> (failwith("closeCallId is empty") : nat)
    end;

    (* TODO: Check that current time is not far away from measurementStartTime
        + timedelta, if it is, run Force Majeure. Give Manager ability to
        control this timedelta *)

    const param : callbackReturnedValue = Layout.convert_from_right_comb(p);

    const event : eventType = getEvent(s, eventId);

    (* Check that callback runs from right address
        and with right currency pair: *)
    if Tezos.sender =/= event.oracleAddress
    then failwith("Unknown sender") else skip;
    if param.currencyPair =/= event.currencyPair
    then failwith("Unexpected currency pair") else skip;

    if not event.isMeasurementStarted then
        failwith("Can't close contract before measurement period started")
    else skip;

    const endTime : timestamp =
        event.measureOracleStartTime + int(event.measurePeriod);
    if param.lastUpdate < endTime then
        failwith("Can't close until lastUpdate reached measureStartTime + measurePeriod")
    else skip;
    (* TODO: what should be done if time is very late?
        (i.e. cancel event and allow withdrawals?) *)
    if event.isClosed then failwith("Contract already closed. Can't close contract twice")
    else skip;

    (* Closing contract: *)
    event.closedOracleTime := param.lastUpdate;
    event.closedRate := param.rate;
    event.closedDynamics := param.rate * s.targetDynamicsPrecision / event.startRate;
    event.isClosed := True;
    event.isBetsForWin := event.closedDynamics > event.targetDynamics;

    (* TODO: what should be done if all bets were For and all of them are loose?
        All raised funds will be freezed. Should they all be winners anyway? *)

    (* Paying expirationFee for this method initiator: *)
    const receiver : contract(unit) = getReceiver(Tezos.source);
    const expirationFeeOperation : operation =
        Tezos.transaction(unit, event.expirationFee, receiver);

    s.events[eventId] := event;

    (* Cleaning up event ID: *)
    s.closeCallId := (None : eventIdType);

    (* TODO: this close/measurement callbacks have a lot similarities, maybe
        there are some code that can be moved in separate function *)


} with (list[expirationFeeOperation], s)
