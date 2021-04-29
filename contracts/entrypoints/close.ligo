function close(var eventId : eventIdType; var s : storage) : (list(operation) * storage) is
block {
    (* When calling close event, s.closeCallEventId should be equal to None, otherwise
        it looks like another callback is runned but no answer is received yet (is it
        even possible, btw?) *)
    case s.closeCallEventId of
    | Some(closeCallEventId) -> failwith("Another call to oracle in process (should not be here)")
    | None -> skip
    end;

    const operations = makeCallToOracle(
        eventId, s, (Tezos.self("%closeCallback") : callbackEntrypoint));
    s.closeCallEventId := eventId;

} with (operations, s)
