# cfg = {
#     'retina': 'retina_s', # ['retina_s', 'retina_m', 'retina_l']
#     'arcface': 'arcface_s', # ['arcface_s', 'arcface_m', 'arcface_l']
#     'landmark': '2d', #  ['2d', '3d']
#     'tracking': False,
#     'data_path': './data',
#     'max_face': 1,
#     'thresh_angle': 15
# }
from __future__ import annotations

import os
from os.path import dirname


# pointer to outside of virtual_fence module
ROOT = dirname(dirname(os.path.abspath(__file__)))

CONFIG_PATH = os.path.join(
    ROOT, 'resources', 'config',
    'config.yaml',
).replace('\\', '/')
