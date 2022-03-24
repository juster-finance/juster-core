(* this is very simple proto reward contract used to test views in Juster *)
(* TODO: possibility to add different programs with lambdas that get list of
    events and then return True/False if user satisfies conditions *)
(* TODO: possibility to accumulate events before calling check, so it would be
    possible to accumulate events over long period of times *)
(* TODO: ability to add different rewards and reward lambdas. This should be
    executed when program executed with True (user satisfies conditions) *)


#include "../partial/juster/juster_types.ligo"

type rewardProgramStorage is record [
    juster : address;
    result : bool;
]

(* list of event ids used to check that evidence is correct *)
type listOfIds is list(nat)

type action is
| ProvideEvidence of listOfIds
| AddTez of unit


(* simple case: one event with provided liquidity > 1xtz *)
function provideEvidence(
    const ids : listOfIds;
    var store : rewardProgramStorage
) : (list(operation)*rewardProgramStorage) is

block {
    const eventId = case List.head_opt(ids) of [
    | Some(id) -> id
    | None -> (failwith("No events provided") : nat)
    ];

    const key = (Tezos.sender, eventId);

    const positionOption : option(positionType) = Tezos.call_view
        ("getPosition", key, store.juster);
    const position = case positionOption of [
    | Some(id) -> id
    | None -> (failwith("Juster.getPosition view is not found") : positionType)
    ];

    if position.depositedLiquidity >= 1_000_000mutez
        then store.result := True
        else store.result := False

} with ((nil : list(operation)), store)


function main(const params : action; const s : rewardProgramStorage) : (list(operation)*rewardProgramStorage) is
case params of [
| ProvideEvidence(ids) -> provideEvidence(ids, s)
| AddTez -> ((nil : list(operation)), s)
];

