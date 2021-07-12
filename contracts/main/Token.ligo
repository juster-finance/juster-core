type transferParams is unit
type balanceOfParams is unit
type updateOperatorsParams is unit


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
