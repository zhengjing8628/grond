# Grond

A bootstrap-based probabilistic battering ram to explore solution spaces in
earthquake source parameter estimation problems.


## Installation

First, install [Pyrocko](http://pyrocko.org/current/install.html),
then install Grond:

```bash
git clone https://gitext.gfz-potsdam.de/heimann/grond.git
cd grond
sudo python setup.py install
```


## Updating an existing installation

```bash
cd grond  # change to the directory to where you cloned grond initially
git pull origin master
sudo python setup.py install
```


## Basic usage

Grond can be run as a command line tool or by calling Grond's library functions
from a Python script. To get a brief description on available options of
Grond's command line tool, run `grond --help` or `grond <subcommand> --help`.
Once dataset and configuration are ready, the command `grond go <configfile>
<eventname>` starts the optimization algorithm for a selected event. Before
running the optimization, to debug problems with the dataset and configuration,
use `grond check <configfile> <eventname>`. To get a list of event names
available in a configured setup, run `grond events <configfile>`. During the
optimization, results are aggregated in a directory, referred to in the
configuration as `<rundir>`. To visualize the results run `grond plot
<plotnames> <rundir>`. The results can be exported in various ways by running
the subcommand `grond export <what> <rundir>`. Finally, you may run `grond
report <rundir>` to aggregate results to a browsable summary, (by default)
under the directory `reports`.


## Example configuration file

```yaml
%YAML 1.1
--- !grond.Config

# Path, where to store output (run-directories)
rundir_template: 'gruns/${problem_name}.run'

# -----------------------------------------------------------------------------
# Configuration section for dataset (input data)
# -----------------------------------------------------------------------------

dataset_config: !grond.DatasetConfig

  # List of files with station coordinates
  stations_stationxml_paths:
  - 'events/${event_name}/responses-geofon.stationxml'
  - 'events/${event_name}/responses-iris.stationxml'

  # File with hypocenter information and possibly reference solution
  events_path: 'events/${event_name}/prepared/event.txt'

  # List of directories with raw waveform data
  waveform_paths:
  - 'events/${event_name}/raw'

  # List of files with instrument response information
  responses_stationxml_paths:
  - 'events/${event_name}/responses-geofon.stationxml'
  - 'events/${event_name}/responses-iris.stationxml'

  # List with station/channel codes to exclude
  #blacklist: ['STA','NET.STA', 'NET.STA.LOC', 'NET.STA.LOC.CHA']

  # Same but using a file, one exclusion entry per line
  blacklist_paths:
  - 'events/${event_name}/blacklist.txt'

  # Make available picks for forced trace alignment, file must be in Pyrocko's
  # marker file format
  #picks_paths: ['events/${event_name}/picks.markers']


# -----------------------------------------------------------------------------
# Configuration section for synthetic seismogram engine (configures where
# to look for GF stores)
# -----------------------------------------------------------------------------

engine_config: !grond.EngineConfig

  # Whether to use GF store directories listed in ~/.pyrocko/config.pf
  gf_stores_from_pyrocko_config: false

  # List of directories with GF stores
  gf_store_superdirs:
  - 'gf_stores'


# -----------------------------------------------------------------------------
# Configuration section selecting data to be included in the data fitting
# procedure. This defines the objective function to be minimized in the
# optimization procedure. It can be composed of one or more contributions, each
# represented by a !grond.TargetConfig section.
# -----------------------------------------------------------------------------

target_groups:

- !grond.WaveformTargetGroup

  # misfits are normalized within each normalization_family separately
  normalization_family: 'td'

  # Name of the group to which this contribution belongs
  path: 'td.rayleigh'

  # Minimum distance of stations to be considered
  distance_min: 0e3

  # Maximum distance of stations to be considered
  distance_max: 1000e3

  # List with names of channels to be considered
  channels: ['Z']

  # How to weight stations from this contribution in the global misfit
  weight: 1.0

  # Subsection on how to fit the traces
  misfit_config: !grond.WaveformMisfitConfig

    # Frequency band [Hz] of acausal filter (flat part of frequency taper)
    fmin: 0.01
    fmax: 0.05

    # Factor defining fall-off of frequency taper
    # (zero at fmin/ffactor, fmax*ffactor)
    ffactor: 1.5

    # Time window to include in the data fitting. Times can be defined offset
    # to given phase arrivals. E.g. '{stored:begin}-100' would mean 100 s 
    # before arrival of the phase named 'begin', which must be defined in the 
    # travel time tables in the GF store.

    tmin: '{stored:anyP_no_Pdiff}'
    tmax: '{vel_surface:2.5}'

    # Align traces by picks (will lose some control on origin time and 
    # location). Define the synthetic phasename, for which a travel time table 
    # must be available in the GF store, 
    #pick_synthetic_traveltime: 'anyP_no_Pdiff'
    # and the name of the picks to use in the picks file (defined in 
    # dataset_config)
    #pick_phasename: 'P'

    # How to fit the data (available choices: 'time_domain',
    # 'frequency_domain', 'absolute', 'envelope', 'cc_max_norm')
    domain: 'time_domain'

    # allow for some time-shifting of individual traces, maximum shift [s]
    tautoshift_max: 4.0

    # whether to penalise time-shifting (0.0 for no penalty)
    autoshift_penalty_max: 0.0

    # exponent of the norm used when comparing traces, 1 or 2
    norm_exponent: 1

  # How to interpolate the Green's functions (available choices:
  # 'nearest_neighbor', 'multilinear'). Note that the GFs have to be densely 
  # sampled when using interpolation other than nearest_neighbor.
  interpolation: 'nearest_neighbor'

  # Name of GF store to use
  store_id: 'global_2s'


# A second contribution to the misfit function (for descriptions, see above)
- !grond.WaveformTargetGroup
  normalisation_family: 'td'
  path: 'td.love'
  distance_min: 0e3
  distance_max: 1000e3
  channels: [T]
  weight: 1.0
  #limit: 20
  misfit_config: !grond.WaveformMisfitConfig
    fmin: 0.01
    fmax: 0.05
    ffactor: 1.5
    tmin: 'stored:anyP_no_Pdiff'
    tmax: 'vel_surface:2.5'
    domain: time_domain
    tautoshift_max: 4.0
    autoshift_penalty_max: 0.0
    norm_exponent: 1
  interpolation: nearest_neighbor
  store_id: 'global_2s'


# -----------------------------------------------------------------------------
# Definition of the problem to be solved - source model, parameter space, and
# global misfit configuration settings.
# -----------------------------------------------------------------------------

problem_config: !grond.CMTProblemConfig

  # Name used when creating output directory
  name_template: 'timedomain_${event_name}'

  # Definition of model parameter space to be searched in the optimization
  ranges:
    # Time relative to hypocenter origin time [s]
    time: '-10 .. 10 | add'

    # Centroid location with respect to hypocenter origin [m]
    north_shift: '-40e3 .. 40e3'
    east_shift: '-40e3 .. 40e3'
    depth: '0 .. 50e3'

    # Range of magnitudes to allow
    magnitude: '4.0 .. 7.0'

    # Relative moment tensor component ranges (don't touch)
    rmnn: '-1.41421 .. 1.41421'
    rmee: '-1.41421 .. 1.41421'
    rmdd: '-1.41421 .. 1.41421'
    rmne: '-1 .. 1'
    rmnd: '-1 .. 1'
    rmed: '-1 .. 1'

    # Source duration range [s]
    duration: '0. .. 0.'

  # Clearance distance around stations (no models with origin closer than this
  # distance to any station are produced by the sampler)
  distance_min: 0.

  # Type of moment tensor to restrict to (choices: 'full', 'deviatoric')
  mt_type: 'deviatoric'

  # Whether to apply automatic weighting to balance the effects of geometric
  # spreading etc.
  apply_balancing_weights: true

  # Under what norm to combine targets into the global misfit 
  # (exponent of norm, 1 or 2)
  norm_exponent: 1


# -----------------------------------------------------------------------------
# Configuration of the optimization procedure
# -----------------------------------------------------------------------------

# This configuration will run the BABO (Bayesian Bootstrap) optimization
optimizer_config: !grond.HighScoreOptimizerConfig

  # Number of bootstrap realizations to be tracked simultaneously in the
  # optimization
  nbootstrap: 100

  sampler_phases:

  - !grond.UniformSamplerPhase

      # Number of iterations to operate in 'uniform' phase
      niterations: 1000

  - !grond.DirectedSamplerPhase

      # Number of iterations to operate in 'directed' phase
      niterations: 10000

      # Multiplicator for width of sampler distribution at end of this phase 
      scatter_scale_begin: 2.0

      # Multiplicator for width of sampler distribution at end of this phase 
      scatter_scale_end: 0.5


# -----------------------------------------------------------------------------
# Configuration of pre-optimization analysis phase. E.g. balancing weights are
# determined during this phase.
# -----------------------------------------------------------------------------

analyser_config: !grond.AnalyserConfig

  # Number of iterations (number of models to forward model in the analysis,
  # larger number -> better statistics)
  niterations: 1000
```
