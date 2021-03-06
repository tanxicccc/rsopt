import sys, subprocess, os
import numpy as np

# Import libEnsemble items for this test
from libensemble.libE import libE
from rsopt.codes.warp.libe_sim import simulate_tec_efficiency as sim_f

# Only import the optimizer package we need for APOSMM
import libensemble.gen_funcs
libensemble.gen_funcs.rc.aposmm_optimizers = 'nlopt'

from libensemble.gen_funcs.persistent_aposmm import aposmm as gen_f
from libensemble.alloc_funcs.persistent_aposmm_alloc import persistent_aposmm_alloc as alloc_f
from libensemble.tools import parse_args, save_libE_output, add_unique_random_streams
from time import time

# Output/Run directory setup
# `base_directory` should be set before running this script
# Recommendations are provided below are well
base_directory = '/home/vagrant/jupyter/StaffScratch/cchall/opt_tests'
# For NERSC use
# base_directory = os.environ['SCRATCH']

# RUN SETTINGS
RUN_NAME = 'tec_efficiency_example'
# Base design for the TEC to start optimization
TEMPLATE_FILE = 'gpyopt_best.yaml'
RUN_DIR = os.path.join(base_directory, RUN_NAME)
# Can be used to load the results of a previous optimization run
CHECKPOINT_FILE = None
# How often to record parameters in the middle of the optimization
CHECKPOINTS = 1  # Steps per libE checkpoint
# How many points does APOSMM sample before it starts to run optimization
INIT_SAMPLES = 15
# Optimizer input parameter dimensionality
N = 2
# Local optimizer that APOSMM wil use - see APOSMM documentation for more information
LOCAL_OPT = 'LN_BOBYQA'

# Simulation Options
PROCESSORS = 1  # Number of processors to use for each Warp simulation


# libEnsemble Setup     
nworkers, is_master, libE_specs, _ = parse_args()
ranks = libE_specs['comm'].size
print("Number of workers:", nworkers)
print("MPI ranks:",libE_specs['comm'].size)
print("1 worker will run the persistent generator.")
print("\n{} workers will be able to work simultaneously with {} processors each.".format((nworkers-1)//PROCESSORS, PROCESSORS))

if is_master:
    if not os.path.isdir('./{}'.format(RUN_DIR)):
        os.makedirs('{}'.format(RUN_DIR))
    else:
        print("Stopping - Directory exists: {}".format(RUN_DIR))
        exit()


if CHECKPOINTS:
    libE_specs['save_every_k_sims'] = CHECKPOINTS
libE_specs['sim_dirs_make'] = False
libE_specs['ensemble_dir_path'] = RUN_DIR
libE_specs['sim_dir_copy_files'] = [os.path.join('./support', TEMPLATE_FILE)]

if is_master:
    start_time = time()


# Job Controller
from libensemble.executors.mpi_executor import MPIExecutor
jobctrl = MPIExecutor(auto_resources=True, central_mode=True)


# Sim App
sim_app = 'rsopt'
jobctrl.register_calc(full_path=sim_app, calc_type='sim')


# Setup for Run with APOSMM
USER_DICT = {
             'failure_penalty': -10.,
             'base_path': RUN_DIR,
             'cores': PROCESSORS,
             'time_limit': 30. * 60.,
             'template_file': TEMPLATE_FILE,
             'scaling': lambda x: -1.0 * x  # Change to minimization problem, seeking eff = -1.0
             }

sim_specs = {'sim_f': sim_f,
             'in': ['x'],
             'out': [('f', float)],
             'user': USER_DICT
             }

gen_out = [('x', float, N), ('x_on_cube', float, N), ('sim_id', int),
           ('local_min', bool), ('local_pt', bool)]

gen_specs = {'gen_f': gen_f,
             'in': [],
             'out': gen_out,
             'user': {'initial_sample_size': INIT_SAMPLES,
                      'localopt_method': 'LN_BOBYQA',
                      'xtol_rel': 1e-12,
                      'ftol_rel': 1e-12,
                      'high_priority_to_best_localopt_runs': True,
                      'max_active_runs': nworkers,
                      'lb': np.array([0.5e-6, 0.5e-6]),
                      'ub': np.array([2.5e-6, 2.5e-6])}
             }

alloc_specs = {'alloc_f': alloc_f, 'out': [('given_back', bool)], 'user': {'batch_mode': True}}
persis_info = add_unique_random_streams({}, nworkers + 1)
exit_criteria = {'sim_max': 45}

# Perform the run
# Load from Checkpoint if requested
if CHECKPOINT_FILE:
    H0 = np.load(CHECKPOINT_FILE)
    H0 = H0[H0['given_back'] * H0['returned']]  # Remove points that failed to evaluate before end of run
else:
    H0 = None


# Perform the run
H, persis_info, flag = libE(sim_specs, gen_specs, exit_criteria, persis_info,
                            alloc_specs, libE_specs, H0=H0)

if is_master:
    print('[Manager]: Time taken =', time() - start_time, flush=True)
    save_libE_output(H, persis_info, __file__, nworkers)
