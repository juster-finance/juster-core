import numpy as np
from numpy.random import exponential, normal, uniform
from random import choice


def clipped_normal(mean, std, n=None, margin=0.0001):
    """ clips normal distribution between (0, 1) with small margin from both sides.
        used to generate noise to the market ratio
    """

    return np.clip(normal(mean, std, n), margin, 1-margin)


def ape(forecast, actual):
    """ Absolute percent error """

    return abs((forecast - actual)/actual)


def generate_params(market_dynamics, target_dynamics):

    # a_expected is the chance expectations that pool_a wins
    # calculating market ratio for the given params:
    market_expected_a = (market_dynamics >= target_dynamics).mean()

    provider_expected_a_deviation = 0.1

    # calculate provider expected ratio adding normal error to the market value:
    provider_expected_a = clipped_normal(
        market_expected_a,
        provider_expected_a_deviation)

    # this params affect liquidity size / bet size:
    providers_exp_scale = 100_000_000
    providers_min = 10_000_000
    bet_value_exp_scale = 10_000_000

    # absolute percent error of provider are saved to be used in further analysis:
    provider_expected_a_ape = ape(provider_expected_a, market_expected_a)
    
    event_run_params = dict(
        # total betting length:
        ticks = 1000,

        # chance that one of the users will bet during the tick:
        bet_chance = uniform(0.001, 0.200),

        # amount of unique users in event:
        # NOTE: users count does not affect chances
        users_count = int(uniform(2, 100)),

        # Selecting actual dynamics as one of the market examples provided:
        actual_dynamics = choice(market_dynamics),

        target_dynamics = target_dynamics,

        # TODO: replace with uniform dist and then use bins?
        fee = choice([0, 0.001, 0.005, 0.01, 0.02, 0.03, 0.04, 0.05]),

        primary_provider_amount = providers_min + exponential(providers_exp_scale),
        primary_provider_expected_a = provider_expected_a,
        primary_provider_expected_a_ape = provider_expected_a_ape,
        following_provider_amount = providers_min + exponential(providers_exp_scale),

        # np.random.exponential param used to generate random value for bets
        bet_value_exp_scale = bet_value_exp_scale,

        # standard deviation param used to calculate each user marker expectation:
        bet_ratio_deviation = choice([0, 0.01, 0.05, 0.1, 0.2]),

        market_expected_a = market_expected_a,
    )

    return event_run_params

