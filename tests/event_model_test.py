from unittest import TestCase
from event_model import EventModel


# storage from three_participants_test at the moment after event is closed:
# (only required fields)
EXAMPLE_STORAGE = {
    'betsAboveEq': {
        ('tz1MdaJfWzP5pPx3gwPxfdLZTHW6js9havos', 0): 75_000
    },
    'betsBelow': {},
    'depositedBets': {
        ('tz1MdaJfWzP5pPx3gwPxfdLZTHW6js9havos', 0): 50_000
    },
    'events': {0: {
        'betsCloseTime': 86_400,
        'createdTime': 0,
        'liquidityPercent': 0,
        'measurePeriod': 43_200,
        'poolAboveEq': 220_000,
        'poolBelow': 55_000,
        'totalLiquidityShares': 220_000_000
    }},
    'liquidityPrecision': 1_000_000,
    'liquidityShares': {
        ('tz1RS9GoEXakf9iyBmSaheLMcakFRtzBXpWE', 0): 80_000_000,
        ('tz1iQE8ijR5xVPffBUPFubwB9XQJuyD9qsoJ', 0): 140_000_000
    },
    'providedLiquidityAboveEq': {
        ('tz1RS9GoEXakf9iyBmSaheLMcakFRtzBXpWE', 0): 80_000,
        ('tz1iQE8ijR5xVPffBUPFubwB9XQJuyD9qsoJ', 0): 90_000
    },
    'providedLiquidityBelow': {
        ('tz1RS9GoEXakf9iyBmSaheLMcakFRtzBXpWE', 0): 20_000,
        ('tz1iQE8ijR5xVPffBUPFubwB9XQJuyD9qsoJ', 0): 60_000
    },
}


# The same event in EventModel structure:
EXAMPLE_EVENT_ARGS = {
    'fee': 0,
    'winning_pool': 'aboveEq',
    'pool_a': 220_000,
    'pool_b': 55_000,
    'total_shares': 220_000_000,
    'shares': {
        'tz1RS9GoEXakf9iyBmSaheLMcakFRtzBXpWE': 80_000_000,
        'tz1iQE8ijR5xVPffBUPFubwB9XQJuyD9qsoJ': 140_000_000
    },
    'diffs': {
        'tz1RS9GoEXakf9iyBmSaheLMcakFRtzBXpWE': 0,
        'tz1iQE8ijR5xVPffBUPFubwB9XQJuyD9qsoJ': -25_000,
        'tz1MdaJfWzP5pPx3gwPxfdLZTHW6js9havos': 25_000
    }
}


class EventModelTest(TestCase):
    def test_bet_pool_a_win(self):
        event = EventModel(
            fee=0.03,
            winning_pool='aboveEq',
            pool_a=1_000_000,
            pool_b=1_000_000
        )
        event.bet('user', 1_000_000, 'aboveEq', 0)
        self.assertTrue(event.diffs['user'] == 500_000)
        self.assertTrue(event.pool_a == 2_000_000)
        self.assertTrue(event.pool_b == 500_000)

    def test_bet_pool_b_win(self):
        event = EventModel(
            fee=0,
            winning_pool='below',
            pool_a=4_000_000,
            pool_b=1_000_000
        )
        event.bet('user', 1_000_000, 'below', 1)
        self.assertTrue(event.diffs['user'] == 2_000_000)
        self.assertTrue(event.pool_a == 2_000_000)
        self.assertTrue(event.pool_b == 2_000_000)

    def test_bet_pool_b_lose(self):
        event = EventModel(
            fee=0,
            winning_pool='aboveEq',
            pool_a=2_000_000,
            pool_b=1_000_000
        )
        event.bet('user', 1_000_000, 'below', 1)
        self.assertTrue(event.diffs['user'] == -1_000_000)
        self.assertTrue(event.pool_a == 1_000_000)
        self.assertTrue(event.pool_b == 2_000_000)

    def test_provide_liquidity(self):
        event = EventModel(
            fee=0,
            winning_pool='aboveEq',
            pool_a=1_000_000,
            pool_b=1_000_000,
            total_shares=100
        )
        event.provide_liquidity('provider', 1_000_000)
        self.assertTrue(event.shares['provider'] == 100)
        self.assertTrue(event.total_shares == 200)
        self.assertTrue(event.pool_a == 2_000_000)
        self.assertTrue(event.pool_b == 2_000_000)

        event.bet('loser', 2_000_000, 'below', 1)
        self.assertTrue(event.pool_b == 4_000_000)
        self.assertTrue(event.pool_a == 1_000_000)
        self.assertTrue(event.diffs['loser'] == -2_000_000)
        self.assertTrue(event.diffs['provider'] == 1_000_000)

    def test_first_provide_liquidity(self):
        event = EventModel(
            fee=0,
            winning_pool='aboveEq',
            total_shares=100
        )
        event.provide_liquidity('provider', 4_000_000, 4, 1)
        self.assertTrue(event.pool_a == 4_000_000)
        self.assertTrue(event.pool_b == 1_000_000)
        event.bet('loser', 0, 'below', 1)
        self.assertTrue(event.diffs['loser'] == 0)
        self.assertTrue(event.diffs['provider'] == 0)

    def test_bet_with_fee(self):
        event = EventModel(
            fee=0.2,
            winning_pool='aboveEq',
            pool_a=1_000_000,
            pool_b=1_000_000
        )
        event.bet('user', 1_000_000, 'aboveEq', 0.5)
        self.assertTrue(event.diffs['user'] == 450_000)
        self.assertTrue(event.pool_a == 2_000_000)
        self.assertTrue(event.pool_b == 550_000)


    def test_from_storage_and_equal(self):
        created_event = EventModel.from_storage(
            storage=EXAMPLE_STORAGE,
            event_id=0,
            winning_pool='aboveEq'
        )

        target_event = EventModel(**EXAMPLE_EVENT_ARGS)
        self.assertEqual(created_event, target_event)


    def test_equal_not_equal(self):
        first_event = EventModel(**EXAMPLE_EVENT_ARGS)
        second_event = EventModel(**EXAMPLE_EVENT_ARGS)
        self.assertEqual(first_event, second_event)

        second_event.provide_liquidity(
            user='tz1RS9GoEXakf9iyBmSaheLMcakFRtzBXpWE',
            amount=100_000
        )

        self.assertNotEqual(first_event, second_event)


