from __future__ import annotations

import json
import unittest

import requests  # type: ignore
from mediapipe.tasks.python.components.containers.landmark import NormalizedLandmark


class TestHeightPredictorAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.api_url = 'http://localhost:5000/v1/height_pred'
        self.distance = [
            [
                9.933471372616063,57.19990722740044,67.03142189601489,87.5611880572484,32.26543209272624,5.833722614191923
            ]
        ]


    def test_height_pred(self):

        payload = {
            'x': self.distance,
        }

        response = requests.post(self.api_url, json=payload)

        self.assertEqual(
            response.status_code, 200,
            f'Expected status code 200, got {response.status_code}: {response.text}',
        )

        try:
            response_json = response.json()
            print(
                'Response JSON:', json.dumps(
                    response_json, indent=4, ensure_ascii=False,
                ),
            )
        except json.JSONDecodeError:
            self.fail(f'Response is not valid JSON: {response.text}')



if __name__ == '__main__':
    unittest.main()
