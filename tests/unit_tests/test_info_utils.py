import joblib
import numpy as np
from unittest import TestCase
from moseq2_viz.model.util import parse_model_results
from moseq2_viz.info.util import entropy, entropy_rate
from moseq2_viz.model.util import get_syllable_statistics
from moseq2_viz.model.trans_graph import get_transition_matrix


class TestInfoUtils(TestCase):
    
    def test_entropy(self):
        model_fit = 'data/test_model.p'

        model_data = parse_model_results(model_fit)
        labels = model_data['labels']
        truncate_syllable = 40
        smoothing = 1.0

        ent = []
        ents = []
        for v in labels:
            usages = get_syllable_statistics([v])[0]
            assert usages is not None

            syllables = np.array(list(usages.keys()))
            truncate_point = np.where(syllables == truncate_syllable)[0]

            if truncate_point is None or len(truncate_point) != 1:
                truncate_point = len(syllables)
            else:
                truncate_point = truncate_point[0]

            assert truncate_point > 0

            usages = np.array(list(usages.values()), dtype='float')
            usages = usages[:truncate_point] + smoothing
            usages /= usages.sum()

            ent.append(-np.sum(usages * np.log2(usages)))
            ents.append(-(usages * np.log2(usages)))

        test_ent = entropy(labels)

        assert len(test_ent) == 2 # for 2 sessions in modeling

    def test_entropy_rate(self):

        model_fit = 'data/test_model.p'

        model_data = parse_model_results(model_fit)
        labels = model_data['labels']
        truncate_syllable = 40
        smoothing = 1.0
        tm_smoothing = 1.0
        for norm in ['bigram', 'rows', 'columns']:
            tmp = []
            tmp_er = []
            for v in labels:

                usages = get_syllable_statistics([v])[0]
                syllables = np.array(list(usages.keys()))
                truncate_point = np.where(syllables == truncate_syllable)[0]

                if truncate_point is None or len(truncate_point) != 1:
                    truncate_point = len(syllables)
                else:
                    truncate_point = truncate_point[0]

                syllables = syllables[:truncate_point]

                usages = np.array(list(usages.values()), dtype='float')
                usages = usages[:truncate_point] + smoothing
                usages /= usages.sum()
            
                tm = get_transition_matrix([v],
                                            max_syllable=truncate_syllable,
                                            normalize=norm,
                                            smoothing=smoothing,
                                            disable_output=True)[0] + tm_smoothing
                tm = tm[:truncate_point, :truncate_point]

                assert tm.shape == (truncate_point, truncate_point)

                if norm == 'bigram':
                    tm /= tm.sum()
                elif norm == 'rows':
                    tm /= tm.sum(axis=1, keepdims=True)
                elif norm == 'columns':
                    tm /= tm.sum(axis=0, keepdims=True)

                real_er = -np.sum(usages[:, None] * tm * np.log2(tm))
                tmp_er.append(-(usages[:, None] * tm * np.log2(tm)))
                tmp.append(real_er)
            
            test_er = entropy_rate(labels, normalize=norm, truncate_syllable=truncate_syllable, smoothing=smoothing, tm_smoothing=tm_smoothing)

            assert len(test_er) == len(tmp) == 2