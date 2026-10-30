"""One-to-one face verification and an active head-turn capture check.

YuNet supplies a face and five landmarks. SFace supplies a 128-dimensional
recognition descriptor; merely detecting a face is never treated as a login.
Only descriptors leave this module. JPEGs are decoded in RAM and never saved.

The four captures reduce simple still-photo use, but are not certified 3-D
presentation-attack detection. A compromised client or replayed video remains a
limitation; this module must be used with the server's signed device challenge.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
import io
import math
import threading
from typing import Sequence

from .face_models import verified_model_paths


MAX_FRAME_BYTES = 768 * 1024
MAX_IMAGE_PIXELS = 2_073_600
EMBEDDING_DIMENSIONS = 128
COSINE_MATCH_THRESHOLD = 0.50
CONSISTENCY_THRESHOLD = 0.40
FRONT_CONSISTENCY_THRESHOLD = 0.55
MIN_YAW_DELTA = 0.12
MAX_FRONT_YAW = 0.20
MAX_FRONT_DRIFT = 0.10
MIN_TURN_SPAN = 0.26


class FaceCheckError(ValueError):
    def __init__(self, message: str, reason: str = 'capture'):
        super().__init__(message)
        self.message = message
        self.reason = reason


class FaceEngineUnavailable(FileNotFoundError):
    def __init__(self, message: str = 'Máy chủ nhận diện đang chưa sẵn sàng. Hãy dùng mật khẩu và OTP.'):
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class _Observation:
    feature: list[float]
    yaw: float


_slot = threading.Semaphore(1)
_engine = None
_initialization_failed = False


def face_ready() -> bool:
    """Lightweight asset/dependency readiness, without allocating a DNN per poll."""
    if _initialization_failed:
        return False
    try:
        return all(importlib.util.find_spec(module) is not None for module in ('cv2', 'numpy', 'PIL')) and verified_model_paths() is not None
    except (ImportError, OSError, ValueError):
        return False


def _normalise(values: Sequence[float], *, reason: str = 'capture') -> list[float]:
    if not isinstance(values, (list, tuple)) or len(values) != EMBEDDING_DIMENSIONS:
        raise FaceCheckError('Không đọc được mẫu nhận diện. Hãy đăng ký lại khuôn mặt bằng mật khẩu và OTP.', reason)
    try:
        numbers = [float(value) for value in values]
    except (TypeError, ValueError):
        raise FaceCheckError('Mẫu nhận diện không hợp lệ.', reason) from None
    if not all(math.isfinite(value) for value in numbers):
        raise FaceCheckError('Mẫu nhận diện không hợp lệ.', reason)
    norm = math.sqrt(sum(value * value for value in numbers))
    if norm < 1e-8 or not math.isfinite(norm):
        raise FaceCheckError('Mẫu nhận diện không hợp lệ.', reason)
    return [value / norm for value in numbers]


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _validate_inputs(images: Sequence[bytes], steps: Sequence[str]) -> None:
    if not isinstance(images, (list, tuple)) or len(images) != 4:
        raise FaceCheckError('Cần chụp đủ bốn bước theo hướng dẫn trên màn hình.')
    if not isinstance(steps, (list, tuple)) or len(steps) != 4 or steps[0] != 'front' or steps[-1] != 'front' or set(steps[1:3]) != {'turn_left', 'turn_right'}:
        raise FaceCheckError('Phiên chụp không hợp lệ. Hãy bắt đầu lại.')
    if any(not isinstance(image, bytes) or not image or len(image) > MAX_FRAME_BYTES for image in images):
        raise FaceCheckError('Ảnh chưa hợp lệ hoặc vượt kích thước cho phép. Hãy chụp lại trong ứng dụng.')
    if len({hashlib.sha256(image).digest() for image in images}) != 4:
        raise FaceCheckError('Các bước phải dùng ảnh chụp mới. Hãy làm theo hướng quay đầu.', 'pose')


def _decode_jpeg(data: bytes):
    """Check format/dimensions before allocation, then apply orientation metadata."""
    if not isinstance(data, bytes) or not data or len(data) > MAX_FRAME_BYTES:
        raise FaceCheckError('Ảnh chưa hợp lệ hoặc vượt kích thước cho phép.')
    try:
        import numpy as np
        from PIL import Image, ImageOps, UnidentifiedImageError
    except ImportError:
        raise FaceEngineUnavailable() from None
    try:
        with Image.open(io.BytesIO(data)) as picture:
            width, height = picture.size
            if picture.format != 'JPEG' or width * height > MAX_IMAGE_PIXELS or min(width, height) < 160:
                raise FaceCheckError('Ảnh cần là JPEG rõ nét, ít nhất 160 px và không quá 2 megapixel.')
            picture.load()
            upright = ImageOps.exif_transpose(picture).convert('RGB')
            # Copy because the Pillow object is closed on leaving this block.
            return np.array(upright, dtype=np.uint8, copy=True)[:, :, ::-1].copy()
    except FaceCheckError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise FaceCheckError('Không đọc được ảnh camera. Hãy chụp lại trong ánh sáng tốt.') from None


def _landmark_yaw(row: Sequence[float]) -> float:
    """Nose displacement in the eye-line coordinate system, invariant to roll.

    Images must be unmirrored. A person turning to THEIR left moves the nose
    towards image +X, while a right turn moves it towards image -X. Camera
    preview may be mirrored; uploaded JPEG bytes must retain sensor orientation.
    """
    left, right = sorted(((float(row[4]), float(row[5])), (float(row[6]), float(row[7]))))
    dx, dy = right[0] - left[0], right[1] - left[1]
    distance_squared = dx * dx + dy * dy
    if distance_squared < 30 * 30 or dx <= 0 or abs(dy) > dx * 0.70:
        raise FaceCheckError('Giữ điện thoại thẳng và để hai mắt rõ trong khung.')
    nx = float(row[8]) - (left[0] + right[0]) / 2
    ny = float(row[9]) - (left[1] + right[1]) / 2
    return (nx * dx + ny * dy) / distance_squared


class _Engine:
    def __init__(self):
        paths = verified_model_paths()
        if paths is None:
            raise FaceEngineUnavailable()
        try:
            import cv2
            self.cv2 = cv2
            cv2.setNumThreads(1)
            cv2.ocl.setUseOpenCL(False)
            self.detector = cv2.FaceDetectorYN.create(str(paths[0]), '', (320, 320), 0.90, 0.30, 5000,
                                                    cv2.dnn.DNN_BACKEND_OPENCV, cv2.dnn.DNN_TARGET_CPU)
            self.recognizer = cv2.FaceRecognizerSF.create(str(paths[1]), '', cv2.dnn.DNN_BACKEND_OPENCV, cv2.dnn.DNN_TARGET_CPU)
        except (ImportError, OSError, RuntimeError, AttributeError):
            raise FaceEngineUnavailable() from None
        except Exception:
            # OpenCV exceptions can include file paths; never expose those details.
            raise FaceEngineUnavailable() from None

    def observe(self, data: bytes) -> _Observation:
        import numpy as np
        cv2 = self.cv2
        image = _decode_jpeg(data)
        height, width = image.shape[:2]
        factor = min(1.0, 640.0 / max(width, height))
        detection_image = cv2.resize(image, (round(width * factor), round(height * factor))) if factor < 1 else image
        resized_height, resized_width = detection_image.shape[:2]
        padded_width = (resized_width + 31) // 32 * 32
        padded_height = (resized_height + 31) // 32 * 32
        detection_image = cv2.copyMakeBorder(detection_image, 0, padded_height - resized_height, 0, padded_width - resized_width, cv2.BORDER_CONSTANT)
        try:
            self.detector.setInputSize((padded_width, padded_height))
            _, faces = self.detector.detect(detection_image)
            if faces is None or len(faces) == 0:
                raise FaceCheckError('Chưa thấy rõ khuôn mặt. Đưa mặt vào khung và chụp lại.')
            if len(faces) != 1:
                raise FaceCheckError('Chỉ để một người trong khung hình khi xác thực.')
            row = np.asarray(faces[0], dtype=np.float32).copy()
            row[:14] /= factor
            if len(row) != 15 or not np.isfinite(row).all():
                raise FaceCheckError('Không đọc được các điểm khuôn mặt. Hãy chụp lại.')
            x, y, box_width, box_height = (float(value) for value in row[:4])
            if min(box_width, box_height) < 96 or box_width * box_height < width * height * 0.04:
                raise FaceCheckError('Đưa điện thoại gần hơn để khuôn mặt rõ trong khung.')
            if x < -width * 0.02 or y < -height * 0.02 or x + box_width > width * 1.02 or y + box_height > height * 1.02:
                raise FaceCheckError('Giữ toàn bộ khuôn mặt trong khung, không che hoặc cắt phần mặt.')
            yaw = _landmark_yaw(row)
            aligned = self.recognizer.alignCrop(image, row)
            gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)
            brightness = float(gray.mean())
            sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            if not 30 <= brightness <= 245 or sharpness < 18:
                raise FaceCheckError('Ảnh tối, chói hoặc bị mờ. Giữ máy ổn định trong ánh sáng tốt.')
            feature = self.recognizer.feature(aligned)
            return _Observation(_normalise(feature.reshape(-1).astype(float).tolist()), yaw)
        except FaceCheckError:
            raise
        except Exception:
            raise FaceCheckError('Không xử lý được ảnh camera. Hãy chụp lại đủ bốn bước.') from None


def _read_sequence(images: Sequence[bytes]) -> list[_Observation]:
    global _engine, _initialization_failed
    if _engine is None:
        try:
            _engine = _Engine()
        except FaceEngineUnavailable:
            _initialization_failed = True
            raise
    return [_engine.observe(image) for image in images]


def _check_sequence(observations: Sequence[_Observation], steps: Sequence[str]) -> list[list[float]]:
    if len(observations) != 4 or any(not math.isfinite(item.yaw) for item in observations):
        raise FaceCheckError('Không đọc đủ mẫu khuôn mặt. Hãy bắt đầu lại.')
    front_start, front_end = observations[0].yaw, observations[-1].yaw
    if max(abs(front_start), abs(front_end)) > MAX_FRONT_YAW or abs(front_start - front_end) > MAX_FRONT_DRIFT:
        raise FaceCheckError('Ở bước nhìn thẳng, giữ đầu thẳng và nhìn vào camera.', 'pose')
    baseline = (front_start + front_end) / 2
    turned = {}
    for item, step in zip(observations[1:3], steps[1:3]):
        delta = item.yaw - baseline
        turned[step] = delta
        if step == 'turn_left' and delta < MIN_YAW_DELTA:
            raise FaceCheckError('Chưa thấy bước quay sang trái của bạn. Quay đầu nhẹ theo hướng dẫn rồi chụp lại.', 'pose')
        if step == 'turn_right' and delta > -MIN_YAW_DELTA:
            raise FaceCheckError('Chưa thấy bước quay sang phải của bạn. Quay đầu nhẹ theo hướng dẫn rồi chụp lại.', 'pose')
    if turned['turn_left'] - turned['turn_right'] < MIN_TURN_SPAN:
        raise FaceCheckError('Cần thể hiện rõ hai hướng quay đầu trong các bước chụp.', 'pose')
    features = [_normalise(item.feature) for item in observations]
    if _cosine(features[0], features[-1]) < FRONT_CONSISTENCY_THRESHOLD or any(
            _cosine(left, right) < CONSISTENCY_THRESHOLD
            for index, left in enumerate(features) for right in features[index + 1:]):
        raise FaceCheckError('Các ảnh chưa khớp cùng một người. Hãy giữ nguyên người xác thực và chụp lại.', 'identity')
    return features


def _capture(images: Sequence[bytes], steps: Sequence[str]) -> list[list[float]]:
    _validate_inputs(images, steps)
    if not _slot.acquire(blocking=False):
        raise FaceEngineUnavailable('Máy chủ đang xử lý một lượt nhận diện khác. Hãy thử lại sau hoặc dùng mật khẩu và OTP.')
    try:
        return _check_sequence(_read_sequence(images), steps)
    finally:
        _slot.release()


def enroll_faces(images: list[bytes], steps: list[str]) -> list[list[float]]:
    return _capture(images, steps)


def verify_faces(images: list[bytes], steps: list[str], templates: list[list[float]]) -> float:
    if not isinstance(templates, (list, tuple)) or len(templates) != 4:
        raise FaceCheckError('Mẫu đăng ký chưa hợp lệ. Hãy dùng mật khẩu và OTP để đăng ký lại.', 'template')
    references = [_normalise(item, reason='template') for item in templates]
    candidates = _capture(images, steps)
    scores = [max(_cosine(candidate, reference) for reference in references) for candidate in candidates]
    if min(scores) < COSINE_MATCH_THRESHOLD:
        raise FaceCheckError('Chưa xác nhận được khuôn mặt đã đăng ký. Hãy thử lại hoặc dùng mật khẩu và OTP.', 'identity')
    return min(scores)
