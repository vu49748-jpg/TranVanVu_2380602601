"""Face challenge validation tests; stubbed inference is explicit in these tests.

Model loading and real inference have a separate opt-in smoke test. These tests
do not claim to measure population accuracy or certified presentation attacks.
"""
import hashlib
import io
import math
from pathlib import Path

import pytest

from app import face_engine as faces, face_models as assets


STEPS = ['front', 'turn_left', 'turn_right', 'front']
CAPTURES = [b'captured-frame-' + bytes([i]) for i in range(4)]


def vector(index=0):
    return [1.0 if i == index else 0.0 for i in range(128)]


def observations(yaws=(0.0, 0.18, -0.18, 0.01), features=None):
    return [faces._Observation(feature, yaw) for feature, yaw in zip(features or [vector()] * 4, yaws)]


def test_live_order_and_identity_are_checked_after_mocked_inference(monkeypatch):
    monkeypatch.setattr(faces, '_read_sequence', lambda images: observations())
    references = faces.enroll_faces(CAPTURES, STEPS)
    assert len(references) == 4
    assert all(len(item) == 128 for item in references)
    assert faces.verify_faces(CAPTURES, STEPS, references) == pytest.approx(1.0)
    with pytest.raises(faces.FaceCheckError) as mismatch:
        faces.verify_faces(CAPTURES, STEPS, [vector(1)] * 4)
    assert mismatch.value.reason == 'identity'


def test_same_face_without_head_movement_cannot_pass(monkeypatch):
    monkeypatch.setattr(faces, '_read_sequence', lambda images: observations((0.0, 0.01, -0.01, 0.0)))
    with pytest.raises(faces.FaceCheckError) as rejected:
        faces.enroll_faces(CAPTURES, STEPS)
    assert rejected.value.reason == 'pose'


def test_randomized_head_turn_order_and_direction_are_enforced(monkeypatch):
    monkeypatch.setattr(faces, '_read_sequence', lambda images: observations())
    with pytest.raises(faces.FaceCheckError):
        faces.enroll_faces(CAPTURES, ['front', 'turn_right', 'turn_left', 'front'])
    monkeypatch.setattr(faces, '_read_sequence', lambda images: observations((0.0, -0.18, 0.18, 0.0)))
    assert len(faces.enroll_faces(CAPTURES, ['front', 'turn_right', 'turn_left', 'front'])) == 4


def test_repeated_bytes_and_malformed_challenge_fail_before_inference(monkeypatch):
    monkeypatch.setattr(faces, '_read_sequence', lambda images: pytest.fail('Invalid capture must not start inference.'))
    for images, steps in [
        ([b'same-image'] * 4, STEPS),
        (CAPTURES[:3], STEPS),
        (CAPTURES, ['front', 'turn_left', 'turn_left', 'front']),
        (CAPTURES, ['turn_left', 'front', 'turn_right', 'front']),
        ([b'x' * (faces.MAX_FRAME_BYTES + 1), *CAPTURES[1:]], STEPS),
    ]:
        with pytest.raises(faces.FaceCheckError):
            faces.enroll_faces(images, steps)


def test_mixed_people_and_corrupt_encrypted_template_plaintext_are_rejected(monkeypatch):
    monkeypatch.setattr(faces, '_read_sequence', lambda images: observations(features=[vector(), vector(), vector(1), vector()]))
    with pytest.raises(faces.FaceCheckError) as different_person:
        faces.enroll_faces(CAPTURES, STEPS)
    assert different_person.value.reason == 'identity'
    for bad in [[], [vector()] * 3, [[0.0] * 128] * 4, [[float('nan')] * 128] * 4, [[1.0] * 127] * 4]:
        with pytest.raises(faces.FaceCheckError):
            faces.verify_faces(CAPTURES, STEPS, bad)


def test_busy_engine_rejects_without_allocating_another_inference(monkeypatch):
    monkeypatch.setattr(faces, '_read_sequence', lambda images: pytest.fail('Busy service must not start another inference.'))
    assert faces._slot.acquire(blocking=False)
    try:
        with pytest.raises(faces.FaceEngineUnavailable):
            faces.enroll_faces(CAPTURES, STEPS)
    finally:
        faces._slot.release()


def test_turn_measurement_ignores_flat_photo_translation_scale_and_roll():
    row = [10, 10, 160, 180, 60, 70, 140, 70, 100, 115, 70, 155, 130, 155, .99]
    baseline = faces._landmark_yaw(row)
    angle = math.radians(20)
    moved = row.copy()
    for index in range(4, 14, 2):
        x, y = row[index], row[index + 1]
        moved[index] = 2 * (x * math.cos(angle) - y * math.sin(angle)) + 90
        moved[index + 1] = 2 * (x * math.sin(angle) + y * math.cos(angle)) - 30
    assert faces._landmark_yaw(moved) == pytest.approx(baseline, abs=1e-8)
    # A horizontal turn changes the nose relative to the eyes, unlike flat roll.
    turned = row.copy()
    turned[8] += 16
    assert faces._landmark_yaw(turned) - baseline == pytest.approx(.20)


