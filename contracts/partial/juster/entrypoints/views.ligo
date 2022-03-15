[@view] function getNextEventId (const _ : unit ; const s: storage) : nat is s.nextEventId

[@view] function getPosition (const key : ledgerKey ; const s : storage) : positionType is
block {
    if isParticipant(s, key)
        then skip;
        else failwith("Position is not found");
} with record [
    providedLiquidityAboveEq = getLedgerAmount(key, s.providedLiquidityAboveEq);
    providedLiquidityBelow = getLedgerAmount(key, s.providedLiquidityBelow);
    betsAboveEq = getLedgerAmount(key, s.betsAboveEq);
    betsBelow = getLedgerAmount(key, s.betsBelow);
    liquidityShares = getNatLedgerAmount(key, s.liquidityShares);
    depositedLiquidity = getLedgerAmount(key, s.depositedLiquidity);
    depositedBets = getLedgerAmount(key, s.depositedBets);
    isWithdrawn = Big_map.mem(key, s.isWithdrawn);
]

[@view] function getEvent (const eventId : nat ; const s : storage) : eventType is
block { const event = getEvent(s, eventId) } with event

[@view] function isParticipatedInEvent (
    const key : ledgerKey ; const s : storage) : bool is isParticipant(s, key)

[@view] function getConfig (const _ : unit ; const s : storage) is s.config

