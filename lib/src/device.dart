import 'dart:async';
import 'dart:math';

import 'package:geolocator/geolocator.dart';
import 'package:sensors_plus/sensors_plus.dart';

import 'api.dart';

Future<Position> capturePosition() async {
  if (!await Geolocator.isLocationServiceEnabled()) {
    throw ApiError('Hãy bật định vị GPS trên điện thoại rồi thử lại.');
  }
  var permission = await Geolocator.checkPermission();
  if (permission == LocationPermission.denied) {
    permission = await Geolocator.requestPermission();
  }
  if (permission == LocationPermission.deniedForever) {
    throw ApiError(
      'Quyền vị trí đã bị từ chối vĩnh viễn. Mở Cài đặt ứng dụng và cấp lại quyền.',
    );
  }
  if (permission == LocationPermission.denied) {
    throw ApiError('Cần quyền vị trí để chia sẻ vị trí và chấm công.');
  }
  return Geolocator.getCurrentPosition(
    locationSettings: const LocationSettings(
      accuracy: LocationAccuracy.high,
      timeLimit: Duration(seconds: 25),
    ),
  );
}

Future<Json> captureMotion({void Function(double)? onSample}) async {
  final samples = <double>[];
  Object? sensorError;
  final watch = Stopwatch()..start();
  final subscription =
      userAccelerometerEventStream(
        samplingPeriod: const Duration(milliseconds: 60),
      ).listen(
        (event) {
          final magnitude = sqrt(
            event.x * event.x + event.y * event.y + event.z * event.z,
          );
          if (magnitude.isFinite) {
            samples.add(magnitude);
            onSample?.call(magnitude);
          }
        },
        onError: (Object e) {
          sensorError = e;
        },
      );
  try {
    await Future<void>.delayed(const Duration(seconds: 3));
  } finally {
    await subscription.cancel();
    watch.stop();
  }
  if (sensorError != null || samples.length < 15) {
    throw ApiError(
      'Không lấy đủ mẫu chuyển động. Hãy thử trên điện thoại có cảm biến gia tốc.',
    );
  }
  return {
    'motion_rms': sqrt(
      samples.fold<double>(0, (sum, x) => sum + x * x) / samples.length,
    ),
    'motion_samples': samples.length,
    'motion_duration_ms': watch.elapsedMilliseconds,
  };
}
