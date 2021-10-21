type newLineParams is record [
    currencyPair : string;
    (* if currencyPair value is less than minValue this is insurance case *)
    minValue : nat;
    (* if currencyPair value is more than maxValue this is insurance case *)
    maxValue : nat;

    initFor : nat;
    initAgainst : nat;

    fee : nat;
    duration : nat;
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
    minimalRewardAmount : tez;
]

(* this can be made within finish entrypoint *)
type claimInsuranceCaseParams is record [
    lineId : nat;
]

type giveRewardParams is record [agreementId : nat];

type removeLiquidityParams is record [
    lineId : nat;
    shares : nat
];

type action is
| NewLine of newLineParams
| ProvideLiquidity of provideLiquidityParams
| RemoveLiquidity of removeLiquidityParams
| Insure of insureParams
| ClaimInsuranceCase of claimInsuranceCaseParams
| GiveReward of giveRewardParams

(* lines is like macro events where users can have different agreements *)
type lineType is record [
    poolFor : nat;
    poolAgainst : nat;
    totalShares : nat;

    (* line creation params *)
    currencyPair : string;
    minValue : nat;
    maxValue : nat;
    fee : nat;
    duration : nat;

    (* this flag is set to true when someone claims insurance case :: similar to isClosed *)
    isClaimed : bool;

    (* MAYBE: isStopped : bool *)
    (* this can be used for providers to exit event, maybe need providers to vote for this *)
]

type agreementType is record [
    lineId : nat;
    beneficiary : address;

    (* pool where funds placed for *)
    pool : insureType;
    endTime : timestamp;
    rewardAmount : tez;
]

type liquidityType is record [
    deposited : tez;
    providedFor : nat;
    providedAgainst : nat;
    shares : nat;
]

type liquidityLedger is big_map(address*nat, liquidityType)
type agreementsLedger is big_map(nat, agreementType)
type linesLedger is big_map(nat, lineType)

type storage is record [
    lines : linesLedger;
    agreements : agreementsLedger;
    depositedLiquidity : liquidityLedger;

    nextLineId : nat;
    nextAgreementId : nat;

    ratioPrecision : nat;
    feePrecision : nat;
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
function natToTez(const t : nat) : tez is t * 1mutez;


(* NOTE: copypasted from JUSTER:tools.ligo *)
function maxNat(const a : nat; const b : nat) : nat is
block {
    var maxValue : nat := a;
    if (a < b) then maxValue := b else skip;
} with maxValue


function checkNotClaimed(const line : lineType) : unit is
if line.isClaimed then
    failwith("Insurance Case is claimed")
else unit;


function calculateNewLiquidity(
    const line : lineType;
    const liquidityFor : nat;
    const liquidityAgainst : nat;
    const maxSlippage : nat;
    const precision : nat
) : liquidityType is
block {

    checkNotClaimed(line);

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

    if p.fee > s.feePrecision then failwith("Fee > 100%") else skip;

    (* NOTE: No measurement fee is required to provide to create newLine *)
    const line = record [
        poolFor = 0n;
        poolAgainst = 0n;
        totalShares = 0n;
        currencyPair = p.currencyPair;
        minValue = p.minValue;
        maxValue = p.maxValue;
        isClaimed = False;
        fee = p.fee;
        duration = p.duration;
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
    const p : insureParams;
    var s : storage) : return is
block {

    var line := getLine(s, p.lineId);
    checkNotClaimed(line);
    if Tezos.amount = 0tez then failwith("No xtz provided") else skip;

    const key = (Tezos.sender, p.lineId);

    (* poolTo is the pool where payment goes *)
    var poolTo := case p.pool of
    | For -> line.poolFor
    | Against -> line.poolAgainst
    end;

    (* poolFrom is the pool where possible reward coming *)
    var poolFrom := case p.pool of
    | For -> line.poolAgainst
    | Against -> line.poolFor
    end;

    const value = tezToNat(Tezos.amount);

    (* adding liquidity to payment pool *)
    poolTo := poolTo + value;

    const winDelta = value * poolFrom / poolTo;
    const winDeltaCut = winDelta * abs(s.feePrecision - line.fee) / s.feePrecision;

    (* removing liquidity from another pool to keep ratio balanced: *)
    (* NOTE: liquidity fee is included in the delta *)
    (* NOTE: this is impossible to have winDeltaCut > poolFrom [but I check] *)
    if winDeltaCut > poolFrom then failwith("Wrong winDeltaCut") else skip;
    poolFrom := abs(poolFrom - winDeltaCut);

    const rewardAmount = natToTez(value + winDeltaCut);
    if rewardAmount < p.minimalRewardAmount
    then failwith("Wrong minimalRewardAmount")
    else skip;

    (* Adding agreement to ledger: *)
    s.agreements[s.nextAgreementId] := record [
        beneficiary = Tezos.sender;
        lineId = p.lineId;
        pool = p.pool;
        endTime = Tezos.now + int(line.duration);
        rewardAmount = rewardAmount
    ];

    line.poolFor := case p.pool of
    | For -> poolTo
    | Against -> poolFrom
    end;

    line.poolAgainst := case p.pool of
    | For -> poolFrom
    | Against -> poolTo
    end;

    s.lines[p.lineId] := line;

} with ((nil: list(operation)), s)


function removeLiquidity(
    const p : removeLiquidityParams;
    const s : storage) : return is
block {
    skip;
} with ((nil: list(operation)), s)


function giveReward(
    const p : giveRewardParams;
    const s : storage) : return is
block {
    skip;
} with ((nil: list(operation)), s)


function claimInsuranceCase(
    const p : claimInsuranceCaseParams;
    const s : storage) : return is
block {
    skip;
} with ((nil: list(operation)), s)


function main (const params : action; var s : storage) : return is
case params of
| NewLine(p) -> newLine(p, s)
| ProvideLiquidity(p) -> provideLiquidity(p, s)
| RemoveLiquidity(p) -> removeLiquidity(p, s)
| Insure(p) -> insure(p, s)
| ClaimInsuranceCase(p) -> claimInsuranceCase(p, s)
| GiveReward(p) -> giveReward(p, s)
end

