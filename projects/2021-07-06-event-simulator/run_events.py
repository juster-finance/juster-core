import sys
sys.path.insert(0, '../../tests')
from event_model import EventModel
from types import SimpleNamespace
from user import User
from params_generation import clipped_normal
from random import random, randint, choice
from numpy.random import exponential


def run_random_event(**run_event_params):

    # TODO: decide is this good way to work with params?
    p = SimpleNamespace(**run_event_params)

    # creating users, each have unique market expectation:
    users = [User(
        name=f'user_{num}',
        expected_a=clipped_normal(
            p.market_expected_a,
            p.bet_ratio_deviation)
    ) for num in range(p.users_count)]

    primary_provider = 'primary_provider'
    following_provider = 'following_provider'

    winning_pool = 'aboveEq' if p.actual_dynamics >= p.target_dynamics else 'below'
    event = EventModel(
        fee=p.fee,
        winning_pool=winning_pool
    )

    event.provide_liquidity(
        user=primary_provider,
        amount=p.primary_provider_amount,
        pool_a=p.primary_provider_expected_a,
        pool_b=(1 - p.primary_provider_expected_a)
    )

    following_provider_entry_tick = randint(0, p.ticks)

    for tick in range(p.ticks):
        if p.bet_chance > random():
            user = choice(users)
            event.bet(
                user=user.name,
                amount=exponential(p.bet_value_exp_scale),
                pool=user.select_pool(event),
                time=tick/p.ticks
            )

        if tick == following_provider_entry_tick:
            event.provide_liquidity(
                user=following_provider,
                amount=p.following_provider_amount
            )

    # TODO: do I need to analyze single users expectations and return them somehow?

    # TODO: do I need to calculate another meta params: bets count, mean bet value and others?
    # -- maybe improve EventModel to keep track this meta?

    # TODO: do I need to somehow agregate all users diffs and calculate stats?
    # -- looks like it is good to have some stat agregator after this event returned
    return event
