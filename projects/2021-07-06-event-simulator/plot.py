import pandas as pd
import numpy as np
from matplotlib import pyplot as plt


def make_histogram(series, bins=30, range=None):
    if range is None:
        range = (series.min(), series.max())
    bins = np.histogram(series, bins=bins, range=range, density=True)
    return pd.Series(bins[0], index=bins[1][:-1])


def plot_hist(series, ax):
    ax.axvline(x=1, color='#666666', linestyle='--', linewidth=1)
    ax = make_histogram(series, range=(0.85, 1.15)).plot(ax=ax)
    return ax


def plot_dynamics_hists(dynamics):
    cols = len(dynamics)
    x_size = 5*cols
    fig, axes = plt.subplots(1, cols, figsize=(x_size, 3), sharex=True, sharey=True)

    axes = [
        plot_hist(dynamics[duration], ax=axes[num]).set_title(f'{duration} sec event dynamics')
        for num, duration in enumerate(dynamics)
    ]

    return axes
