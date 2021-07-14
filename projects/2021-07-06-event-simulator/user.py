""" Simple model that implement user behaviour """
import sys
sys.path.insert(0, '../../tests')
from event_model import EventModel


class User:
    def __init__(self, name, expected_a):
        self.name = name
        self.expected_a = expected_a

    def select_pool(self, event):
        return 'aboveEq' if self.expected_a > event.pool_a_expected() else 'below'


def test_user_model():
    # TODO: unittest?

    # user expects 50:50 that price go where it want to go
    gambler = User('gambler', 0.5)

    # but there are event where he can win x10 if price > target (low a expectance):
    bearish_event = EventModel(pool_a=1, pool_b=9)
    assert gambler.select_pool(bearish_event) == 'aboveEq'

    # the opposite event with high expectance that price will be > target:
    bullish_event = EventModel(pool_a=9, pool_b=1)
    assert gambler.select_pool(bullish_event) == 'below'

    # market is equally expecting price movement:
    neutral_event = EventModel(pool_a=1, pool_b=1)

    # but there are insider who knows that market will drop soon:
    insider = User('insider', 0.1)
    assert insider.select_pool(neutral_event) == 'below'

    # or there are insider that is waiting for market boom:
    insider = User('insider', 0.9)
    assert insider.select_pool(neutral_event) == 'aboveEq'


test_user_model()

