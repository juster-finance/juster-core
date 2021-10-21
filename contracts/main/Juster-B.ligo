type newLineParams is record [
    currencyPair : string;
    (* if currencyPair value is less than minValue this is insurance case *)
    minValue : nat;
    (* if currencyPair value is more than maxValue this is insurance case *)
    maxValue : nat;
    (* TODO: maybe there should be provided initial ratio *)
    (* TODO: maybe there should be provided initial liquidity *)
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
    amountFor : nat;
    amountAgainst : nat;
    shares : nat;
]

type storage is record [
    lines : big_map(nat, lineType);
    agreements : big_map(nat, agreementType);
    depositedLiquidity : big_map(nat, liquidityType);

    (* Basic timeslot in seconds, can be moved to newLine *)
    standardTimeslot : nat;

    nextLineId : nat;
    nextAgreementId : nat;
]

type return is list(operation) * storage

function newLine(const params : newLineParams; const s : storage) : return is ((nil: list(operation)), s)
function provideLiquidity(const params : provideLiquidityParams; const s : storage) : return is ((nil: list(operation)), s)
function insure(const params : insureParams; const s : storage) : return is ((nil: list(operation)), s)
function claimInsuranceCase(const params : claimInsuranceCaseParams; const s : storage) : return is ((nil: list(operation)), s)
function withdraw(const params : withdrawParams; const s : storage) : return is ((nil: list(operation)), s)

function main (const params : action; var s : storage) : return is
case params of
| NewLine(p) -> newLine(p, s)
| ProvideLiquidity(p) -> provideLiquidity(p, s)
| Insure(p) -> insure(p, s)
| ClaimInsuranceCase(p) -> claimInsuranceCase(p, s)
| Withdraw(p) -> withdraw(p, s)
end

