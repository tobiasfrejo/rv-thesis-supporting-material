import matplotlib.pyplot as plt
import re


#%% 
def read_lola_output(file, streams:list):
    parsed = dict()

    with open(file, 'r') as f:
        for line in f.readlines():
            pattern = r'([a-zA-Z][a-zA-Z0-9]*)\[(\d+)\] = (Bool\((false|true)\)|Str\("([^"]+)\"\)|Int\((\d+)\)|Float\((\d+\.\d+)\))\s+'
            m = re.match(pattern, line)
            if m:
                stream_name, stream_idx, whole_value, bool_value, string_value, int_value, float_value = m.groups()
                if stream_name in streams:
                    v = None
                    if whole_value.startswith('Bool'):
                        v = bool_value == 'true'
                    elif whole_value.startswith('Str'):
                        v = string_value
                    elif whole_value.startswith('Int'):
                        v = int(int_value)
                    elif whole_value.startswith('Float'):
                        v = float(float_value)
                    i = int(stream_idx)

                    if not i in parsed:
                        parsed[i] = dict()
                    parsed[i][stream_name] = v
    return parsed

def zero_index(d:dict):
    least_index = min(d.keys())
    d_new = dict()
    for k,v in d.items():
        d_new[k-least_index] = v
    return d_new

def split_dict(d:dict):
    values = dict()

    for n,dv in d.items():
        for k,v in dv.items():
            if not k in values:
                values[k] = []
            values[k].append((n,v))
    
    return values


def split_merged_stream(l: list[tuple]):
    unmerged = dict()
    for v in l:
        if not v[1] in unmerged:
            unmerged[v[1]] = []
        unmerged[v[1]].append(v[0])
    return unmerged


def plot_binary(steps, ax=plt, binary_range=(-1,1), **kwargs):
    xs = list(map(lambda v: v[0], steps))
    ys = list(map(lambda v: binary_range[1] if v[1] else binary_range[0], steps))

    ax.step(xs, ys, where='post', **kwargs)

def plot_stage(name, steps, ax=plt, color_map=None, **kwargs):
    xs = steps
    ys = [0] * len(steps)

    if color_map and name in color_map:
        ax.scatter(xs, ys, label=name, color=color_map[name], **kwargs)
    else:
        ax.scatter(xs, ys, label=name, **kwargs)

def plot_stages(stages, ax=plt, color_map=None, **kwargs):
    for k,v in stages.items():
        plot_stage(k, v, ax, color_map, **kwargs)




def create_maple_plot(streams, outfile, legend_ncol=5, title=None):
    stage_colours = {
        'm':'#cbd7ea',
        'a': '#b1d0ad',
        'anom': '#e02e44',
        'aok': '#b1d0ad',
        'p': '#f4a918',
        'l': '#3273d8',
        'e': '#a251cb'
    }

    fig = plt.figure(figsize=(9,2))
    ax = plt.subplot()
    if title:
        ax.set_title(title)

    ax.grid(axis='x')
    # plt.set_axisbelow(True)
    ax.set_axisbelow(True)
    ax.set_yticks([-1, 1])
    ax.set_yticklabels(['false', 'true'])
    ax.set_ylim(-1.2,1.2)
    ax.set_ylabel("MAPLE property\nevaluation")
    ax.set_xlabel("Time step")

    plot_stages(
        split_merged_stream(streams['stageout']), 
        ax=ax, marker='.', color_map=stage_colours, s=200, zorder=2)
    plot_binary(streams['maple'], ax=ax, zorder=1, color="#444488")

    # Shrink current axis's height by 10% on the bottom
    box = ax.get_position()
    ax.set_position([box.x0, box.y0 + box.height * 0.4,
                    box.width, box.height * 0.6])

    # Put a legend below current axis
    ax.legend(loc='upper left', bbox_to_anchor=(-.1, -.25),
            fancybox=True, shadow=True, ncol=legend_ncol)

    fig.savefig(outfile, bbox_inches='tight')

def maple_plot(folder, legend_ncol=5, title=None):
    INPUTFILE=folder+"/TWC-output-window.txt"
    OUTPUTFILE=folder+"/TWC-output-window.pdf"

    streams = split_dict(
    zero_index(
    read_lola_output(INPUTFILE,['stageout', 'maple'])
    ))

    create_maple_plot(streams, OUTPUTFILE, legend_ncol, title=title)

def tag_list(l, tag=None):
    return [
        (v, tag)
        for v in l
    ]

def insert_into_dict_list_and_sort(d:dict, key:str, new_values:list[tuple]):
    if key not in d:
        d[key] = list()
    d[key] += new_values
    d[key].sort(key=lambda x: x[0])

