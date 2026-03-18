from __future__ import annotations

from dataclasses import dataclass

import cv2
import mediapipe as mp


@dataclass
class EyeFrameSignals:
    look_away: bool
    both_eyes_detected: bool
    gaze_ratio: float


class EyeMovementMonitor:
    """Simple gaze-direction monitor using FaceMesh eye landmarks."""

    def __init__(self) -> None:
        self._mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def analyze(self, frame_bgr) -> tuple:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        result = self._mesh.process(rgb)

        if not result.multi_face_landmarks:
            return frame_bgr, EyeFrameSignals(look_away=True, both_eyes_detected=False, gaze_ratio=0.0)

        h, w = frame_bgr.shape[:2]
        landmarks = result.multi_face_landmarks[0].landmark

        left_inner = landmarks[133]
        left_outer = landmarks[33]
        right_inner = landmarks[362]
        right_outer = landmarks[263]

        left_x = (left_inner.x + left_outer.x) / 2
        right_x = (right_inner.x + right_outer.x) / 2
        eye_center_x = (left_x + right_x) / 2

        # Ratio around 0.5 is center-facing; extreme values suggest looking aside.
        gaze_ratio = eye_center_x
        look_away = gaze_ratio < 0.36 or gaze_ratio > 0.64

        for idx in [33, 133, 263, 362, 1]:
            pt = landmarks[idx]
            cv2.circle(frame_bgr, (int(pt.x * w), int(pt.y * h)), 2, (0, 255, 0), -1)

        label = "LOOK AWAY" if look_away else "FOCUSED"
        color = (0, 0, 255) if look_away else (0, 200, 0)
        cv2.putText(frame_bgr, label, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)

        return frame_bgr, EyeFrameSignals(look_away=look_away, both_eyes_detected=True, gaze_ratio=gaze_ratio)


def proctoring_risk_level(eye_away_ratio: float, violation_count: int, reading_suspicion: float) -> dict:
    eye_risk = min(100.0, eye_away_ratio * 100.0)
    violation_risk = min(100.0, violation_count * 15.0)
    reading_risk = min(100.0, reading_suspicion)

    risk_score = (0.35 * eye_risk) + (0.30 * violation_risk) + (0.35 * reading_risk)
    integrity_score = max(0.0, 100.0 - risk_score)

    if integrity_score >= 70:
        label = "Low Risk"
    elif integrity_score >= 45:
        label = "Medium Risk"
    else:
        label = "High Risk"

    return {
        "risk_score": round(risk_score, 2),
        "integrity_score": round(integrity_score, 2),
        "label": label,
    }
