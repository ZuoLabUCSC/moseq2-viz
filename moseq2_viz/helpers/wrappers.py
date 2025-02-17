'''

Wrapper functions for all functionality included in MoSeq2-Viz that is accessible via CLI or GUI.
Each wrapper function executes the functionality from end-to-end given it's dependency parameters are inputted.
(See CLI Click parameters)

'''
import os
import shutil
import matplotlib as mpl
from glob import glob
from ruamel import yaml
from tqdm.auto import tqdm
from cytoolz import keyfilter, groupby
from os.path import exists, join, dirname, basename
from moseq2_viz.scalars.util import scalars_to_dataframe, compute_all_pdf_data
from moseq2_viz.io.video import write_crowd_movies, write_crowd_movie_info_file
from moseq2_viz.util import (parse_index, get_index_hits, get_metadata_path, clean_dict,
                             h5_to_dict, recursive_find_h5s)
from moseq2_viz.model.trans_graph import get_trans_graph_groups, compute_and_graph_grouped_TMs
from moseq2_viz.viz import (plot_syll_stats_with_sem, scalar_plot, plot_mean_group_heatmap,
                            plot_verbose_heatmap, save_fig, plot_cp_comparison)
from moseq2_viz.model.util import (relabel_by_usage, parse_model_results,
                                   get_best_fit, compute_behavioral_statistics,
                                   make_separate_crowd_movies, labels_to_changepoints)


def _make_directories(crowd_movie_path, plot_path):

    # Set up output directory to save crowd movies in
    if crowd_movie_path is not None:
        os.makedirs(crowd_movie_path, exist_ok=True)
    # Set up output directory to save plots in
    if plot_path is not None:
        os.makedirs(dirname(plot_path), exist_ok=True)


def init_wrapper_function(index_file=None, output_dir=None, output_file=None):
    '''
    Helper function that will optionally load the index file and a trained model given their respective paths.
    The function will also create any output directories given path to the output file or directory.

    Parameters
    ----------
    index_file (str): path to index file to load.
    output_dir (str): path to directory to save plots in.
    output_file (str): path to saved figures.

    Returns
    -------
    index (dict): loaded index file dictionary
    sorted_index (dict): OrderedDict object representing a sorted version of index
    '''

    _make_directories(output_dir, output_file)

    # Get sorted index dict
    if index_file is not None:
        index, sorted_index = parse_index(index_file)
    else:
        index, sorted_index = None, None

    return index, sorted_index


def add_group_wrapper(index_file, config_data):
    '''
    Given a pre-specified key and value, the index file will be updated
    with the respective found keys and values.

    Parameters
    ----------
    index_file (str): path to index file
    config_data (dict): dictionary containing the user specified keys and values

    Returns
    -------
    None
    '''
    new_index_path = f'{index_file.replace(".yaml", "")}_update.yaml'

    # Read index file contents
    index, _ = parse_index(index_file)
    h5_uuids = [f['uuid'] for f in index['files']]
    metadata = [f['metadata'] for f in index['files']]

    value = config_data['value']
    key = config_data['key']

    if isinstance(value, str):
        value = [value]

    # Search for inputted key-value pair and relabel all found instances in index
    for v in value:
        if config_data['exact']:
            v = r'\b{}\b'.format(v)

        # Get matched keys
        hits = get_index_hits(config_data, metadata, key, v)

        # Update index dict with inputted group values
        for uuid, hit in zip(h5_uuids, hits):
            position = h5_uuids.index(uuid)
            if hit:
                index['files'][position]['group'] = config_data['group']


    # Atomically write updated index file
    with open(new_index_path, 'w+') as f:
        yaml.safe_dump(index, f)
    shutil.move(new_index_path, index_file)

    print('Group(s) added successfully.')


