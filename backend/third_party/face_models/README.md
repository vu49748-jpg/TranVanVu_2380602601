# Face recognition model provenance

The application uses **YuNet for face/landmark detection and SFace for actual
one-to-one face recognition**. Detecting a face alone is not accepted as a login.

Both ONNX assets are pinned to OpenCV Zoo commit
`48b10fa505aeb51fbd127fc60a5c660040e823b7`. They are downloaded during the backend
build, not from an arbitrary URL supplied by a client. Exact sizes and SHA-256
digests are checked before an atomic rename. A missing or changed asset disables
face login; password plus Email OTP remains available.

| Asset | Bytes | SHA-256 | License |
|---|---:|---|---|
| `face_detection_yunet_2023mar.onnx` | 232589 | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` | [MIT](YuNet-LICENSE.txt) |
| `face_recognition_sface_2021dec.onnx` | 38696353 | `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79` | [Apache-2.0](SFace-LICENSE.txt) |

Official sources:

- [YuNet model, upstream description and license](https://github.com/opencv/opencv_zoo/tree/48b10fa505aeb51fbd127fc60a5c660040e823b7/models/face_detection_yunet)
- [SFace model, upstream description and license](https://github.com/opencv/opencv_zoo/tree/48b10fa505aeb51fbd127fc60a5c660040e823b7/models/face_recognition_sface)
- [OpenCV face detection and recognition tutorial](https://docs.opencv.org/4.x/d0/dd4/tutorial_dnn_face.html)

The copies of the model licenses in this directory retain upstream notices.

## Build and operating limits

From `backend/`, after installing the pinned requirements:

```text
python -m app.face_models --download
python -m app.face_models
```

The default model cache is `backend/.face_models/`; `FACE_MODEL_DIR` can override
it. Model weights are build assets, not user data. No runtime inference call
downloads or substitutes weights. OpenCV uses one CPU thread and only one
inference sequence runs at a time; another concurrent sequence receives a safe
busy response rather than allocating another DNN on a small server.

Each request has four JPEG frames, each at most 768 KiB and at most 2,073,600
pixels. Image dimensions are checked before full decoding; EXIF rotation is
applied. Frames require exactly one adequately sized, visible, sharp face. The
JPEGs and aligned face crops remain in process memory and are not written to
files, logs or the database. The route layer encrypts the resulting descriptors
and never returns those descriptors to the client.

## Recognition and active capture checks

SFace produces 128-dimensional descriptors. This application normalizes them
and requires cosine similarity of at least **0.50** against the registered
references for every capture. It also checks identity consistency between the
four frames. The official OpenCV tutorial gives **0.363** as the LFW evaluation
cutoff; the stricter value used here is a design choice, not a calibrated claim
of population accuracy or a guaranteed false-acceptance rate.

The server supplies four ordered steps: front, left/right in random order,
then front again. Images must be **unmirrored camera JPEGs**. `turn_left` means
the person turns towards **their own left**, so the nose moves towards image
positive X in the unmirrored image; `turn_right` is the opposite. The selfie
preview may be mirrored, but the uploaded JPEGs must not be mirrored.

Nose displacement is measured relative to the eye line. Merely moving an image
sideways, changing scale or rolling it in its own plane does not satisfy this
check. Equal JPEG payloads, unchanged pose, wrong directions and mixed-person
sequences are rejected. Small head turns of roughly 20–30 degrees are preferable
to turning completely into profile.

This is an **active capture check intended to reduce simple still-photo use**.
It is not certified 3-D liveness or a complete presentation-attack detector.
Replayed/manipulated video, a compromised client, and advanced physical spoofs
remain limitations. Signed, one-use device challenges, rate limits, OTP-gated
enrollment and credential revocation are independent layers; none converts this
prototype into certified biometric hardware.

## Verification performed during development

- Unit tests exercise step ordering, wrong direction, no movement, repeated
  payloads, inconsistent identities, corrupt templates, single-inference limits,
  malformed/oversized JPEGs, EXIF orientation and model-integrity failures.
- An actual CPU inference smoke used the Apache-2.0 example image from the
  pinned SFace directory. YuNet and SFace loaded, emitted a finite normalized
  128-dimensional descriptor, and four brightness variants of the same still
  portrait were rejected for missing head turns. The fixture and its derived
  images are diagnostic artifacts, not user registration data.
- Live owner enrollment and later login must be tested on the actual Android
  camera. A passing model smoke or mocked protocol test does not substitute for
  that live test or establish population accuracy.
