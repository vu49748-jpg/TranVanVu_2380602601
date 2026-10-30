"""Pinned OpenCV Zoo model assets; no application secrets are needed to run this CLI.

Download at build time with ``python -m app.face_models --download``. Inference
never downloads a model or silently substitutes a different model at runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
import tempfile
import threading
import urllib.request


ZOO_COMMIT = '48b10fa505aeb51fbd127fc60a5c660040e823b7'
_BASE = f'https://media.githubusercontent.com/media/opencv/opencv_zoo/{ZOO_COMMIT}/models'


@dataclass(frozen=True)
class ModelAsset:
    filename: str
    subdirectory: str
    sha256: str
    size: int

    @property
    def url(self) -> str:
        return f'{_BASE}/{self.subdirectory}/{self.filename}'


MODELS = (
    ModelAsset(
        'face_detection_yunet_2023mar.onnx', 'face_detection_yunet',
        '8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4',
        232589,
    ),
    ModelAsset(
        'face_recognition_sface_2021dec.onnx', 'face_recognition_sface',
        '0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79',
        38696353,
    ),
)


class ModelDownloadError(RuntimeError):
    """An asset was not fetched and verified; an old model is never overwritten."""


_verified: dict[str, tuple] = {}
_cache_lock = threading.Lock()


def model_directory(directory: Path | str | None = None) -> Path:
    if directory is not None:
        return Path(directory).resolve()
    configured = os.getenv('FACE_MODEL_DIR')
    return (Path(configured) if configured else Path(__file__).resolve().parent.parent / '.face_models').resolve()


def _valid(path: Path, asset: ModelAsset) -> bool:
    try:
        stat = path.stat()
        stamp = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        if not path.is_file() or stat.st_size != asset.size:
            return False
        key = str(path)
        with _cache_lock:
            if _verified.get(key) == (*stamp, asset.sha256):
                return True
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        if digest.hexdigest() != asset.sha256:
            return False
        with _cache_lock:
            _verified[key] = (*stamp, asset.sha256)
        return True
    except OSError:
        return False


def verified_model_paths(directory: Path | str | None = None) -> tuple[Path, Path] | None:
    root = model_directory(directory)
    paths = tuple(root / asset.filename for asset in MODELS)
    return paths if all(_valid(path, asset) for path, asset in zip(paths, MODELS)) else None


def download_models(directory: Path | str | None = None) -> tuple[Path, Path]:
    """Stream to a temporary file, check exact size/hash, then atomically replace.

    A truncated response, HTML error page, LFS pointer, or changed upstream model
    fails the build. The two hashes are the official Git LFS object identifiers.
    """
    root = model_directory(directory)
    root.mkdir(parents=True, exist_ok=True)
    for asset in MODELS:
        destination = root / asset.filename
        if _valid(destination, asset):
            continue
        temporary: Path | None = None
        try:
            request = urllib.request.Request(asset.url, headers={'User-Agent': 'TranVanVu-face-model-build/2'})
            with urllib.request.urlopen(request, timeout=120) as response:
                length = response.headers.get('Content-Length')
                if length is not None and int(length) != asset.size:
                    raise ModelDownloadError('Model response has an unexpected size.')
                digest = hashlib.sha256()
                written = 0
                with tempfile.NamedTemporaryFile(mode='wb', prefix=asset.filename + '.', suffix='.part', dir=root, delete=False) as stream:
                    temporary = Path(stream.name)
                    while True:
                        block = response.read(128 * 1024)
                        if not block:
                            break
                        written += len(block)
                        if written > asset.size:
                            raise ModelDownloadError('Model response exceeds the pinned size.')
                        digest.update(block)
                        stream.write(block)
                    stream.flush()
                    os.fsync(stream.fileno())
            if written != asset.size or digest.hexdigest() != asset.sha256:
                raise ModelDownloadError('Model checksum verification failed.')
            os.replace(temporary, destination)
            temporary = None
            with _cache_lock:
                _verified.pop(str(destination), None)
        except ModelDownloadError:
            raise
        except (OSError, ValueError) as error:
            raise ModelDownloadError('Unable to download the pinned face model.') from error
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    result = verified_model_paths(root)
    if result is None:
        raise ModelDownloadError('Downloaded face models did not pass verification.')
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true', help='Download and verify pinned official model assets.')
    parser.add_argument('--directory', type=Path)
    args = parser.parse_args()
    if args.download:
        download_models(args.directory)
        print('Verified YuNet and SFace model assets are ready.')
    elif verified_model_paths(args.directory) is None:
        raise SystemExit('Face model assets are missing or failed integrity verification.')
    else:
        print('Face model assets passed integrity verification.')


if __name__ == '__main__':
    main()
