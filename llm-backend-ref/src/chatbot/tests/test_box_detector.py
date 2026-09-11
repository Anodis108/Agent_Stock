from __future__ import annotations

import unittest

import cv2
from common.utils import get_settings
from fastapi.encoders import jsonable_encoder
from infrastructure.box_detector import BoxDetector
from infrastructure.box_detector import BoxDetectorInput


class TestBoxDetector(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = get_settings()
        self.box_detector = BoxDetector(settings=self.settings)
        self.img_path = '/mnt/d/project/DATN/DATN_PhamDangDong/resource/data/data_test/z6194149941298_733dfe9d1f76e5f775c0f9336c4b3f3e.jpg'

    def test_api_box_detection(self):
        test_image = cv2.imread(self.img_path)
        print(
            'Image shape:', test_image,
            'dtype:', test_image.dtype,
        )

        inputs = BoxDetectorInput(image=test_image)
        result = self.box_detector.process(inputs=inputs)
        print(jsonable_encoder(result))

        # Kiểm tra kết quả trả về (có thể là bboxes và scores)
        self.assertIn('bboxes', result.model_dump())
        self.assertIn('scores', result.model_dump())

        self.assertIsInstance(result.bboxes, list)
        self.assertIsInstance(result.scores, list)

        # Kiểm tra kiểu dữ liệu của scores (phải là danh sách số thực)
        for score in result.scores:
            self.assertIsInstance(score, float)


if __name__ == '__main__':
    unittest.main()
