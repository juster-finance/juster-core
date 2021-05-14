function close(
    var eventId : nat;
    var s : storage) : (list(operation) * storage) is
block {
    (* When calling close event, s.closeCallId should be equal to None,
        otherwise it looks like another callback is runned but no answer
        is received yet (is it even possible, btw?) *)
    case s.closeCallId of
    | Some(closeCallId) ->
        failwith("Another call to oracle in process (should not be here)")
    | None -> skip
    end;

    const operations = makeCallToOracle(
        eventId, s, (Tezos.self("%closeCallback") : callbackEntrypoint));
    s.closeCallId := Some(eventId);

} with (operations, s)
