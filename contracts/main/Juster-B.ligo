type newLineParams is record [
    currencyPair : string;
    (* if currencyPair value is less than minValue this is insurance case *)
    minValue : nat;
    (* if currencyPair value is more than maxValue this is insurance case *)
    maxValue : nat;

    initFor : nat;
    initAgainst : nat;
]

type provideLiquidityParams is record [
    lineId : nat;
    expectedFor : nat;
    expectedAgainst : nat;
    maxSlippage : nat;
]

type insureType is
| For of unit
| Against of unit

type insureParams is record [
    lineId : nat;
    pool : insureType;

    (* Amount of standard timeslots that purchased in insurance *)
    timeslots : nat;
    minimalWinAmount : tez;
]

(* this can be made within finish entrypoint *)
type claimInsuranceCaseParams is record [
    lineId : nat;
]

type withdrawParams is record [
    agreementId : nat;
]

type action is
| NewLine of newLineParams
| ProvideLiquidity of provideLiquidityParams
| Insure of insureParams
| ClaimInsuranceCase of claimInsuranceCaseParams
| Withdraw of withdrawParams

(* lines is like macro events where users can have different agreements *)
type lineType is record [
    poolFor : nat;
    poolAgainst : nat;
    totalShares : nat;

    (* line creation params *)
    currencyPair : string;
    minValue : nat;
    maxValue : nat;

    (* this flag is set to true when someone claims insurance case :: similar to isClosed *)
    isClaimed : bool;

    (* MAYBE: isStopped : bool *)
    (* this can be used for providers to exit event, maybe need providers to vote for this *)
]

type agreementType is record [
    lineId : nat;

    (* pool where funds placed for *)
    pool : insureType;
    endTime : timestamp;
    winAmount : tez;
]

type liquidityType is record [
    deposited : tez;
    providedFor : nat;
    providedAgainst : nat;
    shares : nat;
]

type liquidityLedger is big_map(address*nat, liquidityType)
type agreementsLedger is big_map(address*nat, agreementType)
type linesLedger is big_map(nat, lineType)

type storage is record [
    lines : linesLedger;
    agreements : agreementsLedger;
    depositedLiquidity : liquidityLedger;

    (* Basic timeslot in seconds, can be moved to newLine *)
    standardTimeslot : nat;

    nextLineId : nat;
    nextAgreementId : nat;

    ratioPrecision : nat;
]

type return is list(operation) * storage


(* NOTE: copypasted from JUSTER:providedLiquidity.ligo *)
function calculateSlippage(
    const ratio : nat;
    const expectedRatio : nat;
    const precision : nat) is
block {

    (* Slippage calculated in ratioPrecision values as multiplicative difference
        between bigger and smaller ratios: *)
    var slippage : nat := if expectedRatio > ratio
        then precision * expectedRatio / ratio;
        else precision * ratio / expectedRatio;

    (* At this point slippage is always >= store.ratioPrecision *)
    slippage := abs(slippage - precision);

} with slippage


(* NOTE: copypasted from JUSTER:tools.ligo *)
function tezToNat(const t : tez) : nat is t / 1mutez;


(* NOTE: copypasted from JUSTER:tools.ligo *)
function maxNat(const a : nat; const b : nat) : nat is
block {
    var maxValue : nat := a;
    if (a < b) then maxValue := b else skip;
} with maxValue


