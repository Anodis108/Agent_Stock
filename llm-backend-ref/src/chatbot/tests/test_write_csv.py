from __future__ import annotations

import asyncio
import csv
import os
import unittest

from common.utils import get_settings
from src.chatbot.domain.service.write_csv import CSVWriterInput
from src.chatbot.domain.service.write_csv import CSVWriterService


class TestCSVWriter(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = get_settings()
        self.model = CSVWriterService(settings=self.settings)

        # Dummy landmarks and distances
        self.pose_landmarks_list = [
            [
                {'x': 0.5586, 'y': 0.2867, 'z': -0.4227},
                {'x': 0.5733, 'y': 0.2703, 'z': -0.4115},
                {'x': 0.5830, 'y': 0.2696, 'z': -0.4121},
                {'x': 0.5924, 'y': 0.2688, 'z': -0.4119},
                {'x': 0.5570, 'y': 0.2723, 'z': -0.3661},
                {'x': 0.5535, 'y': 0.2730, 'z': -0.3667},
                {'x': 0.5499, 'y': 0.2737, 'z': -0.3670},
                {'x': 0.6205, 'y': 0.2729, 'z': -0.2993},
                {'x': 0.5616, 'y': 0.2794, 'z': -0.0892},
                {'x': 0.5821, 'y': 0.3022, 'z': -0.3746},
                {'x': 0.5599, 'y': 0.3050, 'z': -0.3179},
                {'x': 0.6929, 'y': 0.3739, 'z': -0.3338},
                {'x': 0.5318, 'y': 0.3843, 'z': 0.1600},
                {'x': 0.6918, 'y': 0.4964, 'z': -0.4211},
                {'x': 0.5108, 'y': 0.4961, 'z': 0.2110},
                {'x': 0.6538, 'y': 0.6056, 'z': -0.6017},
                {'x': 0.4943, 'y': 0.5829, 'z': -0.0586},
                {'x': 0.6522, 'y': 0.6440, 'z': -0.6936},
                {'x': 0.4919, 'y': 0.6180, 'z': -0.1179},
                {'x': 0.6261, 'y': 0.6416, 'z': -0.7240},
                {'x': 0.4968, 'y': 0.6158, 'z': -0.1804},
                {'x': 0.6212, 'y': 0.6296, 'z': -0.6149},
                {'x': 0.5032, 'y': 0.6032, 'z': -0.0943},
                {'x': 0.6424, 'y': 0.6118, 'z': -0.1694},
                {'x': 0.5516, 'y': 0.6091, 'z': 0.1692},
                {'x': 0.6469, 'y': 0.7800, 'z': -0.1144},
                {'x': 0.5764, 'y': 0.7626, 'z': 0.3816},
                {'x': 0.6446, 'y': 0.9188, 'z': 0.1971},
                {'x': 0.5966, 'y': 0.8795, 'z': 0.7458},
                {'x': 0.6518, 'y': 0.9326, 'z': 0.2148},
                {'x': 0.6204, 'y': 0.9024, 'z': 0.7743},
                {'x': 0.6166, 'y': 0.9801, 'z': -0.0147},
                {'x': 0.5080, 'y': 0.9112, 'z': 0.6287},
            ],
        ]

        self.distances = [
            [
                2.7044468780412365,
                25.86994921344918,
                31.611666755925693,
                43.256925485231314,
                17.14147394895663,
                3.943363087357334,
                12.760722950688333,
            ],
        ]

        self.height_truth = 170.5
        self.pose_num = 1
        self.pre = [186.6]
        self.px_per_cm = 3.835972520171619

    def test_write_csv_files(self):
        # Tạo input
        inputs = CSVWriterInput(
            pose_num=self.pose_num,
            height_truth=self.height_truth,
            pose_landmarks_list=self.pose_landmarks_list,
            distances=self.distances,
            height_pre=self.pre,
            px_per_cm=self.px_per_cm,
        )

        # Gọi model (phải chạy async)
        output = asyncio.run(self.model.process(inputs=inputs))

        # === Kiểm tra kết quả trả về ===
        self.assertTrue(output.landmarks_csv_written)
        self.assertTrue(output.distances_csv_written)

        # === Kiểm tra file tồn tại ===
        self.assertTrue(
            os.path.exists(
                self.model.settings.write_csv.pose_landmark_path,
            ),
        )
        self.assertTrue(
            os.path.exists(
                self.model.settings.write_csv.distance2D_path,
            ),
        )

        # === Đọc file và kiểm tra nội dung landmarks ===
        print('\n📄 Nội dung pose_landmarks.csv:')
        with open(self.model.settings.write_csv.pose_landmark_path) as f:
            self._extracted_from_test_write_csv_files_34(f)
        # === Đọc file và kiểm tra nội dung distances ===
        print('\n📄 Nội dung distance_2d.csv:')
        with open(self.model.settings.write_csv.distance2D_path) as f:
            self._extracted_from_test_write_csv_files_34(f)

    def _extracted_from_test_write_csv_files_34(self, f):
        rows = list(csv.reader(f))
        self.assertGreater(len(rows), 1)
        for row in rows:
            print(row)


if __name__ == '__main__':
    unittest.main()
