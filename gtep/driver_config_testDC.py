from gtep.gtep_model import ExpansionPlanningModel
from gtep.gtep_data import ExpansionPlanningData
from gtep.gtep_solution import ExpansionPlanningSolution
from pyomo.core import TransformationFactory
from pyomo.environ import SolverFactory
from pyomo.contrib.appsi.solvers.highs import Highs
from pyomo.contrib.appsi.solvers.gurobi import Gurobi
from pyomo.contrib.appsi.solvers.ipopt import Ipopt
from icecream import ic
import json
from pathlib import Path

data_path = "./gtep/data/123_Bus_Coal"
data_object = ExpansionPlanningData()
data_object.load_prescient(data_path)

def load_dc_plan(json_path):
    primals = json.loads(Path(json_path).read_text())["results"]["primals_tree"]
    plan = {}
    for stage_key, payload in primals.items():
        if not stage_key.startswith("investmentStage"):
            continue
        stage = int(stage_key.split("[")[1].split("]")[0])
        plan[stage] = {
            name: entry["value"]
            for name, entry in payload.items()
            if name.startswith(("branch", "gen", "renewable"))
        }
    return plan

def apply_plan_to_model(m, plan):
    for stage, stage_plan in plan.items():
        blk = m.investmentStage[stage]
        for br in m.transmission:
            for tag in ("Operational", "Installed", "Retired", "Disabled", "Extended"):
                key = f"branch{tag}[{br}]"
                if key in stage_plan:
                    getattr(blk, f"branch{tag}")[br].indicator_var.fix(int(round(stage_plan[key])))
        for gen in m.thermalGenerators:
            for tag in ("Operational", "Installed", "Retired", "Disabled", "Extended"):
                key = f"gen{tag}[{gen}]"
                if key in stage_plan:
                    getattr(blk, f"gen{tag}")[gen].indicator_var.fix(int(round(stage_plan[key])))
        for ren in m.renewableGenerators:
            for varname in ("renewableOperational", "renewableInstalled", "renewableRetired", "renewableExtended"):
                key = f"{varname}[{ren}]"
                if key in stage_plan:
                    getattr(blk, varname)[ren].fix(stage_plan[key])

# Usage
# dc_plan = load_dc_plan("gtep_solution_DC_9busExtremeVariation_trying.json")


mod_object = ExpansionPlanningModel(
    stages=3,
    data=data_object.md,
    num_reps=1,
    len_reps=1,
    num_commit=24, # 24
    num_dispatch=6, # 4
)
mod_object.config["flow_model"] = "DC"
for k,v in mod_object.config.items():
    ic(k,v)

# quit()

mod_object.create_model()
# apply_plan_to_model(mod_object.model, dc_plan)
#ic(mod_object)


#quit()
TransformationFactory("gdp.bound_pretransformation").apply_to(mod_object.model)
TransformationFactory("gdp.bigm").apply_to(mod_object.model)
opt = SolverFactory("gurobi")
opt = Gurobi()
#opt = SolverFactory("ipopt")
#opt = Ipopt()
opt.config.logfile = "logfile_Moderate_DC_123bus.txt"
# # mod_object.results = opt.solve(mod_object.model, tee=True)
mod_object.results = opt.solve(mod_object.model)

sol_object = ExpansionPlanningSolution()
sol_object.load_from_model(mod_object)
sol_object.dump_json("./gtep_solution_Moderate_DC_123bus.json")

sol_object.import_data_object(data_object)

# sol_object.read_json("./gtep_lots_of_buses_solution.json")  # "./gtep/data/WECC_USAEE"
# sol_object.read_json("./gtep_11bus_solution.json")  # "./gtep/data/WECC_Reduced_USAEE"
# sol_object.read_json("./gtep_solution.json")
# sol_object.read_json("./updated_gtep_solution_test.json")
# sol_object.read_json("./gtep_wiggles.json")
# sol_object.plot_levels(save_dir="./plots/")

# save_numerical_results = False
# if save_numerical_results:

#     sol_object = ExpansionPlanningSolution()

#     sol_object.load_from_model(mod_object)
#     sol_object.dump_json()
# load_numerical_results = False
# if load_numerical_results:
#     # sol_object.read_json("./gtep_solution.json")
#     sol_object.read_json("./bigger_longer_wigglier_gtep_solution.json")
plot_results = False
if plot_results:
    sol_object.plot_levels(save_dir="./gtep/ACreactive_plots/")



pass
