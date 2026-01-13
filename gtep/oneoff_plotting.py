from pathlib import Path
import json
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import pandas as pd
import numpy as np
import matplotlib.patheffects as pe
import re
import networkx as nx
from matplotlib.patches import FancyArrowPatch


save_dir = "./5busPlots/"
block_pos = "bottom"  # "centered"  # 'bottom'

plt.rcParams.update({"font.size": 24})


def read_json(filepath):
    # read a json file and recover a solution primals
    json_filepath = Path(filepath)
    with open(json_filepath, "r") as fobj:
        json_read = json.loads(fobj.read())
    return json_read


def branches_to_dict(dict_in):

    # split_subkey_prefixes = ["gen", "branch"]

    # ignore_this = "branch"
    # ignore_this = "gen"

    branch_results_dict = {}

    investment_stage_keys = [
        this_key
        for this_key in dict_in["results"]["primals_tree"].keys()
        if "investmentStage" in this_key
    ]

    for this_invest_stage in investment_stage_keys:
        branch_results_dict.setdefault(this_invest_stage, {})
        branch_keys_in_stage = [
            this_key
            for this_key in dict_in["results"]["primals_tree"][this_invest_stage].keys()
            if "branch" in this_key
        ]

        # pull out the category in the middle of the key, and the name, and the state
        for branch_key in branch_keys_in_stage:
            match_category = re.search(r"branch(.*?)\[", branch_key)
            match_name = re.search(r"\[(.*?)\]", branch_key)
            if match_category and match_name:
                # match_category.group(1)
                # match_name.group(1)
                branch_results_dict[this_invest_stage].setdefault(
                    match_category.group(1), {}
                )
                branch_results_dict[this_invest_stage][match_category.group(1)][
                    match_name.group(1)
                ] = dict_in["results"]["primals_tree"][this_invest_stage][branch_key][
                    "value"
                ]

    return branch_results_dict


def plot_investment_graph(bus_dict, branch_dict, branch_results_dict, suptitle):
    branch_state_colors = {
        "Installed": "xkcd:blue",
        #"Extended": "xkcd:orange",
        "Operational": "xkcd:green",
        "Disabled": "xkcd:orange",
        #"Retired": "xkcd:grey",
    }
    branch_state_linestyles = {
        "Installed": "--",
        #"Extended": "-.",
        "Operational": "-",
        "Disabled": ":",
        #"Retired": ":",
    }
    branch_line_thickness = 3

    for this_invest_stage, this_branch_states in branch_results_dict.items():
        G = nx.MultiGraph()
        labels = {}

        # add nodes
        for this_branch, this_branch_attrs in branch_dict.items():
            from_bus = this_branch_attrs["from_bus"]
            to_bus = this_branch_attrs["to_bus"]
            G.add_node(from_bus)
            labels[from_bus] = from_bus
            G.add_node(to_bus)
            labels[to_bus] = to_bus

        # add multiedges with state metadata
        for this_branch_state_name, this_branch_state_dict in this_branch_states.items():
            for this_branch, this_state in this_branch_state_dict.items():
                if bool(this_state):
                    from_bus = branch_dict[this_branch]["from_bus"]
                    to_bus = branch_dict[this_branch]["to_bus"]
                    edge_key = f"{this_branch}_{this_branch_state_name}"
                    G.add_edge(
                        from_bus,
                        to_bus,
                        key=edge_key,
                        state=this_branch_state_name,
                    )

        # layout & base drawing
        fig, ax_graph = plt.subplots(figsize=(16, 8))
        ax_graph.grid(False)
        pos = nx.kamada_kawai_layout(G)

        nx.draw_networkx_nodes(
            G,
            pos,
            node_size=3000,
            node_color="white",
            edgecolors="black",
            ax=ax_graph,
        )
        nx.draw_networkx_labels(
            G,
            pos,
            labels,
            font_size=18,
            font_color="black",
            ax=ax_graph,
        )

        # group edges by unordered pair to assign unique rad per parallel edge
        pair_to_edges = {}
        for u, v, k, data in G.edges(data=True, keys=True):
            pair = tuple(sorted((u, v)))
            pair_to_edges.setdefault(pair, []).append((u, v, k, data))

        def make_rads(m, base=0.5):
            if m == 1:
                return [0.0]
            if m % 2 == 1:
                half = (m - 1) // 2
                return [((i - half) * base) for i in range(m)]
            else:
                return [((i + 0.5) - m / 2) * base for i in range(m)]

        # draw each parallel edge individually using FancyArrowPatch for true curvature
        for pair, edges in pair_to_edges.items():
            rads = make_rads(len(edges), base=0.2) # change base to adjust curvature
            for (_, _, _, data), rad in zip(edges, rads):
                u, v = pair
                state = data["state"]
                color = branch_state_colors.get(state, "black")
                style = branch_state_linestyles.get(state, "-")
                connectionstyle = f"arc3,rad={rad}"
                arrow = FancyArrowPatch(
                    pos[u],
                    pos[v],
                    connectionstyle=connectionstyle,
                    arrowstyle="-",  # undirected
                    linewidth=branch_line_thickness,
                    linestyle=style,
                    color=color,
                    shrinkA=0,
                    shrinkB=0,
                    zorder=-1,
                )
                ax_graph.add_patch(arrow)

        # legend
        for state, state_color in branch_state_colors.items():
            ax_graph.plot(
                [None],
                [None],
                label=state,
                color=state_color,
                linestyle=branch_state_linestyles[state],
            )

        fig.legend(loc="lower center", fancybox=True, shadow=True, ncol=5)
        fig.suptitle(f"{suptitle} - {this_invest_stage}")
        fig.savefig(f"{save_dir}DC_ExtremeVariation_{this_invest_stage}_SuperNew.png")
        plt.close(fig)


target_file = Path(
    "./gtep_solution_DC_5busExtremeVariation_test.json"
)

# read gen info
gens_pd = pd.read_csv("./gtep/data/5bus_jsc/gen.csv")

# "./gtep_wiggles.json"
# this_json = read_json("./dispatchable_investments 2.json")
this_json = read_json(target_file)
bus_dict = this_json["data"]["elements"]["bus"]
branch_dict = this_json["data"]["elements"]["branch"]
branch_results_dict = branches_to_dict(this_json)
states_order = ["genDisabled", "genExtended", "genInstalled", "genOperational"]
#print("This is different now")
plot_investment_graph(
    bus_dict, branch_dict, branch_results_dict, "Dispatchable Investments"
)

pass
