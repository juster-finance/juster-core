type operatorParam is
    [@layout:comb]
    record [
        owner : address;
        operator : address;
        token_id : nat;
    ]

type updateAction is
| Add_operator of operatorParam
| Remove_operator of operatorParam

type updateOperatorsParams is list(updateAction)


type transactionType is
    [@layout:comb]
    record [
        to_ : address;
        token_id : nat;
        amount : nat;
]

type singleTransferParams is
    [@layout:comb]
    record [
        from_ : address;
        txs : list(transactionType)
    ]

type transferParams is list(singleTransferParams)


(* TODO: rename to: keyType? idType? keyParam? *)
type requestType is
    [@layout:comb]
    record [
        owner : address;
        token_id : nat;
]

type balanceRequest is
    [@layout:comb]
    record [
        request : requestType;
        balance : nat;
]

type balanceOfCallbackParams is list(balanceRequest)

type balanceOfParams is
    [@layout:comb]
    record [
        requests : list(requestType);
        callback : contract(balanceOfCallbackParams)
]


type action is
| Transfer of transferParams
| Balance_of of balanceOfParams
| Update_operators of updateOperatorsParams


type storage is record [
    balances : big_map(requestType, nat);
    operators : big_map(operatorParam, unit);
]


function getBalance(const store : storage; const key : requestType) : nat is
// TODO: should operators check here or not?
case Big_map.find_opt(key, store.balances) of
| Some(tokenBalance) -> tokenBalance
| None -> 0n
end;


function transfer(
    const params : transferParams;
    var store : storage) : list(operation) * storage is

block {
    // TODO: remove block for outer loop
    for singleTransfer in list params block {
        for tx in list singleTransfer.txs block {

            const keyTo : requestType = record[
                owner=tx.to_;
                token_id=tx.token_id
            ];

            const keyFrom : requestType = record[
                owner=singleTransfer.from_;
                token_id=tx.token_id
            ];

            // TODO: spec should have value in from_
            // TODO: spec should have value in from_ or should be operator in from_
            const balanceFrom = getBalance(store, keyFrom);

            store.balances[keyFrom] := abs(balanceFrom - tx.amount);
            store.balances[keyTo] := getBalance(store, keyTo) + tx.amount;
        }
    }
} with ((nil : list(operation)), store)


function balanceOf(
    const params : balanceOfParams;
    var store : storage) : list(operation) * storage is

block {
    var balances : list(balanceRequest) := nil;

    // TODO: remove block?
    for key in list params.requests block {
        const balanceData = record[
            request = key;
            balance = getBalance(store, key)
        ];
        balances := balanceData # balances;
    };

    const balanceOfOperation = Tezos.transaction(balances, 0mutez, params.callback);
} with (list[balanceOfOperation], store)


(*
function keyFromOperator(const operator : operatorParam) : requestType is
record[
    owner=operator.owner;
    token_id=operator.token_id
];
*)


function updateOperators(
    // TODO: consider rename to updateOparatorsActions
    const params : updateOperatorsParams;
    var store : storage) : list(operation) * storage is
block {

    for action in list params block {
        store.operators := case action of
        | Add_operator(param) ->
            Big_map.update(param, Some(Unit), store.operators)
        | Remove_operator(param) ->
            Big_map.update(param, (None : option(unit)), store.operators)
        end;
    }

} with ((nil : list(operation)), store)


function main(
    const params : action;
    const store : storage) : list(operation) * storage is

case params of
| Transfer(params) -> transfer(params, store)
| Balance_of(params) -> balanceOf(params, store)
| Update_operators(params) -> updateOperators(params, store)
end

