#!/bin/env python3
import argparse
import re
from matplotlib.figure import Figure
from matplotlib.axes import Axes
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection


def chain(initial_value, *funcs):
    """Chain a list of functions together by passing the return value to the next function.

    Args:
        initial_value (Any): Initial value to pass to the first function.

    Returns:
        Any: Return value of the last function
    """
    v = initial_value
    for func in funcs:
        v = func(v)
        # print(v)

    return v


"""
Recognized patterns of the LOLA input parser
"""
COMMENT = r"//.*"
MAYBE_COMMENT = f"({COMMENT})?"
WHITESPACE = r"\s*"
INDEX = r"(\d+)"
SEP = ":"
STREAM = r"([a-zA-Z]+)"
EQ = "="
VAL = r'((true|false)|(\d+)|"(.*)")'


def join_pattern(*tokens):
    """Join multiple patterns together allowing any non-line-breaking whitespace between.

    Returns:
        str: Resulting RegEx pattern
    """
    pattern = WHITESPACE
    for tok in tokens:
        pattern += tok + WHITESPACE
    return pattern


def parse(inp: str):
    """Parse an input LOLA specification to an internal data structure.

    Args:
        inp (str): String containing the contents of a LOLA input specification

    Raises:
        Exception: Bad line. Does not match any defined patterns.

    Returns:
        dict: Each item in the result corresponds to a time step, with the step as 
              the key and the value being another dict of all streams and their value 
              at this step.
    """
    lines = inp.split("\n")
    idx = None
    steps = {}

    for line in lines:
        # Ignore comments
        m = re.match(join_pattern(COMMENT) + r"|\s*$", line)
        if m:
            continue

        # Regular stream inputs; "i: stream = value"
        m = re.match(join_pattern(INDEX, SEP, STREAM, EQ, VAL), line)
        if m:
            idx, stream, raw_val, val_bool, val_int, val_str = m.groups()
            idx = int(idx)

            if idx not in steps:
                steps[idx] = dict()
        else:
            # Multiple streams in the same time step can omit the "i:" part and use the step index from the previous line
            m = re.match(join_pattern(STREAM, EQ, VAL), line)
            if m:
                stream, raw_val, val_bool, val_int, val_str = m.groups()

            else:
                raise Exception("Bad line: ", line)

        # Get the value data type and format it correctly
        match (val_int, val_bool, val_str):
            case (int() as i, None, None):
                val = int(i)
            case (None, str() as b, None):
                val = b == "true"
            case (None, None, str() as s):
                val = s
            case _:
                val = raw_val

        steps[idx][stream] = val

    return steps


def format_atomic(parsed: dict):
    """The "atomicity" tests is based on the "atomicstage" stream with values "start_x"/"end_x".
    This gets this "x" which corresponds to the phase of the MAPLE loop and saves whether the event is a "start" or and "end".
    Additionally, the phase can have an additional comment "end_aok" (Normal analysis result) "end_anom" (anomaly in analysis result).
    This extra comment is also saved

    Args:
        parsed (dict): Dictionary of streams as returned by the parsing step

    Raises:
        Exception: Missing stage
        Exception: Stage does not match MAPLE

    Returns:
        dict: {phase_key: [step, start/end, extra]}
    """
    stages = {}
    for step, streams in parsed.items():
        val = streams.get("atomicstage")
        if val is None:
            raise Exception("Missing stage in step", step)
        m = re.fullmatch(r"(start|end)_([maple])(.*)?", val)
        if m is None:
            raise Exception("Stage not matching:", val)
        lifecycle, stage, extra = m.groups()
        if stage not in stages:
            stages[stage] = []
        stages[stage].append((step, lifecycle, extra))

    return stages


def plot_maple_stages(data):
    """Create a time-line plot over which stage is active. Potential extra comments for each stage is added as a label.

    Args:
        data (dict[int, list]): Output from format_atomic
    
    Returns:
        fig, ax: Matplotlib figure data
    """

    # From a list of (atomic) events, create a new list with the start and end steps for every phase
    def create_boxes(data: list[tuple[int, str, str]]):
        boxes: list[tuple[int, int, str]] = []
        starts = []
        for step, lifecycle, extra in data:
            match lifecycle:
                case "start":
                    starts.append((step, extra))
                case "end":
                    start_step, start_extra = starts.pop()
                    if start_extra:
                        extra = start_extra + "," + extra
                    boxes.append((start_step, step, extra))
        # TODO: Handle cases without matching start and end
        return boxes

    # Map MAPLE category shorthands to the plot's y-values
    categories = {"m": 0, "a": 1, "p": 2, "l": 3, "e": 4}

    # Create polygons for each bar
    verts = []
    labels = []
    for k, v in data.items():
        y = categories[k]

        for xfrom, xto, text in create_boxes(v):
            v = [
                (xfrom, y - 0.4),
                (xfrom, y + 0.4),
                (xto, y + 0.4),
                (xto, y - 0.4),
                (xfrom, y - 0.4),
            ]
            labels.append(((xfrom + xto) / 2, y, text))
            verts.append(v)

    bars = PolyCollection(verts, zorder=3)

    # Draw the plot
    fig, ax = plt.subplots(figsize=[8, 3], dpi=200)
    for label in labels:
        ax.text(
            *label,
            zorder=5,
            color="black",
            backgroundcolor="white",
            fontsize=10,
            va="center",
            ha="center",
        )
    ax.grid(zorder=0)
    ax.add_collection(bars)
    ax.autoscale()

    ax.set_yticks(list(categories.values()))
    ax.set_yticklabels(list((categories.keys())))

    return fig, ax

# Update a figure in a chained function call with a title
def set_fig_title(title: str):
    def f(data: tuple[Figure, Axes]):
        fig, ax = data
        ax.set_title(title)
        return fig, ax

    return f

# Save a figure as part of a chained function call
def save_fig(filename):
    def f(data: tuple[Figure, Axes]):
        fig, ax = data
        fig.savefig(filename)
        return fig, ax

    return f


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse LOLA input files for processing"
    )
    parser.add_argument("input", help="The input lola file", type=str)
    parser.set_defaults(cmd=None)
    subparsers = parser.add_subparsers()

    atomic_parser = subparsers.add_parser(
        "atomic", help="Generate a bar chart of the stages"
    )
    atomic_parser.add_argument("-o", "--output", help="The output file", type=str)
    atomic_parser.set_defaults(cmd="atomic")

    args = parser.parse_args()

    with open(args.input) as f:
        input_text = f.read()

    match args.cmd:
        case "atomic":
            plot = chain(
                input_text,
                parse,
                format_atomic,
                plot_maple_stages,
                set_fig_title(args.input),
            )
            out = args.output
            if out:
                if "." not in out:
                    out = out + ".png"
                save_fig(out)(plot)
            else:
                # Show the plot in a windows if no output file is given
                plt.show()
        case _:
            parser.print_help()