function calculateNewLiquidity(
    const line : lineType;
    const liquidityFor : nat;
    const liquidityAgainst : nat;
    const maxSlippage : nat;
    const precision : nat
) : liquidityType is
block {

    if line.isClaimed then
        failwith("Providing Liquidity after Insurance Case Claimed is not possible")
    else skip;

    (* Calculating expected ratio using provided ratios: *)
    const expectedRatio : nat = liquidityFor * precision / liquidityAgainst;
    const ratio : nat = line.poolFor * precision / line.poolAgainst;

    const slippage : nat = calculateSlippage(ratio, expectedRatio, precision);
    if (slippage > maxSlippage) then
        failwith("Expected ratio very differs from current pool ratio")
    else skip;

    const deposited = tezToNat(Tezos.amount);

    (* Distributing liquidity: *)
    const maxPool : nat = maxNat(line.poolFor, line.poolAgainst);
    const providedFor : nat = deposited * line.poolFor / maxPool;
    const providedAgainst : nat = deposited * line.poolAgainst / maxPool;

    (* Calculating shares: *)
    const shares : nat = deposited * line.totalShares / maxPool;
    if shares = 0n then failwith("Added liquidity is less than one share")
    else skip;

    if ((providedFor = 0n) or (providedAgainst = 0n)) then
        failwith("Expected ratio in pool should be more than zero")
    else skip;

    (* TODO: assert that max liquidity == Tezos.amount (?) *)
} with record [
    deposited = Tezos.amount;
    providedFor = providedFor;
    providedAgainst = providedAgainst;
    shares = shares;
];


function getLine(
    const s : storage;
    const lineId : nat
) : lineType is
case Big_map.find_opt(lineId, s.lines) of
| Some(line) -> line
| None -> (failwith("Line is not found") : lineType)
end;


function getDepositedLiquidity(
    const s : storage;
    const key : address*nat
) : liquidityType is
case Big_map.find_opt(key, s.depositedLiquidity) of
| Some(liquidity) -> liquidity
| None -> record [
    deposited = 0tez;
    providedFor = 0n;
    providedAgainst = 0n;
    shares = 0n;
]
end;


function addLiquidity(
    var s : storage;
    const lineId : nat;
    const new : liquidityType
) : storage is
block {

    var line := getLine(s, lineId);
    line.poolFor := line.poolFor + new.providedFor;
    line.poolAgainst := line.poolAgainst + new.providedAgainst;
    s.lines[lineId] := line;

    const key = (Tezos.sender, lineId);
    const current = getDepositedLiquidity(s, key);
    s.depositedLiquidity[key] := record [
        deposited = current.deposited + new.deposited;
        providedFor = current.providedFor + new.providedFor;
        providedAgainst = current.providedAgainst + new.providedAgainst;
        shares = current.shares + new.shares;
    ]

} with s


function provideLiquidity(
    const p : provideLiquidityParams;
    var s : storage) : return is
block {

    const newLiquidity = calculateNewLiquidity(
        getLine(s, p.lineId),
        p.expectedFor,
        p.expectedAgainst,
        p.maxSlippage,
        s.ratioPrecision
    );

    s := addLiquidity(s, p.lineId, newLiquidity);

} with ((nil: list(operation)), s)


function newLine(
    const p : newLineParams;
    var s : storage) : return is
block {

    (* NOTE: No measurement fee is required to provide to create newLine *)
    const line = record [
        poolFor = 0n;
        poolAgainst = 0n;
        totalShares = 0n;
        currencyPair = p.currencyPair;
        minValue = p.minValue;
        maxValue = p.maxValue;
        isClaimed = False;
    ];

    s.lines[s.nextLineId] := line;

    (* Decided this time provide first liquidity should be within event creation *)
    const newLiquidity = calculateNewLiquidity(
        line,
        p.initFor,
        p.initAgainst,
        s.ratioPrecision,
        s.ratioPrecision
    );

    s := addLiquidity(s, s.nextLineId, newLiquidity);
    s.nextLineId := s.nextLineId + 1n;

} with ((nil: list(operation)), s)

function insure(
    const params : insureParams;
    const s : storage) : return is
block {
    skip;
} with ((nil: list(operation)), s)

function claimInsuranceCase(
    const params : claimInsuranceCaseParams;
    const s : storage) : return is
block {
    skip;
} with ((nil: list(operation)), s)

function withdraw(
    const params : withdrawParams;
    const s : storage) : return is
block {
    skip;
} with ((nil: list(operation)), s)

function main (const params : action; var s : storage) : return is
case params of
| NewLine(p) -> newLine(p, s)
| ProvideLiquidity(p) -> provideLiquidity(p, s)
| Insure(p) -> insure(p, s)
| ClaimInsuranceCase(p) -> claimInsuranceCase(p, s)
| Withdraw(p) -> withdraw(p, s)
end

