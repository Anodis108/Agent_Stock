from __future__ import annotations

import os
import unittest
from pathlib import Path

import cv2
import numpy as np
from common.utils import get_settings
from src.chatbot.domain.service.draw import VisualizationInput
from src.chatbot.domain.service.draw import VisualizationService


class TestVisualizationService(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = get_settings()
        self.visualizer = VisualizationService(settings=self.settings)

        # Đường dẫn ảnh mẫu
        self.image_path = '/mnt/d/project/DATN/DATN_PhamDangDong/resource/data/data/processed_data/1_DungThang_PhamNgocThach_5_183.jpg'
        self.image = cv2.imread(self.image_path)
        self.name_image = Path(self.image_path).stem

        # Dummy pose landmarks: 1 người với 3 điểm
        self.pose_landmarks_list = [
            [
                {'x': 0.7133, 'y': 0.2103, 'z': -0.4058},
                {'x': 0.7234, 'y': 0.1976, 'z': -0.3746},
                {'x': 0.7291, 'y': 0.1979, 'z': -0.3752},
                {'x': 0.7358, 'y': 0.1988, 'z': -0.3752},
                {'x': 0.6991, 'y': 0.1991, 'z': -0.3840},
                {'x': 0.6913, 'y': 0.2006, 'z': -0.3845},
                {'x': 0.6837, 'y': 0.2024, 'z': -0.3848},
                {'x': 0.7393, 'y': 0.2075, 'z': -0.1949},
                {'x': 0.6728, 'y': 0.2117, 'z': -0.2359},
                {'x': 0.7256, 'y': 0.2264, 'z': -0.3345},
                {'x': 0.7000, 'y': 0.2278, 'z': -0.3495},
                {'x': 0.7887, 'y': 0.3087, 'z': -0.0805},
                {'x': 0.6139, 'y': 0.3098, 'z': -0.1457},
                {'x': 0.7956, 'y': 0.4091, 'z': -0.0202},
                {'x': 0.6001, 'y': 0.4140, 'z': -0.1322},
                {'x': 0.8077, 'y': 0.4945, 'z': -0.1823},
                {'x': 0.6031, 'y': 0.4980, 'z': -0.2637},
                {'x': 0.8089, 'y': 0.5255, 'z': -0.2272},
                {'x': 0.5959, 'y': 0.5272, 'z': -0.3176},
                {'x': 0.8000, 'y': 0.5264, 'z': -0.2812},
                {'x': 0.6110, 'y': 0.5267, 'z': -0.3628},
                {'x': 0.7946, 'y': 0.5178, 'z': -0.2060},
                {'x': 0.6206, 'y': 0.5172, 'z': -0.2859},
                {'x': 0.7472, 'y': 0.5128, 'z': 0.0256},
                {'x': 0.6474, 'y': 0.5145, 'z': -0.0260},
                {'x': 0.7480, 'y': 0.6533, 'z': 0.1863},
                {'x': 0.6406, 'y': 0.6531, 'z': 0.1110},
                {'x': 0.7436, 'y': 0.7730, 'z': 0.4757},
                {'x': 0.6534, 'y': 0.7720, 'z': 0.3723},
                {'x': 0.7256, 'y': 0.7893, 'z': 0.4928},
                {'x': 0.6628, 'y': 0.7844, 'z': 0.3897},
                {'x': 0.7793, 'y': 0.8298, 'z': 0.3125},
                {'x': 0.6497, 'y': 0.8272, 'z': 0.2023},
            ],
        ]

        # Dummy bounding box (1 box) và confidence
        self.bboxes = np.array([[
            66.75531768798828, 103.9848861694336,
            87.47063446044922, 134.87550354003906,
        ]])  # x1, y1, x2, y2
        self.confidences = np.array([0.5930715203285217])

    def test_visualization_and_save(self):
        inputs = VisualizationInput(
            image=self.image,
            name_image=self.name_image,
            pose_landmarks_list=self.pose_landmarks_list,
            height_cm=[172.5],
            bboxes=self.bboxes,
            confidences=self.confidences,
        )
        result = self.visualizer.process(inputs=inputs)

        # === Kiểm tra kết quả ===
        self.assertIsNotNone(result.annotated_image)
        self.assertEqual(result.annotated_image.shape, self.image.shape)
        self.assertTrue(os.path.exists(result.output_path))
        print(f'✅ Saved to: {result.output_path}')


if __name__ == '__main__':
    unittest.main()