def make_jpeg(size=(320, 320), *, color=(128, 128, 128)):
    image = pytest.importorskip('PIL.Image')
    output = io.BytesIO()
    image.new('RGB', size, color).save(output, format='JPEG')
    return output.getvalue()


def test_decode_bounds_format_and_orientation_are_checked_before_dnn():
    pytest.importorskip('numpy')
    image = pytest.importorskip('PIL.Image')
    decoded = faces._decode_jpeg(make_jpeg())
    assert decoded.shape == (320, 320, 3)
    for payload in [b'not-a-jpeg', make_jpeg((64, 64)), make_jpeg((1600, 1600)), b'x' * (faces.MAX_FRAME_BYTES + 1)]:
        with pytest.raises(faces.FaceCheckError):
            faces._decode_jpeg(payload)
    png = io.BytesIO()
    image.new('RGB', (320, 320)).save(png, format='PNG')
    with pytest.raises(faces.FaceCheckError):
        faces._decode_jpeg(png.getvalue())
    jpeg = io.BytesIO()
    exif = image.Exif()
    exif[274] = 6
    image.new('RGB', (320, 200)).save(jpeg, format='JPEG', exif=exif)
    assert faces._decode_jpeg(jpeg.getvalue()).shape == (320, 200, 3)


def test_missing_models_fail_closed(monkeypatch, tmp_path):
    monkeypatch.setenv('FACE_MODEL_DIR', str(tmp_path))
    monkeypatch.setattr(faces, '_initialization_failed', False)
    assert not faces.face_ready()
    with pytest.raises(faces.FaceEngineUnavailable):
        faces._Engine()


def test_only_one_face_is_permitted(monkeypatch):
    np = pytest.importorskip('numpy')
    cv2 = pytest.importorskip('cv2')
    engine = faces._Engine.__new__(faces._Engine)
    engine.cv2 = cv2
    engine.recognizer = None  # Any use before rejecting the detection count fails.
    monkeypatch.setattr(faces, '_decode_jpeg', lambda data: np.zeros((320, 320, 3), dtype=np.uint8))

    class Detector:
        def __init__(self, result):
            self.result = result

        def setInputSize(self, size):
            pass

        def detect(self, image):
            return 1, self.result

    for result in [None, np.zeros((2, 15), dtype=np.float32)]:
        engine.detector = Detector(result)
        with pytest.raises(faces.FaceCheckError):
            engine.observe(b'mocked-capture')


def test_asset_download_is_atomic_and_refuses_corruption(monkeypatch, tmp_path):
    first, second = b'approved-yunet', b'approved-sface'
    model_specs = tuple(assets.ModelAsset(name, 'test', hashlib.sha256(body).hexdigest(), len(body))
                        for name, body in [('yunet.onnx', first), ('sface.onnx', second)])
    monkeypatch.setattr(assets, 'MODELS', model_specs)
    monkeypatch.setattr(assets, '_verified', {})
    bodies = {spec.url: body for spec, body in zip(model_specs, [first, second])}

    class Reply(io.BytesIO):
        def __init__(self, body):
            super().__init__(body)
            self.headers = {}

    monkeypatch.setattr(assets.urllib.request, 'urlopen', lambda request, timeout: Reply(bodies[request.full_url]))
    assert assets.verified_model_paths(tmp_path) is None
    paths = assets.download_models(tmp_path)
    assert paths[0].read_bytes() == first and paths[1].read_bytes() == second
    # Same-size mutation must invalidate the cached integrity decision.
    paths[1].write_bytes(b'x' * len(second))
    assert assets.verified_model_paths(tmp_path) is None
    bodies[model_specs[1].url] = b'bad upstream model'
    with pytest.raises(assets.ModelDownloadError):
        assets.download_models(tmp_path)
    assert paths[0].read_bytes() == first
    assert paths[1].read_bytes() == b'x' * len(second)
    assert not list(tmp_path.glob('*.part'))


def test_download_refuses_declared_wrong_length_without_replacing_file(monkeypatch, tmp_path):
    spec = assets.ModelAsset('safe.onnx', 'test', hashlib.sha256(b'model').hexdigest(), 5)
    monkeypatch.setattr(assets, 'MODELS', (spec,))
    existing = tmp_path / spec.filename
    existing.write_bytes(b'old')

    class Reply(io.BytesIO):
        headers = {'Content-Length': '9999999'}

    monkeypatch.setattr(assets.urllib.request, 'urlopen', lambda request, timeout: Reply(b'danger'))
    with pytest.raises(assets.ModelDownloadError):
        assets.download_models(tmp_path)
    assert existing.read_bytes() == b'old'
