import joblib
import numpy as np
from operator import add
from copy import deepcopy
from functools import reduce
from unittest import TestCase
import matplotlib.pyplot as plt
from collections import OrderedDict
from moseq2_viz.util import parse_index, read_yaml
from moseq2_viz.model.util import parse_model_results
from moseq2_viz.model.trans_graph import get_pos, get_trans_graph_groups, \
    get_group_trans_mats, get_transition_matrix, graph_transition_matrix,  get_transitions, make_transition_graphs, \
    make_difference_graphs, draw_graph, normalize_transition_matrix, \
    convert_ebunch_to_graph, convert_transition_matrix_to_ebunch, compute_and_graph_grouped_TMs

def make_sequence(lbls, durs):
    arr = [[x] * y for x, y in zip(lbls, durs)]
    return np.array(reduce(add, arr))

class TestModelTransGraph(TestCase):

    def test_get_trans_graph_groups(self):

        test_model = 'data/test_model.p'

        model = parse_model_results(test_model)

        label_group, label_uuids = get_trans_graph_groups(model)

        assert label_group == ['default', 'default']
        assert label_uuids == ['ae8a9d45-7ad9-4048-963f-ca4931125fcd', '66e77b85-f5fa-4e31-a61c-8952394ff441']

    def test_get_group_trans_mats(self):

        test_model = 'data/test_model.p'

        model = parse_model_results(test_model)

        label_group, _ = get_trans_graph_groups(model)
        group = set(label_group)

        trans_mats, usages = get_group_trans_mats(model['labels'], label_group, group, 20, normalize='bigram')

        assert len(trans_mats) == 1
        assert trans_mats[0].shape == (20, 20)
        assert len(usages) == 1
        assert len(usages[0]) == 20

    def test_compute_and_graph_TMs(self):

        test_model = 'data/test_model.p'
        config_file = 'data/config.yaml'

        config_data = read_yaml(config_file)

        model = parse_model_results(test_model)

        label_group, _ = get_trans_graph_groups(model)
        group = list(set(label_group))

        trans_mats, usages = get_group_trans_mats(model['labels'], label_group, group, 20, normalize='bigram')
        fig, _, _ = graph_transition_matrix(trans_mats,
                                      **config_data,
                                      usages=usages,
                                      groups=group,
                                      headless=True)

        test_fig = compute_and_graph_grouped_TMs(config_data, model['labels'], label_group, group)

        assert type(fig) == type(test_fig)

    def test_get_transitions(self):

        test_model = 'data/test_model.p'
        model = parse_model_results(test_model)

        transitions, locs = get_transitions(model['labels'][0])

        assert len(transitions) == 1
        assert len(locs) == 1

        transitions, locs = get_transitions(model['labels'][1])

        assert len(transitions) == 43
        assert len(locs) == 43

        true_labels = [1, 2, 4, 1, 5]
        durs = [3, 4, 2, 6, 7]
        arr = make_sequence(true_labels, durs)

        trans, locs = get_transitions(arr)

        assert true_labels[1:] == list(trans), 'syllable labels do not match with the transitions'
        assert list(np.diff(locs)) == durs[1:-1], 'syllable locations do not match their durations'

    def test_normalize_matrix(self):

        normalizations = ['bigram', 'rows', 'columns']
        test_model = 'data/test_model.p'

        model = parse_model_results(test_model)
        max_syllable = 20
        smoothing = 0.0

        init_matrix = np.zeros((max_syllable + 1, max_syllable + 1), dtype='float32') + smoothing

        for v in model['labels']:
            # Get syllable transitions
            transitions = get_transitions(v)[0]

            # Populate matrix array with transition data
            for (i, j) in zip(transitions, transitions[1:]):
                if i <= max_syllable and j <= max_syllable:
                    init_matrix[i, j] += 1

        for norm in normalizations:
            normed_mtx = normalize_transition_matrix(deepcopy(init_matrix), norm)
            assert np.any(np.not_equal(init_matrix, normed_mtx))

    def test_get_transition_matrix(self):

        test_model = 'data/test_model.p'

        model = parse_model_results(test_model)
        max_syllable = 20

        trans_mats = get_transition_matrix(model['labels'], max_syllable=max_syllable)

        assert len(trans_mats) == 2
        assert trans_mats[0].shape == (20, 20)

    def test_convert_ebunch_to_graph(self):

        test_model = 'data/test_model.p'

        model = parse_model_results(test_model)
        max_syllable = 20
        edge_threshold = .0025

        tm = get_transition_matrix(model['labels'], max_syllable=max_syllable)[0]

        ebunch = convert_transition_matrix_to_ebunch(
            tm, tm, edge_threshold=edge_threshold, keep_orphans=False,
            max_syllable=tm.shape[0])[0]

        graph = convert_ebunch_to_graph(ebunch)

        assert graph.number_of_nodes() == 0

    def test_convert_transition_matrix_to_ebunch(self):

        test_model = 'data/test_model.p'

        model = parse_model_results(test_model)
        max_syllable = 20
        edge_threshold = .0025

        tm = get_transition_matrix(model['labels'], max_syllable=max_syllable)[0]

        ebunch, orphans = convert_transition_matrix_to_ebunch(tm, tm, keep_orphans=True,
                                                              edge_threshold=edge_threshold,
                                                              max_syllable=max_syllable)

        assert len(ebunch) == 0
        assert len(orphans) == 400

    def test_make_difference_graph(self):

        test_model = 'data/test_model.p'
        edge_threshold = 0.0025

        model = parse_model_results(test_model)

        label_group, _ = get_trans_graph_groups(model)
        group = list(set(label_group))
        group += ['Group2']
        label_group[1] = 'Group2'
        group_names = group.copy()

        trans_mats, usages = get_group_trans_mats(model['labels'], label_group, group, 20, normalize='bigram')

        anchor = 0
        usages_anchor = usages[anchor]

        ebunch_anchor, orphans = convert_transition_matrix_to_ebunch(
            trans_mats[anchor], trans_mats[anchor], edge_threshold=edge_threshold,
            keep_orphans=True, usages=usages_anchor,
            usage_threshold=0, max_syllable=19)

        print(ebunch_anchor, orphans)

        graph_anchor = convert_ebunch_to_graph(ebunch_anchor)
        nnodes = len(graph_anchor.nodes())
        pos = get_pos(graph_anchor, 'circular', nnodes)

        new_usages, new_group_names, new_difference_graphs, _, _, _, _ = \
            make_difference_graphs(trans_mats, usages, group, group_names, {'usages': usages_anchor},
                                   trans_mats, pos, indices=[e[:-1] for e in ebunch_anchor], node_edge_colors=['r'])

        assert len(new_usages) == 3
        assert len(new_group_names) == 3
        assert len(new_difference_graphs) == 1 # no previously generated graphs were passed
        assert new_group_names[-1] == 'Group2 - default'

    def test_make_transition_graphs(self):

        test_model = 'data/test_model.p'
        edge_threshold = 0.0025

        model = parse_model_results(test_model)

        label_group, _ = get_trans_graph_groups(model)
        group = list(set(label_group))
        group += ['Group2']
        label_group[1] = 'Group2'
        group_names = group.copy()

        trans_mats, usages = get_group_trans_mats(model['labels'], label_group, group, 20, normalize='bigram')

        anchor = 0
        usages_anchor = usages[anchor]

        ebunch_anchor, orphans = convert_transition_matrix_to_ebunch(
            trans_mats[anchor], trans_mats[anchor], edge_threshold=edge_threshold,
            keep_orphans=True, usages=usages_anchor,
            usage_threshold=0, max_syllable=19)

        graph_anchor = convert_ebunch_to_graph(ebunch_anchor)
        nnodes = len(graph_anchor.nodes())
        pos = get_pos(graph_anchor, 'circular', nnodes)

        usages, group_names, widths, node_sizes, node_edge_colors, graphs, scalars = \
            make_transition_graphs(trans_mats, usages, group, group_names, {'usages': usages_anchor},
                                   pos, indices=[e[:-1] for e in ebunch_anchor], orphans=orphans, edge_threshold=.0025,
                                   difference_threshold=.0005, orphan_weight=0)

        assert len(usages) == 3
        assert len(group_names) == 3
        assert len(widths) == 3
        assert len(node_sizes) == 3
        assert len(node_edge_colors) == 3
        assert len(graphs) == 3
        assert scalars is None

    def test_get_pos(self):

        test_model = 'data/test_model.p'
        edge_threshold = 0.0025

        model = parse_model_results(test_model)

        label_group, _ = get_trans_graph_groups(model)
        group = set(label_group)

        trans_mats, usages = get_group_trans_mats(model['labels'], label_group, group, 20, normalize='bigram')

        anchor = 0
        usages_anchor = usages[anchor]

        ebunch_anchor, _ = convert_transition_matrix_to_ebunch(
            trans_mats[anchor], trans_mats[anchor],
            edge_threshold=edge_threshold,
            keep_orphans=False, usages=usages_anchor,
            usage_threshold=0, max_syllable=20)

        graph_anchor = convert_ebunch_to_graph(ebunch_anchor)
        nnodes = graph_anchor.number_of_nodes()

        layouts = ['spring', 'circular', 'spectral', usages_anchor]
        for layout in layouts:
            pos = get_pos(graph_anchor, layout, nnodes)
            assert isinstance(pos, dict)
            if isinstance(layout, str):
                assert len(pos.keys()) == nnodes
            else:
                assert len(pos.keys()) == len(usages_anchor.keys())

    def test_draw_graphs(self):
        test_model = 'data/test_model.p'
        width_per_group = 8
        edge_threshold = 0.0025

        model = parse_model_results(test_model)

        label_group, _ = get_trans_graph_groups(model)
        group = list(set(label_group))
        group += ['Group2']
        label_group[1] = 'Group2'
        group_names = group.copy()

        trans_mats, usages = get_group_trans_mats(model['labels'], label_group, group, 20, normalize='bigram')

        anchor = 0
        usages_anchor = usages[anchor]
        ngraphs = len(trans_mats)

        ebunch_anchor, orphans = convert_transition_matrix_to_ebunch(
            trans_mats[anchor], trans_mats[anchor], edge_threshold=edge_threshold,
            keep_orphans=True, usages=usages_anchor,
            usage_threshold=0, max_syllable=20)

        graph_anchor = convert_ebunch_to_graph(ebunch_anchor)
        nnodes = len(graph_anchor.nodes())
        pos = get_pos(graph_anchor, 'circular', nnodes)

        usages, group_names, widths, node_sizes, node_edge_colors, graphs, _ = \
            make_transition_graphs(trans_mats, usages, group, group_names, {'usages': usages_anchor},
                                   pos, orphans, edge_threshold=.0025, indices=[e[:-1] for e in ebunch_anchor], 
                                   difference_threshold=.0005, orphan_weight=0)

        fig, ax = plt.subplots(ngraphs, ngraphs,
                               figsize=(ngraphs * width_per_group,
                                        ngraphs * width_per_group))

        for i, graph in enumerate(graphs):
            if i == ngraphs:
                i = 0
            draw_graph(graph, widths[i], pos, node_color='w',
                       node_size=node_sizes[i], node_edge_colors=node_edge_colors[i],
                       ax=ax[i][i], title=group_names[i])

        assert fig is not None
        assert ax.shape == (2, 2)

    def test_graph_transition_matrix(self):

        test_model = 'data/test_model.p'

        model = parse_model_results(test_model)

        label_group, _ = get_trans_graph_groups(model)
        group = list(set(label_group))

        trans_mats, usages = get_group_trans_mats(model['labels'], label_group, group, 50, normalize='rows')

        fig, ax, pos = graph_transition_matrix(trans_mats, usages=usages, groups=group)

        assert len(pos.keys()) == 4
        assert len(ax) == 1
        assert fig is not None
