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

type updateOperatorParams is updateAction
type updateOperatorsParams is list(updateOperatorParams)
type transferParams is unit
type balanceOfParams is unit


type action is
| Transfer of transferParams
| Balance_of of balanceOfParams
| Update_operators of updateOperatorsParams


type storage is unit


function transfer(const params : transferParams; var store : storage) : list(operation) * storage is
((nil : list(operation)), store)


function balanceOf(const params : balanceOfParams; var store : storage) : list(operation) * storage is
((nil : list(operation)), store)


function updateOperators(const params : updateOperatorsParams; var store : storage) : list(operation) * storage is
((nil : list(operation)), store)


function main(const params : action; const store : storage) : list(operation) * storage is
case params of
| Transfer(params) -> transfer(params, store)
| Balance_of(params) -> balanceOf(params, store)
| Update_operators(params) -> updateOperators(params, store)
end