def create_open_bars(stages):
    stage_split = split_merged_stream(stages)

    print(stage_split)

    stages = set()
    end_stages = set()

    tagged_stages = []
    for k,v in stage_split.items():
        m = re.match(r"(start|end)_([a-zA-Z])([a-zA-Z]+)", k)
        if m:
            tagged_stages.append(m.groups())

    for k in stage_split.keys():
        k: str
        if k.startswith('start_'):
            stages.add(k.removeprefix('start_'))
        elif k.startswith('end_'):
            end_stages.add(k.removeprefix('end_'))

    merged_tagged_stages = {}
    for l, s, t in tagged_stages:
        untagged = f"{l}_{s}"
        for v in stage_split[untagged+t]:
            if untagged not in merged_tagged_stages:
                merged_tagged_stages[untagged] = list()
            merged_tagged_stages[untagged].append((v, t))
    
    for k, v in merged_tagged_stages.items():
        v.sort(key=lambda x: x[0])

        lifecycle = k.split('_')[0]
        stage = k.split('_')[1]

        v_steps = map(lambda x: x[0], v)
        v_tags = map(lambda x: x[1], v)

        if lifecycle == 'start':
            combined = zip(v_steps, stage_split['end_'+stage], v_tags)
            for start, end, tag in combined:
                end_stages.remove(stage)
                end_stages.add(stage+tag)

                if 'end_'+stage+tag not in stage_split:
                    stage_split['end_'+stage+tag] = list()
                stage_split['end_'+stage+tag].append(end)

        else:
            combined = zip(stage_split['start_'+stage], v_steps, v_tags)
            for start, end, tag in combined:
                try:
                    stages.remove(stage)
                    print(f'removed {stage} from start stages')
                except KeyError:
                    pass
                stages.add(stage+tag)

                if 'start_'+stage+tag not in stage_split:
                    stage_split['start_'+stage+tag] = list()
                stage_split['start_'+stage+tag].append(start)
                print('start_'+stage+tag, start, end, tag)

    assert stages == end_stages, f"{len(stages)=}, {len(end_stages)=}"

    broken_bars = {}

    for stage in stages:
        stage_starts = stage_split['start_' + stage]
        stage_ends = stage_split['end_' + stage]
        print(stage)
        print(stage_starts)
        print(stage_ends)

        assert len(stage_starts) == len(stage_ends), f"{stage}: {len(stage_starts)=}, {len(stage_ends)=}"

        broken_bars[stage] = list()

        for i in range(len(stage_starts)):
            step_start = stage_starts[i]
            step_end = stage_ends[i] 
            broken_bars[stage].append((step_start, step_end-step_start))

    return broken_bars




def sort_maple(x):
    return ['m', 'a', 'aok', 'anom', 'p', 'l', 'e'].index(x.lower())


def plot_atomic_bars(stages, ax=plt, **kwargs):
    bars = create_open_bars(stages)
    
    observed_nodes = bars.keys()
    observed_nodes = list(observed_nodes)
    observed_nodes.sort(key=sort_maple, reverse=True)
    
    stage_colours = {
        'm':'#cbd7ea',
        'a': '#b1d0ad',
        'anom': '#e02e44',
        'aok': '#b1d0ad',
        'p': '#f4a918',
        'l': '#3273d8',
        'e': '#a251cb'
    }

    y_ticks = []
    y_ticklabels = []

    for i,node in enumerate(observed_nodes):
        if node in stage_colours:
            ax.broken_barh(bars[node], (i-0.4, 0.8), color=stage_colours[node], **kwargs)
        else:
            ax.broken_barh(bars[node], (i-0.4, 0.8), **kwargs)
        y_ticks.append(i)
        y_ticklabels.append(node)
    
    return y_ticks, y_ticklabels

def atomic_plot(folder, legend_ncol=3, title=None):
    INPUTFILE=folder+"/TWC-output-window.txt"
    OUTPUTFILE=folder+"/TWC-output-window.pdf"

    streams = split_dict(
    zero_index(
    read_lola_output(INPUTFILE,['stageout', 'atomic'])
    ))


    fig = plt.figure(figsize=(8,2))
    ax = plt.subplot()
    if title:
        ax.set_title(title)
    
    fig.tight_layout()


    ax.grid(axis='x')
    ax.set_axisbelow(True)

    ax2 = ax.twinx()
    plot_binary(streams['atomic'], ax=ax2, zorder=1, color="#444488")

    ax.set_ylim(-1, 5)
    ax2.set_yticks([-1,1])
    ax2.set_yticklabels(['false','true'])

    bar_ticks, bar_ticklabels = plot_atomic_bars(streams['stageout'], ax, zorder=2)
    
    ax.set_yticks(bar_ticks)
    ax.set_yticklabels(bar_ticklabels)

    ax2.set_ylabel("Atomic property\nevaluation")
    ax.set_xlabel("Time step")

    fig.savefig(OUTPUTFILE, bbox_inches='tight')


