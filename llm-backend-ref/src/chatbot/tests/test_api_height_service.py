from __future__ import annotations

import json  # Định dạng JSON kết quả
import os
import unittest

import requests  # type: ignore


class TestHeightAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.image_path = '/mnt/d/project/DATN/DATN_PhamDangDong/resource/data/data/processed_data/1_DungThang_PhamNgocThach_5_183.jpg'
        self.api_url = 'http://localhost:5001/v1/height'  # Chỉnh lại nếu port khác

        if not os.path.exists(self.image_path):
            raise FileNotFoundError(f'Image not found: {self.image_path}')

    def test_height_prediction_api(self):
        with open(self.image_path, 'rb') as img_file:
            files = {
                'file': ('/1_DungThang_PhamNgocThach_5_183.jpg', img_file, 'image/jpeg'),
            }
            response = requests.post(self.api_url, files=files)

        print('Status Code:', response.status_code)

        # In kết quả JSON ra theo định dạng đẹp
        print('Response JSON:')
        print(json.dumps(response.json(), indent=4, ensure_ascii=False))

        # Kiểm tra HTTP 200 và dữ liệu trả về
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
