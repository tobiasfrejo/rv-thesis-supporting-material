import datetime as dt
import re
import sys

timestamp_format = "%Y-%m-%d %H:%M:%S,%f"

t0 = None

if len(sys.argv) < 4:
    raise RuntimeError(f'Usage: python3 {sys.argv[0]} [MAPE log file] [output lola file] [stream name to watch]')

infile = sys.argv[1]
outfile = sys.argv[2]
out_stream = sys.argv[3]

events = {}

with open(infile, 'r') as f:
    for line in f.readlines():

        parts = line.split(' - ', 3)
        timestamp = dt.datetime.strptime(parts[0], timestamp_format)
        node = parts[1]
        level = parts[2]
        message = parts[3]

        m = re.match(r'Published to MQTT topic (.+): {"Str": "(.+)"}', message)
        if m:
            stream = m.group(1)
            value = m.group(2)
            if stream not in events:
                events[stream] = []
            events[stream].append(value)

if not out_stream in events:
    raise RuntimeError(f'No events found on "{out_stream}"')

with open(outfile, 'w') as f:
    step = 0

    for value in events[out_stream]:
        f.write(f'{step}: {out_stream} = "{value}"\n')
        step += 1