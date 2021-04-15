type increaseCounterParams is record [
    counterId : nat;
    amount : nat;
]

type counterKeyType is (address * nat);

type storage is record [
    values : big_map(counterKeyType, nat);
]

type action is
| IncreaseCounter of increaseCounterParams
| Default of unit


function increaseCounter(var p : increaseCounterParams; var s : storage) : storage is
block {
    var counterValue : nat := 0n;
    const counterKey : counterKeyType = (Tezos.sender, p.counterId);

    case Big_map.find_opt(counterKey, s.values) of
    | Some(value) -> counterValue := value
    | None -> counterValue := 0n
    end;

    s.values[counterKey] := counterValue + p.amount;
} with s


function main (var params : action; var s : storage) : (list(operation) * storage) is
case params of
| IncreaseCounter(p) -> ((nil: list(operation)), increaseCounter(p, s))
| Default -> ((nil: list(operation)), s)
end
