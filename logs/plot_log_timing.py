#!/bin/env python3

import sys
import re
import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.collections import PolyCollection

from datetime import datetime, timedelta

import matplotlib.ticker as ticker


# https://stackoverflow.com/a/62834880
class PrecisionDateFormatter(ticker.Formatter):
    """
    Extend the `matplotlib.ticker.Formatter` class to allow for millisecond
    precision when formatting a tick (in days since the epoch) with a
    `~datetime.datetime.strftime` format string.

    """

    def __init__(self, fmt, precision=3, tz=None):
        """
        Parameters
        ----------
        fmt : str
            `~datetime.datetime.strftime` format string.
        """
        from matplotlib.dates import num2date
        import matplotlib
        import dateutil.tz
        if tz is None:
            s = matplotlib.rcParams['timezone']
            if s == 'UTC':
                tz = dt.timezone.utc
            tz = dateutil.tz.gettz(s)
        self.num2date = num2date
        self.fmt = fmt
        self.tz = tz
        self.precision = precision

    def __call__(self, x, pos=0):
        if x == 0:
            raise ValueError("DateFormatter found a value of x=0, which is "
                             "an illegal date; this usually occurs because "
                             "you have not informed the axis that it is "
                             "plotting dates, e.g., with ax.xaxis_date()")

        dt = self.num2date(x, self.tz)
        ms = dt.strftime("%f")[:self.precision]

        return dt.strftime(self.fmt).format(ms=ms)

    def set_tzinfo(self, tz):
        self.tz = tz




timestamp_format = "%Y-%m-%d %H:%M:%S,%f"

t0 = None


ticker.Formatter
if len(sys.argv) < 3:
    raise RuntimeError('Usage: python3 plot_log_timing.py [MAPE log file] [output plot.png]')

infile = sys.argv[1]
outfile = sys.argv[2]

events = []
observed_nodes = set()

with open(infile, 'r') as f:
    for line in f.readlines():

        parts = line.split(' - ', 3)
        timestamp = datetime.strptime(parts[0], timestamp_format)
        node = parts[1]
        level = parts[2]
        message = parts[3]

        match (node, message):
            case ('Monitor', msg) if msg.startswith('Received MQTT message: {"angle_min":'):
                events.append((timestamp, node, ''))
            case (_, msg) if re.match(r'.*{"Str": "start_[maple]"}', msg):
                events.append((timestamp, node, 'start'))
            case (_, msg) if re.match(r'.*{"Str": "end_[maple](ok|nom)?"}', msg):
                events.append((timestamp, node, 'end'))
            case _:
                # print('No match for message:')
                # print(message)
                continue

        observed_nodes.add(node)

def sort_maple(x):
    first_letter = x[0]
    return "MAPLE".find(first_letter)

observed_nodes = list(observed_nodes)
observed_nodes.sort(key=sort_maple, reverse=True)

open_bars = {}

data = []
unit_events = []

t0 = events[0][0]

for ts,n,typ in events:
    if typ == "":
        unit_events.append((ts, "Scan"))
    elif typ == "start":
        if not n in open_bars:
            open_bars[n] = []
        open_bars[n].append(ts)
    elif typ == "end":
        if not n in open_bars:
            start = t0
        elif len(open_bars[n]) == 0:
            unit_events.append((ts, f"{n} end"))
            continue
        else:
            start = open_bars[n].pop(0)
        ts_actual = ts
        if start-ts < timedelta(milliseconds=5): 
            ts += timedelta(milliseconds=5)
        ev = (start, ts, n, ts_actual)
        data.append(ev)
        # print(ev)

# Based on https://stackoverflow.com/a/51506028

categories = {
    node: idx
    for idx, node in enumerate(observed_nodes)
}

verts = []
labels = []
for d in data:
    cat = categories[d[2]]
    v =  [(mdates.date2num(d[0]), cat-.4),
          (mdates.date2num(d[0]), cat+.4),
          (mdates.date2num(d[1]), cat+.4),
          (mdates.date2num(d[1]), cat-.4),
          (mdates.date2num(d[0]), cat-.4)]
    verts.append(v)
    delta = int((d[3]-d[0]).total_seconds()*1000)
    text_pos = (mdates.date2num(d[1]) + mdates.date2num(d[0]))/2
    labels.append((text_pos, cat, str(delta) if delta > 0 else "<1"))

bars = PolyCollection(verts, zorder=3)

fig_len = (events[-1][0]-events[0][0]).total_seconds()*5

fig, ax = plt.subplots(figsize=[fig_len,5], dpi=200)
for label in labels:
    ax.text(*label, zorder=5, color='black', backgroundcolor='white', fontsize=10, va='center', ha='center')
ax.vlines([x[0] for x in unit_events], -.5, 1.5, colors='black')
ax.grid(zorder=0)
ax.add_collection(bars)
ax.autoscale()
loc = mdates.MicrosecondLocator(100_000)
ax.xaxis.set_major_locator(loc)
ax.xaxis.set_major_formatter(PrecisionDateFormatter("%S.{ms}"))
# ax.xaxis.set_major_formatter(mdates.AutoDateFormatter(loc))

for label in ax.get_xticklabels(which='major'):
    label.set(rotation=30)

ticks = list(range(len(observed_nodes)))
tick_labels = observed_nodes
print(ticks, tick_labels)

ax.set_yticks(ticks)
ax.set_yticklabels(tick_labels)
plt.savefig(outfile)