def new_atomic_plot(folder, legend_ncol=3, title=None):
    INPUTFILE=folder+"/TWC-output-window.txt"
    OUTPUTFILE=folder+"/TWC-output-window.pdf"

    streams = split_dict(
    zero_index(
    read_lola_output(INPUTFILE,['s', 'atomic'])
    ))


    fig = plt.figure(figsize=(8,2))
    ax = plt.subplot()
    if title:
        ax.set_title(title)
    
    fig.tight_layout()


    ax.grid(axis='x')
    ax.set_axisbelow(True)

    ax2 = ax.twinx()
    plot_binary(streams['atomic'], ax=ax2, zorder=1, color="#444488")

    ax.set_ylim(-1, 6)
    ax2.set_yticks([-1,1])
    ax2.set_yticklabels(['false','true'])

    bar_ticks, bar_ticklabels = plot_atomic_bars(streams['s'], ax, zorder=2)
    
    ax.set_yticks(bar_ticks)
    ax.set_yticklabels(bar_ticklabels)

    ax2.set_ylabel("Atomic property\nevaluation")
    ax.set_xlabel("Time step")

    fig.savefig(OUTPUTFILE, bbox_inches='tight')

def plot_knowledge(folder, stream_name, title=None):
    INPUTFILE=folder+"/TWC-output-window.txt"
    outfile=folder+"/TWC-output-window.pdf"

    streams = split_dict(
    zero_index(
    read_lola_output(INPUTFILE,[stream_name, 'missed'])
    ))

    stage_colours = {
        'read': '#6688ee',
        'write': '#ee6688'
    }

    fig = plt.figure(figsize=(9,2))
    ax = plt.subplot()
    if title:
        ax.set_title(title)
    ax.grid(axis='x')
    # plt.set_axisbelow(True)
    ax.set_axisbelow(True)
    ax.set_yticks([-1, 1])
    ax.set_yticklabels(['false', 'true'])
    ax.set_ylim(-1.2,1.2)
    ax.set_ylabel(f"Knowledge\nmissed")
    ax.set_xlabel("Time step")

    plot_stages(
        split_merged_stream(streams[stream_name]), 
        ax=ax, marker='.', color_map=stage_colours, s=200, zorder=2)
    plot_binary(streams['missed'], ax=ax, zorder=1, color="#444488")

    # Shrink current axis's height by 10% on the bottom
    box = ax.get_position()
    ax.set_position([box.x0, box.y0 + box.height * 0.4,
                    box.width, box.height * 0.6])

    # Put a legend below current axis
    ax.legend(loc='upper left', bbox_to_anchor=(-.1, -.25),
            fancybox=True, shadow=True, ncol=2)

    fig.savefig(outfile, bbox_inches='tight')

def plot_labels(stream, ax=plt, y_offset=0, conditinal_format=None, **kwargs):
    for x, l in stream:
        extra_format = dict()
        if conditinal_format:
            extra_format = conditinal_format((x, l))
        ax.text(x, y_offset, l, **kwargs, **extra_format)

def plot_sol(folder,input_file=None, output_file=None, title=None):
    INPUTFILE=folder + '/' + (input_file or "TWC-output-window.txt")
    outfile=folder + '/' + (output_file or "TWC-output-window.pdf")

    streams = split_dict(
    zero_index(
    read_lola_output(INPUTFILE,['timeout', 'acc', 'clockEcho'])
    ))

    colours = {
        'scan': '#ee6688',
        'timer': '#6688ee'
    }

    fig = plt.figure(figsize=(9,2))
    ax = plt.subplot()
    if title:
        ax.set_title(title)

    ax.set_axisbelow(True)
    ax.set_yticks([-1, 1])
    ax.set_yticklabels(['false', 'true'])
    ax.set_ylim(-1.2,1.2)

    plot_stages(
        split_merged_stream(streams['clockEcho']), 
        ax=ax, marker='.', s=200, zorder=2, color_map=colours)
    plot_binary(streams['timeout'], ax=ax, zorder=1, color="#444488")
    plot_labels(streams['acc'], y_offset=0.3, horizontalalignment='center', conditinal_format=lambda x: {'c':'#cc0000'} if x[1] > 10 else {})

    # Shrink current axis's height by 10% on the bottom
    box = ax.get_position()
    ax.set_position([box.x0, box.y0 + box.height * 0.4,
                    box.width, box.height * 0.6])
    
    ax.set_ylabel(f"Timeout")
    ax.set_xlabel("Time step")

    # Put a legend below current axis
    ax.legend(loc='upper left', bbox_to_anchor=(-.1, -.25),
            fancybox=True, shadow=True, ncol=2)

    fig.savefig(outfile, bbox_inches='tight')