def get_best_fit_model_wrapper(model_dir, cp_file, output_file, plot_all=False, ext='p', fps=30,
                               objective='duration'):
    '''
    Given a directory containing multiple models trained on different kappa values,
    finds the model with the closest median syllable duration to the PC changepoints.
    Function also graphs the distributions of the best fit model and PC changepoints

    Parameters
    ----------
    model_dir (str): Path to directory containing multiple models.
    cp_file (str): Path to PCA changepoints
    output_file (str): Path to file to save figure to.
    plot_all (bool): Plot all model changepoint distributions.
    ext (str): File extension to search for models with
    fps (int): Frames per second
    objective (str): can be either duration or jsd. The objective finds the best model
        based on either median changepoint durations or the jensen-shannon divergence
        beteween changepoint duration distributions

    Returns
    -------
    selected_model_path (str): Path to model with closest median duration to PC Changepoints
    fig (pyplot figure): syllable usage ordered by frequency, 90% usage marked
    '''

    # Get models
    if not ext.startswith('.'): ext = '.' + ext
    models = glob(join(model_dir, f'*{ext}'), recursive=True)

    print(f'Found {len(models)} models in given input folder: {model_dir}')

    # Load models into a single dict and compute their changepoints
    def _load_models(pth):
        mdl = parse_model_results(pth)
        mdl['changepoints'] = labels_to_changepoints(mdl['labels'], fs=fps)
        return mdl

    model_results = {name: _load_models(name) for name in models}

    # Find the best fit model by comparing their median durations with the PC scores changepoints
    best_model_info, pca_changepoints = get_best_fit(cp_file, model_results)

    print('Model closest to PC scores:', best_model_info[f'best model - {objective}'])

    # Graph model CP difference(s)
    fig, ax = plot_cp_comparison(model_results, pca_changepoints, plot_all=plot_all, best_model=best_model_info[f'best model - {objective}'])

    # Save the figure
    if output_file is not None:
        legends = [c for c in ax.get_children() if isinstance(c, mpl.legend.Legend)]
        save_fig(fig, output_file, bbox_extra_artists=legends, bbox_inches='tight')

    return best_model_info, fig


def plot_scalar_summary_wrapper(index_file, output_file, groupby='group', colors=None,
                                show_scalars=['velocity_2d_mm', 'velocity_3d_mm',
                                              'height_ave_mm', 'width_mm', 'length_mm']):
    '''
    Creates a scalar summary graph.

    Parameters
    ----------
    index_file (str): path to index file.
    output_file (str): path to save graphs
    groupby (str): scalar_df column to group sessions by when graphing scalar and position summaries
    colors (list): list of colors to serve as the palette in the scalar summary
    show_scalars (list): list of scalar variables to plot.

    Returns
    -------
    scalar_df (pandas DataFrame): df containing scalar data per session uuid.
    '''

    # Get loaded index dict
    _, sorted_index = init_wrapper_function(index_file, output_file=output_file)

    # Parse index dict files to return pandas DataFrame of all computed scalars from extraction step
    scalar_df = scalars_to_dataframe(sorted_index)

    # Plot Scalar Summary with specified groupings and colors
    plt_scalars, _ = scalar_plot(scalar_df, group_var=groupby, show_scalars=show_scalars, colors=colors, headless=True)

    # Save figures
    save_fig(plt_scalars, output_file, suffix='_summary')

    return scalar_df


def plot_syllable_stat_wrapper(model_fit, index_file, output_file, stat='usage', sort=True, count='usage', group=None, max_syllable=40,
                               ordering=None, ctrl_group=None, exp_group=None, colors=None, figsize=(10, 5)):
    '''
    Graph given syllable statistic from a trained AR-HMM model.

    Parameters
    ----------
    model_fit (str): path to trained model file.
    index_file (str): path to index file.
    output_file (str): filename for syllable usage graph.
    stat (str): syllable statistic to plot. It can be any of the scalars (i.e., velocity_2d_mm) in addition
        to: 'usage' and 'duration'
    sort (bool): sort syllables by `count`.
    count (str): method to sort syllables: 'usage' or 'frames'.
    group (tuple, list, None): tuple or list of groups to include in usage plot. (None to graph all groups)
    max_syllable (int): maximum number of syllables to plot.
    ordering (list, range, str, None): order to list syllables. Default is None to graph syllables [0-max_syllable)
        in numerical order. Setting ordering to "diff" will sort syllables based the difference in "stat"
        between ctrl_group and exp_group. "stat" to order syllables by stat values.
    ctrl_group (str): Control group to graph.
    exp_group (str): Experimental group to compare with control group.
    colors (list): list of colors to serve as the sns palette in the scalar summary. If None, default colors are used.
    figsize (tuple): tuple value of length = 2, representing (columns x rows) of the plotted figure dimensions

    Returns
    -------
    fig (pyplot figure): figure to show in Jupyter Notebook.
    '''
    if ordering == 'diff' and any(x is None for x in (ctrl_group, exp_group)):
        raise ValueError('ctrl_group and exp_group must be specified to order by group differences') 

    # Load index file and model data
    _, sorted_index = init_wrapper_function(index_file, output_file=output_file)

    scalar_df = scalars_to_dataframe(sorted_index, model_path=model_fit)

    syll_key = f'labels ({count} sort)'
    features = compute_behavioral_statistics(scalar_df, count=count, syllable_key=syll_key)
    features = features.query('syllable < @max_syllable').copy()

    # Plot and save syllable stat plot
    fig, lgd = plot_syll_stats_with_sem(features, ctrl_group=ctrl_group, exp_group=exp_group, colors=colors, groups=group,
                                        ordering=ordering, stat=stat, max_sylls=max_syllable, figsize=figsize)

    # Save
    save_fig(fig, output_file, bbox_extra_artists=(lgd,), bbox_inches='tight')

    return fig

