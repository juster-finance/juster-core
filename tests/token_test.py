from unittest import TestCase
from os.path import join, dirname
from pytezos import ContractInterface, pytezos, MichelsonRuntimeError


TOKEN_FN = '../build/tz/token.tz'


class TokenTest(TestCase):


    def generate_token_storage(self, balances):
        """ Creates token storage initialization using giving balances """

        token_id = 0
        return {
            'balances': {
                (user, token_id): value for user, value in balances.items()
            },
            'operators': {}
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
        import pdb; pdb.set_trace()
        self.assertDictEqual(result.storage, target)
        self.assertEqual(len(result.operations), 1)


    # TODO: test should transfer params succeeded for two different to_
    # TODO: test should transfer params succeeded for two similar to_
    # TODO: test should transfer params order matters (how?)
    # TODO: test should transfer params succeeded for two different from_
    # TODO: test should transfer params succeeded for two different token_id