def plot_trigger(folder,input_file=None, output_file=None, title=None):
    INPUTFILE=folder + '/' + (input_file or "TWC-output-window.txt")
    outfile=folder + '/' + (output_file or "TWC-output-window.pdf")

    streams = split_dict(
    zero_index(
    read_lola_output(INPUTFILE,['correctOrder', 'scanOut'])
    ))

    colours = {
        's': '#ee6688',
        'm': '#6688ee'
    }

    fig = plt.figure(figsize=(9,2))
    ax = plt.subplot()
    if title:
        ax.set_title(title)

    ax.set_axisbelow(True)
    ax.set_yticks([-1, 1])
    ax.set_yticklabels(['false', 'true'])
    ax.set_ylim(-1.2,1.2)

    plot_stages(
        split_merged_stream(streams['scanOut']), 
        ax=ax, marker='.', s=200, zorder=2, color_map=colours)
    plot_binary(streams['correctOrder'], ax=ax, zorder=1, color="#444488")

    # Shrink current axis's height by 10% on the bottom
    box = ax.get_position()
    ax.set_position([box.x0, box.y0 + box.height * 0.4,
                    box.width, box.height * 0.6])
    
    ax.set_ylabel(f"Trigger\ncorrect order")
    ax.set_xlabel("Time step")

    # Put a legend below current axis
    ax.legend(loc='upper left', bbox_to_anchor=(-.1, -.25),
            fancybox=True, shadow=True, ncol=2)

    fig.savefig(outfile, bbox_inches='tight')

def plot_phase_write(folder, node_name, input_file=None, output_file=None, ncol=3):
    INPUTFILE=folder + '/' + (input_file or "TWC-output-window.txt")
    outfile=folder + '/' + (output_file or "TWC-output-window.pdf")

    streams = split_dict(
    zero_index(
    read_lola_output(INPUTFILE,['s', 'error'])
    ))

    fig = plt.figure(figsize=(9,2))
    ax = plt.subplot()

    ax.set_axisbelow(True)
    ax.set_yticks([-1, 1])
    ax.set_yticklabels(['false', 'true'])
    ax.set_ylim(-1.2,1.2)

    opens = []
    closes = []

    for step, s in streams['s']:
        if s.startswith('start'):
            opens.append(step)
        elif s.startswith('end'):
            closes.append(step)
    
    bars = []
    bars_ws = []
    for s,e in zip(opens, closes):
        bars.append(s)
        bars_ws.append(e-s)
    
    ax.barh([0]*len(bars), bars_ws, left=bars, facecolor="white", edgecolor="green", zorder=2, label='phase duration')

    colours = {
        'start':'#cbd7ea',
        'end': '#b1d0ad',
        'end_ok': '#b1d0ad',
        'end_nom': '#e02e44',
    }

    plot_stages(
        split_merged_stream(streams['s']), 
        ax=ax, marker='.', s=200, zorder=2, color_map=colours)
    plot_binary(streams['error'], ax=ax, zorder=1, color="#444488")

    # Shrink current axis's height by 10% on the bottom
    box = ax.get_position()
    ax.set_position([box.x0, box.y0 + box.height * 0.4,
                    box.width, box.height * 0.6])
    
    ax.set_ylabel(f"Phase write\nerror")
    ax.set_xlabel("Time step")
    ax.set_title(f'Phase write — {node_name}')

    # Put a legend below current axis
    ax.legend(loc='upper left', bbox_to_anchor=(-.1, -.5),
            fancybox=True, shadow=True, ncol=ncol)

    fig.savefig(outfile, bbox_inches='tight')

