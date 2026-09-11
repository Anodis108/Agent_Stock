from __future__ import annotations

import csv
import json
import sys
from functools import cached_property
from pathlib import Path
from typing import List
from typing import Optional

from common.bases import BaseModel
from common.bases import BaseService
from common.logs import get_logger
from common.settings import Settings

sys.path.append(str(Path(__file__).parent.parent))
logger = get_logger(__name__)


class CSVWriterInput(BaseModel):
    """Input data for CSV writing."""
    pose_landmarks_list: Optional[List[List[dict]]] = None
    distances: Optional[List[List[float]]] = None
    pose_num: int           # số thứ tự tương ứng với pose
    height_truth: float     # height thực
    height_pre: List[float]
    px_per_cm: float        # số pixel tương ứng với 1 cm


class CSVWriterOutput(BaseModel):
    """Output status of CSV writing."""
    landmarks_csv_written: bool = False
    distances_csv_written: bool = False


class CSVWriterService(BaseService):
    """Model to write pose landmarks and distances to CSV files."""
    settings: Settings

    @cached_property
    def body_parts(self) -> dict[int, str]:
        """Load body parts mapping from JSON file."""
        with open(self.settings.write_csv.body_parts_path) as f:
            return {int(k): v for k, v in json.load(f).items()}

    async def process(self, inputs: CSVWriterInput) -> CSVWriterOutput:
        """Process input data and write to CSV files."""
        try:
            landmarks_written = False
            distances_written = False

            if inputs.pose_landmarks_list:
                landmarks_written = self._write_pose_landmarks(
                    pose_num=inputs.pose_num,
                    pose_landmarks_list=inputs.pose_landmarks_list,
                    csv_filename=self.settings.write_csv.pose_landmark_path,
                )

            if inputs.distances:
                if self.settings.write_csv.mode == '2D':
                    csv_mode = self.settings.write_csv.distance2D_path
                elif self.settings.write_csv.mode == '3D':
                    csv_mode = self.settings.write_csv.distance3D_path
                else:
                    raise ValueError(
                        f'Chế độ không hợp lệ: {self.settings.write_csv.mode}',
                    )

                distances_written = self._write_distances(
                    pose_num=inputs.pose_num,
                    distances=inputs.distances,
                    csv_filename=csv_mode,
                    height_truth=inputs.height_truth,
                    height_pre=inputs.height_pre,
                    px_per_cm=inputs.px_per_cm,
                )

            return CSVWriterOutput(
                landmarks_csv_written=landmarks_written,
                distances_csv_written=distances_written,
            )
        except Exception as e:
            logger.error(f'CSV writing failed: {str(e)}')
            raise

    def _write_pose_landmarks(
        self,
        pose_num: int,
        pose_landmarks_list: List[List[dict]],
        csv_filename: str,
    ) -> bool:
        """Write pose landmarks to a CSV file."""
        try:
            with open(csv_filename, mode='a', newline='') as csvfile:
                writer = csv.DictWriter(
                    csvfile, fieldnames=[
                        'Pose', 'X', 'Y', 'Z',
                    ],
                )
                if csvfile.tell() == 0:
                    writer.writeheader()

                for person in pose_landmarks_list:
                    for i, landmark in enumerate(person):
                        writer.writerow({
                            'Pose': f'Pose {pose_num} - {self.body_parts.get(i, "Unknown")}',
                            'X': landmark['x'],
                            'Y': landmark['y'],
                            'Z': landmark['z'],
                        })
                    writer.writerow({})  # Empty row between poses
            return True
        except Exception as e:
            logger.error(
                f'Failed to write landmarks to {csv_filename}: {str(e)}',
            )
            return False

    def _write_distances(
        self,
        pose_num: int,
        distances: List[List[float]],
        csv_filename: str,
        height_truth: float,
        height_pre: List[float],
        px_per_cm: float,
    ) -> bool:
        """Write distances and height to a CSV file."""
        try:
            with open(csv_filename, mode='a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                if csvfile.tell() == 0:
                    writer.writerow(
                        ['Pose'] +
                        [f'Distance{i + 1} (cm)' for i in range(len(distances[0]))] +
                        ['Height_Pre (cm)'] +
                        ['px_per_cm'] +
                        ['Height_truth (cm)'],
                    )
                for person, pred_height in zip(distances, height_pre):
                    distances_cm = list(person)
                    writer.writerow([pose_num] + distances_cm +
                                    [pred_height] + [px_per_cm] + [height_truth])
            return True
        except Exception as e:
            logger.error(
                f'Failed to write distances to {csv_filename}: {str(e)}',
            )
            return False
