import pandas as pd


def calc_dynamics_by_freq(df, freq='H'):
    # The difference from real data would be that we would use normalized prices
    # instead of close prices:

    close_price = df.set_index('time').groupby(pd.Grouper(freq=freq)).close.last()
    dynamics = close_price.shift(freq=freq) / close_price
    return dynamics.dropna()


def calc_rate_by_freq_and_target(df, freq='H', target_dynamics=1.00):
    dynamics = calc_dynamics_by_freq(df, freq)
    return (dynamics > target_dynamics).mean()


def make_dynamic_curve(df, pair, freq, spread=0.05, num=51):

    min_target = 1 - spread
    max_target = 1 + spread

    dynamic_curve = pd.Series({
        target: calc_rate_by_freq_and_target(df, freq, target)
        for target in np.linspace(min_target, max_target, num=num)
    })

    return dynamic_curve
