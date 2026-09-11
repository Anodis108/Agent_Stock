from __future__ import annotations

import json
import unittest

import cv2
from common.utils import get_settings
from fastapi.encoders import jsonable_encoder
from infrastructure.pose_detector import PoseDetector
from infrastructure.pose_detector import PoseDetectorInput


class TestPoseDetector(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = get_settings()
        self.pose_detector = PoseDetector(settings=self.settings)
        self.img_path = '/mnt/d/project/DATN/DATN_PhamDangDong/resource/data/data/processed_data/1_DungThang_PhamNgocThach_5_183.jpg'

    def test_api_pose_detection(self):
        test_image = cv2.imread(self.img_path)
        print('Image shape:', test_image.shape, 'dtype:', test_image.dtype)

        inputs = PoseDetectorInput(img_origin=test_image)
        result = self.pose_detector.process(inputs=inputs)

        # Chuyển đổi result thành JSON hợp lệ
        json_result = jsonable_encoder(result)

        # Chuyển đổi thành chuỗi JSON và in ra
        print(json.dumps(json_result, indent=4))


if __name__ == '__main__':
    unittest.main()
