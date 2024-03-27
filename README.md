# MoSeq2-Viz: Visualization toolbox for MoSeq2

[![Build Status](https://travis-ci.com/dattalab/moseq2-viz.svg?token=XJGe3NpjKFY5oYjdNcmg&branch=test-suite)](https://travis-ci.com/dattalab/moseq2-viz)

[![codecov](https://codecov.io/gh/dattalab/moseq2-viz/branch/test-suite/graph/badge.svg?token=jUx63Whtx4)](https://codecov.io/gh/dattalab/moseq2-viz)

Latest version number: `0.5.0`

## Features 

Below are the commands/functionality that moseq2-viz currently affords. 
They are accessible via CLI or Jupyter Notebook in [moseq2-app](https://github.com/dattalab/moseq2-app/tree/release). 
```bash
Usage: moseq2-viz [OPTIONS] COMMAND [ARGS]...

Options:
  --version  Show the version and exit.  [default: False]
  --help     Show this message and exit.  [default: False]

Commands:
  add-group                       Change group name in index file given a...
  copy-h5-metadata-to-yaml        Copies metadata within an h5 file to a...
  get-best-model                  Returns the model with the closest median...
  make-crowd-movies               Writes movies of overlaid examples of the...
  plot-group-position-heatmaps    Plots position heatmaps for each group in...
  plot-scalar-summary             Plots a scalar summary of the index file...
  plot-stats                      Plots syllable usages with different...
  plot-transition-graph           Plots the transition graph depicting the...
  plot-verbose-position-heatmaps  Plots a position heatmap for each session...
```

### Exclusive GUI Function
```
  get_groups_command(index_file)  Prints the given index file's current session metadata groupings.
```

Run any command with the `--help` flag to display all available options and their descriptions.

## Documentation

MoSeq2 uses `sphinx` to generate the documentation in HTML and PDF forms. To install `sphinx`, follow the commands below:
```.bash
pip install sphinx==3.0.3 sphinx_click==2.5.0
pip install sphinx-rtd-theme
pip install rst2pdf
``` 

All documentation regarding moseq2-extract can be found in the `Documentation.pdf` file in the root directory,
an HTML ReadTheDocs page can be generated via running the `make html` in the `docs/` directory.

To generate a PDF version of the documentation, simply run `make pdf` in the `docs/` directory.

## Prerequisites

To use this package, you must already have computed a `pca_scores.h5` files, a trained model: `model.p`, an index file
 `moseq2-index.yaml` listing all your analyzed sessions and paths to their extracted `.h5` files.  

 - The index file is generated when aggregating the results in [moseq2-extract](https://github.com/dattalab/moseq2-extract/tree/release) 
 - The pca_scores are generated via [moseq2-pca](https://github.com/dattalab/moseq2-pca/tree/release).
 - The model is generated via [moseq2-model](https://github.com/dattalab/moseq2-model/tree/release).
 
 
## Example Outputs

#### Crowd Movie Example:
<img src="https://github.com/dattalab/moseq2-viz/blob/release/media/rear_up_wall.gif" width=350 height=350>

#### Usage Plot Example:

<img src="https://github.com/dattalab/moseq2-viz/blob/release/media/usages.png">

#### Alternative Sorting Examples:

##### Usages by Mutated Behaviors (most mutated to least)

<img src="https://github.com/dattalab/moseq2-viz/blob/release/media/u_mute.png">

##### Sorting Syllable Statistic in Descending Order (Speed shown)

<img src="https://github.com/dattalab/moseq2-viz/blob/release/media/speeds.png">

#### Scalar Summary Example:

<img src="https://github.com/dattalab/moseq2-viz/blob/release/media/scalars.png">

#### Position Heatmap Example:

<img src="https://github.com/dattalab/moseq2-viz/blob/release/media/heatmaps.png">

#### Transition Graph Example:

<img src="https://github.com/dattalab/moseq2-viz/blob/release/media/transitions2.png" height=500 width=500>


## Contributing

If you would like to contribute, fork the repository and issue a pull request.  