from __future__ import annotations

import json
import os
import unittest

import cv2
from app.height_cal_pred import HeightInput
from app.height_cal_pred import HeightService
from common.utils import get_settings
from fastapi.encoders import jsonable_encoder


class TestHeightService(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = get_settings()
        self.height_service = HeightService(settings=self.settings)
        self.img_path = '/mnt/d/project/DATN/DATN_PhamDangDong/resource/data/data/processed_data/1_DungThang_PhamNgocThach_5_183.jpg'
        self.img_name = os.path.basename(self.img_path)

    def test_process_height_service(self):
        test_image = cv2.imread(self.img_path)
        inputs = HeightInput(
            image=test_image,
            img_name=self.img_path,
        )

        import asyncio
        result = asyncio.run(self.height_service.process(inputs=inputs))

        # Chuyển đổi kết quả thành JSON hợp lệ và in ra
        json_result = jsonable_encoder(result)
        print(json.dumps(json_result, indent=4))


if __name__ == '__main__':
    unittest.main()