def plot_mean_group_position_pdf_wrapper(index_file, output_file, normalize=False):
    '''
    Computes the position PDF for each session, averages the PDFs within each group,
    and plots the averaged PDFs.

    Parameters
    ----------
    index_file (str): path to index file.
    output_file (str): filename for the group heatmap graph.
    normalize (bool): normalize the PDF so that min and max values range from 0-1.

    Returns
    -------
    fig (pyplot figure): figure to graph in Jupyter Notebook.
    '''

    # Get loaded index dicts via decorator
    _, sorted_index = init_wrapper_function(index_file, output_file=output_file)

    # Load scalar dataframe to compute position PDF heatmap
    scalar_df = scalars_to_dataframe(sorted_index)

    # Compute Position PDF Heatmaps for all sessions
    pdfs, groups, _, _ = compute_all_pdf_data(scalar_df, normalize=normalize)

    # Plot the average Position PDF Heatmap for each group
    fig = plot_mean_group_heatmap(pdfs, groups)

    # Save figure
    save_fig(fig, output_file, bbox_inches='tight')

    return fig

def plot_verbose_pdfs_wrapper(index_file, output_file, normalize=True):
    '''
    Wrapper function that computes the PDF for the mouse position for each session in the index file.
    Will plot each session's heatmap with a "SessionName: Group"-like title.

    Parameters
    ----------
    index_file (str): path to index file.
    output_file (str): filename for the verbose heatmap graph.
    normalize (bool): normalize the PDF so that min and max values range from 0-1.

    Returns
    -------
    fig (pyplot figure): figure to graph in Jupyter Notebook.
    '''

    # Get loaded index dicts via decorator
    _, sorted_index = init_wrapper_function(index_file, output_file=output_file)

    # Load scalar dataframe to compute position PDF heatmap
    scalar_df = scalars_to_dataframe(sorted_index)

    # Compute PDF Heatmaps for all sessions
    pdfs, groups, sessions, subjectNames = compute_all_pdf_data(scalar_df, normalize=normalize)

    # Plot all session heatmaps in columns organized by groups
    fig = plot_verbose_heatmap(pdfs, sessions, groups, subjectNames)

    # Save figure
    save_fig(fig, output_file, bbox_inches='tight')

    return fig

def plot_transition_graph_wrapper(index_file, model_fit, output_file, config_data):
    '''
    Wrapper function to plot transition graphs.

    Parameters
    ----------
    index_file (str): path to index file
    model_fit (str): path to trained model.
    output_file (str): filename for syllable usage graph.
    config_data (dict): dictionary containing the user specified keys and values

    Returns
    -------
    plt (pyplot figure): graph to show in Jupyter Notebook.
    '''

    # Load index file and model data
    model_data = parse_model_results(model_fit)
    _, sorted_index = init_wrapper_function(index_file, output_file=output_file)

    # Optionally load pygraphviz for transition graph layout configuration
    if 'graphviz' in config_data.get('layout').lower():
        try:
            import pygraphviz
        except ImportError:
            raise ImportError('pygraphviz must be installed to use graphviz layout engines')

    # Get labels and optionally relabel them by usage sorting
    labels = model_data['labels']
    if config_data['sort']:
        labels = relabel_by_usage(labels, count=config_data['count'])[0]

    # Get modeled session uuids to compute group-mean transition graph for
    label_group, _ = get_trans_graph_groups(model_data)
    group = list(set(label_group))

    print('Computing transition matrices...')
    try:
        # Compute and plot Transition Matrices
        plt = compute_and_graph_grouped_TMs(config_data, labels, label_group, group)
    except Exception as e:
        print('Error:', e)
        print('Incorrectly inputted group, plotting all groups.')

        label_group = [f['group'] for f in sorted_index['files'].values()]
        group = list(set(label_group))

        print('Recomputing transition matrices...')
        plt = compute_and_graph_grouped_TMs(config_data, labels, label_group, group)

    # Save figure
    save_fig(plt, output_file)

    return plt

