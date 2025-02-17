import os
import shutil
import joblib
import numpy as np
from glob import glob
from unittest import TestCase
from moseq2_viz.util import parse_index, read_yaml
from moseq2_viz.model.util import parse_model_results, relabel_by_usage
from moseq2_viz.io.video import write_crowd_movies, write_frames_preview, write_crowd_movie_info_file


class TestIOVideo(TestCase):

    def test_write_crowd_movie_info_file(self):

        model_path = 'data/test_model.p'
        model_fit = parse_model_results(model_path)
        index_file = 'data/test_index.yaml'
        output_dir = 'data/'

        write_crowd_movie_info_file(model_path, model_fit, index_file, output_dir)

        assert os.path.exists(os.path.join(output_dir, 'info.yaml'))
        os.remove(os.path.join(output_dir, 'info.yaml'))

    def test_write_crowd_movies(self):

        index_file = 'data/test_index.yaml'
        model_path = 'data/test_model.p'
        config_file = 'data/config.yaml'
        output_dir = 'data/crowd_movies/'
        max_syllable = 5

        config_data = read_yaml(config_file)
        config_data['max_syllable'] = max_syllable
        config_data['crowd_syllables'] = range(max_syllable)
        config_data['progress_bar'] = False

        model_fit = parse_model_results(model_path)
        labels = model_fit['labels']

        if 'train_list' in model_fit:
            label_uuids = model_fit['train_list']
        else:
            label_uuids = model_fit['keys']

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        _, sorted_index = parse_index(index_file)

        if config_data['sort']:
            labels, ordering = relabel_by_usage(labels, count=config_data['count'])
        else:
            ordering = list(range(max_syllable))

        write_crowd_movies(sorted_index, config_data, ordering, labels, label_uuids, output_dir)

        assert (os.path.exists(output_dir))
        assert len(glob(os.path.join(output_dir, '*.mp4'))) == max_syllable
        shutil.rmtree(output_dir)

    def test_write_frames_preview(self):

        video_file = 'data/'
        filename = os.path.join(video_file, 'test_data2.avi')
        frames = np.random.randint(0, 256, size=(300, 424, 512), dtype='int16')
        threads = 6
        fps = 30
        pixel_format = 'rgb24'
        codec = 'h264'
        slices=24
        slicecrc=1
        frame_size=None
        depth_min=0
        depth_max=80
        get_cmd=False
        cmap='jet'
        text=None
        text_scale=1
        text_thickness=2
        pipe=None
        close_pipe=True
        progress_bar=True

        out = write_frames_preview(filename, frames, threads, fps, pixel_format, codec, slices, slicecrc,\
                             frame_size, depth_min, depth_max, get_cmd, cmap, text, text_scale, text_thickness,\
                             pipe, close_pipe, progress_bar)

        assert os.path.exists(filename)
        assert out == filename
        os.remove(filename)