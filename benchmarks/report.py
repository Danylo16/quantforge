"""Render medians from stored measurements. Run from the repository root."""

import json
from pathlib import Path
from statistics import median

import matplotlib.pyplot as plt

root = Path(__file__).parent
raw = json.loads((root / "results.json").read_text())["samples"]
sizes = sorted({x["n"] for x in raw})
fig, axes = plt.subplots(1, 2, figsize=(8, 3.5), layout="constrained")
plt.rcParams.update({"svg.fonttype": "none", "svg.hashsalt": "quantforge"})
lines = [
    "| Bars | Engine | Median s | Bars/s | Peak MiB | Scaling efficiency vs 10k | Event / array time |",
    "|---:|---|---:|---:|---:|---:|---:|",
]
for engine in ["event", "array"]:
    times = []
    memory = []
    for n in sizes:
        group = [r for r in raw if r["n"] == n and r["engine"] == engine]
        sec = median(r["seconds"] for r in group)
        times.append(sec)
        memory.append(median(r["peak_process_kib"] for r in group) / 1024)
        event = median(
            r["seconds"] for r in raw if r["n"] == n and r["engine"] == "event"
        )
        lines.append(
            f"| {n:,} | {engine} | {sec:.4f} | {n / sec:,.0f} | {memory[-1]:.1f} | {(n / sizes[0]) * times[0] / sec:.2f} | {event / sec:.2f} |"
        )
    axes[0].loglog(sizes, times, "o-", label=engine)
    axes[1].semilogx(sizes, memory, "o-", label=engine)
for ax, label in zip(
    axes, ["Median runtime (s)", "Peak process RSS (MiB)"], strict=True
):
    ax.set(xlabel="Bars", ylabel=label)
    ax.legend(frameon=False)
fig.savefig(root / "performance.svg", metadata={"Date": None})
(root / "table.md").write_text("\n".join(lines) + "\n")