def plot_anomple(folder,input_file=None, output_file=None, title=None):
    INPUTFILE=folder + '/' + (input_file or "TWC-output-window.txt")
    outfile=folder + '/' + (output_file or "TWC-output-window.pdf")

    streams = split_dict(
    zero_index(
    read_lola_output(INPUTFILE,['timeout', 'acc', 't'])
    ))

    colours = {
        'timer': '#cbd7ea',
        'anom': '#e02e44',
        'end_e': '#a251cb'
    }

    fig = plt.figure(figsize=(9,2))
    ax = plt.subplot()
    if title:
        ax.set_title(title)

    ax.set_axisbelow(True)
    ax.set_yticks([-1, 1])
    ax.set_yticklabels(['false', 'true'])
    ax.set_ylim(-1.2,1.2)

    plot_stages(
        split_merged_stream(streams['t']), 
        ax=ax, marker='.', s=200, zorder=2, color_map=colours)
    plot_binary(streams['timeout'], ax=ax, zorder=1, color="#444488")

    # Shrink current axis's height by 10% on the bottom
    box = ax.get_position()
    ax.set_position([box.x0, box.y0 + box.height * 0.4,
                    box.width, box.height * 0.6])
    
    ax.set_ylabel(f"ANOMPLE\ntimeout")
    ax.set_xlabel("Time step")

    # Put a legend below current axis
    ax.legend(loc='upper left', bbox_to_anchor=(-.1, -.25),
            fancybox=True, shadow=True, ncol=2)

    fig.savefig(outfile, bbox_inches='tight')

# %% MAPLE-1
maple_plot("MAPLE-1_2025-05-14_09-31-56", title="MAPLE property")

# %% SINGLETON
maple_plot("singleton_2025-05-14_11-45-04", legend_ncol=3, title="Singleton property")

# %% Recovering atomic
atomic_plot("atomicity-1r_2025-05-14_12-05-43", title="Atomicity (with recovery)")

# %% New Atomicity
new_atomic_plot('new-atomicity_2025-05-14_14-30-34', title="Atomicity (with sub-loops)")

# %%
plot_knowledge('kLaser_2025-05-15_10-27-19', 'kLaserScanEcho', title="Knowledge (laser)")
plot_knowledge('kDirections_2025-05-15_11-01-49', 'kDirectionsEcho', title="Knowledge (directions)")
plot_knowledge('kHandling_2025-05-15_11-07-17', 'kHandlingAnomalyEcho', title="Knowledge (handling_anomaly)")
plot_knowledge('kIsLegit_2025-05-15_11-12-34', 'kIsLegitEcho', title="Knowledge (isLegit)")
plot_knowledge('kPlannedLidarMask_2025-05-15_11-28-09', 'kPlannedLidarMaskEcho', title="Knowledge (planned_lidar_mask)")

# %% Sign of life
plot_sol('SOL_2025-05-15_13-29-51', title="Sign-of-life")
plot_sol('SOL_2025-05-15_13-29-51', 'TWC-output-window2.txt', 'TWC-output-window2.pdf', title="Sign-of-life with introduced error")

#%%
plot_trigger('scanTrigger_2025-05-15_14-22-36', title="Trigger")
plot_trigger('scanTrigger_2025-05-15_14-22-36', 'TWC-output-end.txt', 'TWC-output-end.pdf', title="Trigger (when managing system stops)")


#%%
plot_phase_write('AnalysisPhaseWrite_2025-05-15_15-47-17', 'Analysis')
plot_phase_write('ExecutePhaseWrite_2025-05-15_15-50-36', 'Execute', 'TWC-output.txt', 'TWC-output.pdf', ncol=4)
plot_phase_write('ExecutePhaseWrite_2025-05-15_15-50-36', 'Execute (Rearranged for error)', 'TWC-output-alt.txt', 'TWC-output-alt.pdf', ncol=4)
plot_phase_write('LegitimatePhaseWrite_2025-05-16_11-39-45', 'Legitimate', 'TWC-output.txt', 'TWC-output.pdf', ncol=4)
plot_phase_write('MonitorPhaseWrite_2025-05-16_11-47-36', 'Monitor', 'TWC-output.txt', 'TWC-output.pdf', ncol=4)
plot_phase_write('PlanPhaseWrite_2025-05-16_11-51-56', 'Plan (before fix)', 'TWC-output.txt', 'TWC-output.pdf')
plot_phase_write('PlanPhaseWrite_2025-05-16_11-56-53', 'Plan', 'TWC-output.txt', 'TWC-output.pdf')

plot_phase_write('AnalysisPhaseWrite_2025-05-16_14-17-14', 'Analysis (fixed)')

# %% Completion
plot_anomple('anomple_2025-05-16_13-18-28', 'twc.txt', 'twc.pdf', title="Completion, timeout after 10 timer ticks @100 ms")
plot_anomple('anomple_2025-05-16_13-39-08', 'twc.txt', 'twc.pdf', title="Completion, timeout after 50 timer ticks @100 ms")
