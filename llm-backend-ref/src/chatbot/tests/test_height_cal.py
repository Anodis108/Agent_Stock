from __future__ import annotations

import json
import unittest

import requests  # type: ignore
from mediapipe.tasks.python.components.containers.landmark import NormalizedLandmark


class TestHeightCalculatorAPI(unittest.TestCase):
    def setUp(self) -> None:
        """Cài đặt ban đầu"""
        self.api_url = 'http://localhost:5000/v1/height_cal'
        self.landmarks = [[
            NormalizedLandmark(
                x=0.55864018201828,
                y=0.28672096133232117, z=-0.42271214723587036,
            ),
            NormalizedLandmark(
                x=0.573281466960907,
                y=0.27034008502960205, z=-0.4114663004875183,
            ),
            NormalizedLandmark(
                x=0.5829789042472839,
                y=0.2695760428905487, z=-0.41205695271492004,
            ),
            NormalizedLandmark(
                x=0.5924376845359802,
                y=0.26882851123809814, z=-0.41193050146102905,
            ),
            NormalizedLandmark(
                x=0.5569609999656677,
                y=0.27227991819381714, z=-0.36614716053009033,
            ),
            NormalizedLandmark(
                x=0.553490400314331,
                y=0.2729531526565552, z=-0.3667007386684418,
            ),
            NormalizedLandmark(
                x=0.5499429702758789,
                y=0.27366429567337036, z=-0.3669990301132202,
            ),
            NormalizedLandmark(
                x=0.6205288767814636,
                y=0.272909939289093, z=-0.29933154582977295,
            ),
            NormalizedLandmark(
                x=0.5616442561149597,
                y=0.2794104218482971, z=-0.08924071490764618,
            ),
            NormalizedLandmark(
                x=0.5821019411087036,
                y=0.302212119102478, z=-0.3745553195476532,
            ),
            NormalizedLandmark(
                x=0.5599366426467896,
                y=0.30495017766952515, z=-0.3179229497909546,
            ),
            NormalizedLandmark(
                x=0.6929395794868469,
                y=0.3739490807056427, z=-0.3338164985179901,
            ),
            NormalizedLandmark(
                x=0.5317705273628235,
                y=0.38431963324546814, z=0.1599603146314621,
            ),
            NormalizedLandmark(
                x=0.6917884349822998,
                y=0.49635210633277893, z=-0.42108044028282166,
            ),
            NormalizedLandmark(
                x=0.5108474493026733,
                y=0.4960823059082031, z=0.2109968066215515,
            ),
            NormalizedLandmark(
                x=0.6538233757019043,
                y=0.6055673360824585, z=-0.6016507744789124,
            ),
            NormalizedLandmark(
                x=0.4943258762359619,
                y=0.58290034532547, z=-0.058593202382326126,
            ),
            NormalizedLandmark(
                x=0.6522201299667358,
                y=0.6439625024795532, z=-0.6935945153236389,
            ),
            NormalizedLandmark(
                x=0.4919459819793701,
                y=0.6180101037025452, z=-0.11793511360883713,
            ),
            NormalizedLandmark(
                x=0.6260724067687988,
                y=0.6415970325469971, z=-0.7239707708358765,
            ),
            NormalizedLandmark(
                x=0.49684688448905945,
                y=0.6158407926559448, z=-0.1804465502500534,
            ),
            NormalizedLandmark(
                x=0.6211699843406677,
                y=0.6295547485351562, z=-0.6148515343666077,
            ),
            NormalizedLandmark(
                x=0.5032134652137756,
                y=0.603217601776123, z=-0.09428758919239044,
            ),
            NormalizedLandmark(
                x=0.6423527598381042,
                y=0.6118481159210205, z=-0.16938163340091705,
            ),
            NormalizedLandmark(
                x=0.5516496896743774,
                y=0.6091470122337341, z=0.16916398704051971,
            ),
            NormalizedLandmark(
                x=0.6469278931617737,
                y=0.7799736261367798, z=-0.11441945284605026,
            ),
            NormalizedLandmark(
                x=0.5763688087463379,
                y=0.7626259922981262, z=0.3816165626049042,
            ),
            NormalizedLandmark(
                x=0.6446341276168823,
                y=0.918790340423584, z=0.197114959359169,
            ),
            NormalizedLandmark(
                x=0.5966443419456482,
                y=0.8795374035835266, z=0.7457952499389648,
            ),
            NormalizedLandmark(
                x=0.6518265604972839,
                y=0.9326217770576477, z=0.21476362645626068,
            ),
            NormalizedLandmark(
                x=0.6203647255897522,
                y=0.9024173617362976, z=0.7743319272994995,
            ),
            NormalizedLandmark(
                x=0.6165841221809387,
                y=0.9801462292671204, z=-0.014705762267112732,
            ),
            NormalizedLandmark(
                x=0.5079806447029114,
                y=0.9112303853034973, z=0.6286630630493164,
            ),
        ]]
        self.img_width = 259.0
        self.img_height = 194.0
        self.px_per_cm = 1.0443975730020492

    def test_height_cal_input_output(self):
        """Test Height Calculator API input và output"""
        # Chuyển NormalizedLandmark thành dictionary
        serialized_landmarks = [
            [
                {'x': lm.x, 'y': lm.y, 'z': lm.z} for lm in landmarks
            ] for landmarks in self.landmarks
        ]

        payload = {
            'landmarks': serialized_landmarks,
            'img_width': self.img_width,
            'img_height': self.img_height,
            'px_per_cm': self.px_per_cm,
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

        self.assertIn(
            'message', response_json,
            "Missing 'message' in response",
        )
        self.assertEqual(
            response_json['message'], 'Process successfully !!!',
            "Expected 'Process successfully !!!' message",
        )
        self.assertIn('info', response_json, "Missing 'info' in response")

        info = response_json['info']
        for field in ['heights', 'distances', 'cm_direct', 'cm_sum', 'diffs']:
            self.assertIn(field, info, f"Missing '{field}' in info")
            self.assertIsInstance(
                info[field], list, f"'{field}' is not a list",
            )

        self.assertGreaterEqual(
            len(info['heights']), 1, "'heights' list is empty",
        )
        for field in ['distances', 'cm_direct', 'cm_sum', 'diffs']:
            self.assertEqual(
                len(info[field]), len(
                    info['heights'],
                ), f"'{field}' length does not match 'heights'",
            )


if __name__ == '__main__':
    unittest.main()