def make_crowd_movies_wrapper(index_file, model_path, output_dir, config_data):
    '''
    Wrapper function to create crowd movie videos and write them to individual
    files depicting respective syllable labels.

    Parameters
    ----------
    index_file (str): path to index file
    model_path (str): path to trained model.
    output_dir (str): directory to store crowd movies in.
    config_data (dict): dictionary conataining all the necessary parameters to generate the crowd movies.
        E.g.: max_syllable: Maximum number of syllables to generate crowd movies for.
              max_example: Maximum number of mouse examples to include in each crowd movie
              specific_syllable: Set to a syllable number to only generate crowd movies of that syllable.
                if value is None, command will generate crowd movies for all syllables with # <= max_syllable.
              separate_by: ['default', 'groups', 'sessions', 'subjects']; If separate_by != 'default', the command
                  will generate a separate crowd movie for each selected grouping per syllable.
                  Resulting in (ngroups * max_syllable) movies.

    Returns
    -------
    cm_paths (dict): Dictionary of syllables and their generated crowd movie paths
    '''

    # Load index file and model data
    model_fit = parse_model_results(model_path)
    _, sorted_index = init_wrapper_function(index_file, output_dir=output_dir)

    # Get list of syllable labels for all sessions
    labels = model_fit['labels']

    # Relabel syllable labels by usage sorting and save the ordering for crowd-movie file naming
    if config_data.get('sort', True):
        labels, ordering = relabel_by_usage(labels, count=config_data.get('count', 'usage'))
    else:
        ordering = list(range(config_data['max_syllable']))

    # get train list uuids if available, otherwise default to 'keys'
    label_uuids = model_fit.get('train_list', model_fit['keys'])
    label_dict = dict(zip(label_uuids, labels))

    # Get uuids found in both the labels and the index
    uuid_set = set(label_uuids) & set(sorted_index['files'])
    # Make sure the files exist 
    uuid_set = [uuid for uuid in uuid_set if exists(sorted_index['files'][uuid]['path'][0])]
    # filter to only include existing UUIDs
    sorted_index['files'] = keyfilter(lambda k: k in uuid_set, sorted_index['files'])
    label_dict = keyfilter(lambda k: k in uuid_set, label_dict)

    labels = list(label_dict.values())
    label_uuids = list(label_dict)

    # Get syllable(s) to create crowd movies of
    if config_data['specific_syllable'] is not None:
        config_data['crowd_syllables'] = [config_data['specific_syllable']]
        config_data['max_syllable'] = 1
    else:
        config_data['crowd_syllables'] = range(config_data['max_syllable'])

    # Write parameter information yaml file in crowd movies directory
    write_crowd_movie_info_file(model_path=model_path, model_fit=model_fit,
                                index_file=index_file, output_dir=output_dir)

    # Ensuring movie separation parameter is found
    separate_by = config_data.get('separate_by', 'default').lower()

    # Optionally generate crowd movies from independent sources, i.e. groups, or individual sessions.
    if separate_by == 'groups':
        # Get the groups to separate the arrays by - use model-assigned groups because index file could
        # be different
        _grp = model_fit['metadata']['groups']
        group_keys = groupby(lambda k: _grp[k], _grp)

        # Write crowd movies for each group
        cm_paths = make_separate_crowd_movies(config_data, sorted_index, group_keys,
                                              label_dict, output_dir, ordering)
    elif separate_by in ('sessions', 'subjects'):
        grouping = 'SessionName'
        if separate_by == 'subjects':
            grouping = 'SubjectName'
        # group UUIDs by grouping
        group_keys = groupby(lambda k: sorted_index['files'][k]['metadata'][grouping], label_uuids)

        # Write crowd movies for each session
        cm_paths = make_separate_crowd_movies(config_data, sorted_index, group_keys,
                                              label_dict, output_dir, ordering)
    else:
        # Write movies using all sessions as the source
        cm_paths = {'all': write_crowd_movies(sorted_index, config_data, ordering, labels, label_uuids, output_dir)}

    return cm_paths

def copy_h5_metadata_to_yaml_wrapper(input_dir):
    '''
    Copy h5 metadata dictionary contents into the respective file's yaml file.

    Parameters
    ----------
    input_dir (str): path to directory that contains h5 files.

    Returns
    -------
    None
    '''

    h5s, dicts, yamls = recursive_find_h5s(input_dir)
    to_load = [(tmp, yml, file) for tmp, yml, file in zip(
        dicts, yamls, h5s) if tmp['complete'] and not tmp['skip']]

    # load in all of the h5 files, grab the extraction metadata, reformat to improve readability
    # then stage the copy
    for _dict, _yml, _h5 in tqdm(to_load, desc='Copying data to yamls'):
        metadata_path = get_metadata_path(_h5)
        _dict['metadata'] = clean_dict(h5_to_dict(_h5, metadata_path))

        # Atomically write updated yaml
        new_file = f'{basename(_yml)}_update.yaml'
        with open(new_file, 'w+') as f:
            yaml.safe_dump(_dict, f)
        shutil.move(new_file, _yml)