#include "../partial/juster/juster_types.ligo"

type oracleAction is
| Get of oracleParam
| Update of nat

type oracleStorage is nat


function get(const param : oracleParam; const store : oracleStorage)
    : (list(operation) * oracleStorage) is
block {
    const requestedPair = param.0;
    const callback = param.1;

    const returnedValue : callbackReturnedValue = record [
        currencyPair = requestedPair;
        lastUpdate = Tezos.now;
        rate = store
    ];

    const operation = Tezos.transaction(
        returnedValue,
        0tez,
        callback);

} with (list[operation], store)


function update(const newValue : nat; const _store : oracleStorage)
    : (list(operation) * oracleStorage) is ((nil: list(operation)), newValue)


function main (const params : oracleAction; var s : oracleStorage)
    : (list(operation) * oracleStorage) is
case params of
| Get(p) -> get(p, s)
| Update(p) -> update(p, s)
end

[@view] function getPrice(const _pair : string; var s : oracleStorage) : timestamp*nat is (Tezos.now, s)

