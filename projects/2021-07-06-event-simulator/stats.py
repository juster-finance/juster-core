import pandas as pd


def agregate_event_state(event):
    diffs = pd.Series(event['diffs'], dtype=float)

    # it is possible that there are no providers in diffs, if there are was no bets in event:
    diff_primary_provider = diffs.get('primary_provider', 0)
    diff_following_provider = diffs.get('following_provider', 0)
    user_diffs = diffs[ diffs.index.str.contains('user') ]

    shares = event['shares']

    stats = {
        'diff_primary_provider': diff_primary_provider,
        'diff_following_provider': diff_following_provider,
        'diff_user_mean': user_diffs.mean(),
        'diff_user_median': user_diffs.median(),
        'diff_user_q0_01': user_diffs.quantile(0.01),
        'diff_user_q0_99': user_diffs.quantile(0.99),
        'following_provider_to_primary_shares': shares['following_provider'] / shares['primary_provider']
    }

    return stats

