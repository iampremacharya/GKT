from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np
from insightface.app import FaceAnalysis


class FaceEngine:
    def __init__(self):
        print("Loading face recognition model...")

        model_root = Path(os.getenv("INSIGHTFACE_ROOT", "/data/insightface"))
        model_root.mkdir(parents=True, exist_ok=True)

        self.app = FaceAnalysis(
            name=os.getenv("INSIGHTFACE_MODEL", "buffalo_l"),
            root=str(model_root),
            providers=["CPUExecutionProvider"],
        )
        self.app.prepare(ctx_id=0, det_size=(640, 640))
        print("Face recognition model loaded.")

    def get_embedding(self, image_path: str):
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("Could not read image.")

        faces = self.app.get(image)
        if len(faces) == 0:
            raise ValueError("No face detected.")
        if len(faces) > 1:
            raise ValueError("Multiple faces detected. Please upload a photo containing one face.")

        embedding = faces[0].normed_embedding
        if embedding is None:
            raise ValueError("Could not generate face embedding.")

        return np.asarray(embedding, dtype=np.float32)


face_engine = FaceEngine()
