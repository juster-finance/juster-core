(* TODO: move all errors here *)
module PoolErrors is {
    const wrongState : string = "Wrong state";
    const notEntryOwner : string = "Not entry position owner";
    const entryNotFound : string = "Entry is not found";
    const positionNotFound : string = "Position is not found";
    const eventNotFound : string = "Event is not found";
    const earlyApprove : string = "Cannot approve liquidity before acceptAfter";
    const noActiveEvents : string = "Need to have at least one line";
    const notPositionOwner : string = "Not position owner";
    const noLiquidity : string = "Not enough liquidity to run event";
    const noFreeEventSlots : string = "Max active events limit reached";
    const lineNotFound : string = "Line is not found";
    const lineIsPaused : string = "Line is paused";
    const emptyLine : string = "Line should have at least one event";
    const depositIsPaused : string = "Deposit is paused";
    const justerNewEventNotFound : string = "Juster.newEvent is not found";
    const justerGetNextEventIdNotFound : string = "Juster.getNextEventId view is not found";
    const justerProvideLiquidityNotFound : string = "Juster.provideLiquidity is not found";
    const activeNotFound : string = "Active event is not found";
    const notExpectedAddress : string = "Address is not expected";
    const eventIdTaken : string = "Event id is already taken";
}
