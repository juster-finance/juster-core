from unittest import TestCase
from os.path import join, dirname
from pytezos import ContractInterface, pytezos, MichelsonRuntimeError
from pytezos.michelson.types.core import Unit


TOKEN_FN = '../build/tz/token.tz'


class TokenTest(TestCase):


    def generate_token_storage(self, balances, operators=None):
        """ Creates token storage initialization using giving balances """

        token_id = 0
        operators = operators or {}

        return {
            'balances': {
                (user, token_id): value for user, value in balances.items()
            },
            'operators': operators,
            'token_metadata': {}
        }


    def generate_token_transfer_params(self, from_, to_, token_id, amount):
        """ Generates token transfer params with one transaction """

        return [{
            'from_': from_,
            'txs': [{
                'to_': to_,
                'token_id': token_id,
                'amount': amount
            }]
        }]


    def setUp(self):
        self.token = ContractInterface.from_file(
            join(dirname(__file__), TOKEN_FN))
        self.a = 'tz1iQE8ijR5xVPffBUPFubwB9XQJuyD9qsoJ'
        self.b = 'tz1MdaJfWzP5pPx3gwPxfdLZTHW6js9havos'


    def test_should_be_possible_to_transfer_token_if_have(self):

        storage = self.generate_token_storage({self.a: 100})
        transfer_params = self.generate_token_transfer_params(
            from_=self.a,
            to_=self.b,
            token_id=0,
            amount=10
        )

        result = self.token.transfer(transfer_params).interpret(
            sender=self.a,
            storage=storage
        )

        target = self.generate_token_storage({self.a: 90, self.b: 10})
        self.assertDictEqual(result.storage, target)


    # TODO: test should transfer params succeeded for two different to_
    # TODO: test should transfer params succeeded for two similar to_
    # TODO: test should transfer params order matters (how?)
    # TODO: test should transfer params succeeded for two different from_
    # TODO: test should transfer params succeeded for two different token_id


    def test_should_return_callback_when_called_balance_of(self):
        storage = self.generate_token_storage({self.a: 100})

        # TODO: self.generate_request ?
        request = {
            'owner': self.a,
            'token_id': 0
        }

        balance_of_params = {
            'requests': [request],
            'callback': f'KT1SUP27JhX24Kvr11oUdWswk7FnCW78ZyUn%someCallback'
        }

        result = self.token.balance_of(balance_of_params).interpret(
            sender=self.a,
            storage=storage
        )

        target = [{
            'request': request,
            'balance': 100
        }]

        self.assertEqual(len(result.operations), 1)
        operation = result.operations[0]
        # TODO: convert operation from micheline and check that it is the same as target:
        # self.assertDictEqual(operation['parameters'], target)

    # TODO: what should happen if no token for user? return 0 (check tzip)
    # TODO: test multiple requests in one transaction
    # TODO: test order matters


    def test_should_add_operator(self):
        # TODO: self.generate_operator? self.generate_operators?
        operators = {(self.a, self.b, 0): Unit}
        storage = self.generate_token_storage({self.a: 100})

        update_operators_params = [{
            'add_operator': {
                'owner': self.a,
                'operator': self.b,
                'token_id': 0
            }
        }]

        result = self.token.update_operators(update_operators_params).interpret(
            sender=self.a,
            storage=storage
        )

        target = self.generate_token_storage({self.a: 100}, operators)
        self.assertEqual(result.storage, target)


    def test_should_remove_operator(self):
        # TODO: self.generate_operator? self.generate_operators?
        operators = {(self.a, self.b, 0): Unit}
        storage = self.generate_token_storage({self.a: 100}, operators)

        update_operators_params = [{
            'remove_operator': {
                'owner': self.a,
                'operator': self.b,
                'token_id': 0
            }
        }]

        result = self.token.update_operators(update_operators_params).interpret(
            sender=self.a,
            storage=storage
        )

        # when key removed from big_map, pytezos show it with None value
        removed_operators = {(self.a, self.b, 0): None}
        target = self.generate_token_storage({self.a: 100}, removed_operators)

        self.assertEqual(result.storage, target)

