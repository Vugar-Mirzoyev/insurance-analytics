"""Static charts for the README (docs/images). The interactive report is Power BI."""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mtick  # noqa: E402
import pandas as pd  # noqa: E402

OUT = "docs/images"
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE = "#2a78d6", "#eb6834"


def _style(ax, title, subtitle=None):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=9, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title(title, loc="left", color=INK, fontsize=12, fontweight="bold", pad=18)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, color=INK_2, fontsize=9)


def loss_ratio_chart(portfolio_monthly):
    """Loss ratio by start month, written vs earned basis, 2017 onwards."""
    df = portfolio_monthly[portfolio_monthly["month"] >= "2017-01"].copy()
    df["date"] = pd.to_datetime(df["month"])
    fig, ax = plt.subplots(figsize=(9, 4.2), facecolor=SURFACE)
    for col, color, label, nudge in (("loss_ratio_written", ORANGE, "Written basis", -5),
                                     ("loss_ratio_earned", BLUE, "Earned basis", 5)):
        ax.plot(df["date"], df[col], color=color, linewidth=2, label=label)
        last = df.iloc[-1]
        ax.annotate(f"{last[col]:.1%}", (last["date"], last[col]),
                    xytext=(6, nudge), textcoords="offset points", va="center",
                    fontsize=8.5, color=INK_2)
    ax.axvspan(pd.Timestamp("2018-01-01"), df["date"].max(), color=GRID, alpha=0.45, lw=0)
    ax.text(pd.Timestamp("2018-01-15"), 0.72, "Periods still running on 2018-12-31",
            fontsize=8.5, color=INK_2)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0, decimals=0))
    ax.set_ylim(0, 0.8)
    ax.legend(frameon=False, loc="lower left", fontsize=9, labelcolor=INK_2)
    _style(ax, "Unfinished policy years look claim-free",
           "Claims / premium by month the policy period started (Spanish motor portfolio)")
    fig.tight_layout()
    fig.savefig(f"{OUT}/loss_ratio_written_vs_earned.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def market_chart(flags, forecasts):
    """Monthly market premiums and claims with trend, flags and forecast."""
    fig, axes = plt.subplots(2, 1, figsize=(9, 6.6), sharex=True, facecolor=SURFACE)
    titles = {"premiums": "Premiums written", "claims_paid": "Claims paid"}
    for ax, metric in zip(axes, ("premiums", "claims_paid")):
        f = flags[flags["metric"] == metric].copy()
        f["date"] = pd.to_datetime(f["month_start"])
        ax.plot(f["date"], f["value"] / 1000, color=BLUE, linewidth=1.2, alpha=0.5,
                label="Month")
        ax.plot(f["date"], f["ma_12"] / 1000, color=BLUE, linewidth=2, label="12-month average")
        flagged = f[f["z_flag"] | f["iqr_flag"]]
        ax.scatter(flagged["date"], flagged["value"] / 1000, s=40, color=ORANGE,
                   edgecolor=SURFACE, linewidth=1.5, zorder=3, label="Flagged month")

        fc = forecasts[(forecasts["metric"] == metric) & forecasts["chosen"]]
        fc_dates = pd.to_datetime(fc["month_start"])
        last = f.dropna(subset=["value"]).iloc[-1]
        ax.plot([last["date"], *fc_dates], [last["value"] / 1000, *(fc["forecast"] / 1000)],
                color=INK_2, linewidth=2, linestyle=(0, (3, 2)), label="Forecast Oct-Dec 2026")
        _style(ax, titles[metric], "AZN million per month, Azerbaijan market (CBAR)")
        ax.legend(frameon=False, loc="upper left", fontsize=8.5, labelcolor=INK_2, ncol=4)
        ax.set_ylim(bottom=0)
    fig.tight_layout()
    fig.savefig(f"{OUT}/market_monthly.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def make_charts(tables, flags, forecasts):
    os.makedirs(OUT, exist_ok=True)
    loss_ratio_chart(tables["portfolio_monthly"])
    market_chart(flags, forecasts)
