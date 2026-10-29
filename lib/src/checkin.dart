import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:provider/provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import 'api.dart';
import 'device.dart';
import 'session.dart';
import 'theme.dart';
import 'widgets.dart';
import 'corrections.dart';

class CheckinScreen extends StatefulWidget {
  final String? assignmentId;
  const CheckinScreen({this.assignmentId, super.key});
  @override
  State<CheckinScreen> createState() => _CheckinScreenState();
}

class _CheckinScreenState extends State<CheckinScreen> {
  List<Json>? assignments;
  String? selected, qr, error;
  Position? position;
  Json? motion, report, lastPayload;
  bool busy = false;
  double live = 0;
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      final list = await context.read<Session>().api!.list('/assignments');
      final yesterday = DateTime.parse(todayIso())
          .subtract(const Duration(days: 1))
          .toIso8601String()
          .substring(0, 10);
      final available = list
          .where(
            (x) =>
                x['user_id'] == context.read<Session>().user!['id'] &&
                (x['work_date'] == todayIso() || x['work_date'] == yesterday) &&
                x['attendance']?['check_out'] == null,
          )
          .toList();
      if (mounted) {
        setState(() {
          assignments = available;
          selected = available.any((x) => x['id'] == widget.assignmentId)
              ? widget.assignmentId
              : available.firstOrNull?['id'];
          error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => error = '$e');
    }
  }

  Json? get assignment =>
      assignments?.where((a) => a['id'] == selected).firstOrNull;
  Future<void> locate() async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final p = await capturePosition();
      if (mounted) setState(() => position = p);
    } catch (e) {
      if (mounted) setState(() => error = '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> measure() async {
    setState(() {
      busy = true;
      error = null;
      motion = null;
    });
    try {
      final m = await captureMotion(
        onSample: (x) {
          if (mounted) setState(() => live = x);
        },
      );
      if (mounted) setState(() => motion = m);
    } catch (e) {
      if (mounted) setState(() => error = '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> scan() async {
    final value = await Navigator.push<String>(
      context,
      MaterialPageRoute(builder: (_) => const ScannerScreen()),
    );
    if (mounted && value != null) {
      setState(() {
        qr = value;
        report = null;
      });
    }
  }

  Future<void> shareLocation() async {
    try {
      final p = position ?? await capturePosition();
      if (!mounted) return;
      final box = context.findRenderObject() as RenderBox?;
      await SharePlus.instance.share(
        ShareParams(
          text:
              'Vị trí chấm công của tôi\nhttps://maps.google.com/?q=${p.latitude},${p.longitude}\nSai số GPS: ${p.accuracy.round()} m',
          sharePositionOrigin: box == null
              ? null
              : box.localToGlobal(Offset.zero) & box.size,
        ),
      );
    } catch (e) {
      if (mounted) toast(context, '$e', error: true);
    }
  }

  Future<void> submit() async {
    if (assignment == null || qr == null) {
      toast(context, 'Chọn ca làm và quét QR trước.', error: true);
      return;
    }
    setState(() {
      busy = true;
      error = null;
      report = null;
    });
    try {
      // Recapture both sensors at submission; earlier previews are never reused as fresh evidence.
      final results = await Future.wait<dynamic>([
        capturePosition(),
        captureMotion(
          onSample: (x) {
            if (mounted) setState(() => live = x);
          },
        ),
      ]);
      position = results[0] as Position;
      motion = Json.from(results[1]);
      final p = position!;
      final evidence = <String, dynamic>{
        'latitude': p.latitude,
        'longitude': p.longitude,
        'accuracy_m': p.accuracy,
        'captured_at': p.timestamp.toUtc().toIso8601String(),
        'is_mocked': p.isMocked,
        'qr_token': qr,
        ...motion!,
      };
      lastPayload = evidence;
      if (!mounted) return;
      final result = await context.read<Session>().api!.call(
        '/attendance/check',
        method: 'POST',
        body: {
          ...evidence,
          'assignment_id': selected,
          'action': assignment!['attendance']?['check_in'] == null
              ? 'in'
              : 'out',
        },
      );
      if (mounted) {
        toast(
          context,
          'Đã chấm công lúc ${clockText(result['check_out'] ?? result['check_in'])}.',
        );
        Navigator.pop(context, true);
      }
    } on ApiError catch (e) {
      if (mounted) {
        setState(() {
          error = e.message;
          report = e.evidence;
        });
      }
    } catch (e) {
      if (mounted) setState(() => error = '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Widget step(
    int n,
    String title,
    String detail,
    IconData icon,
    VoidCallback action, {
    bool done = false,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: 14),
    child: Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(
          children: [
            CircleAvatar(
              backgroundColor: done ? teal.withValues(alpha: .12) : canvas,
              child: Icon(done ? Icons.check_rounded : icon, color: teal),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '$n. $title',
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    detail,
                    style: const TextStyle(color: muted, fontSize: 12),
                  ),
                ],
              ),
            ),
            IconButton(
              onPressed: busy ? null : action,
              icon: const Icon(Icons.arrow_forward_rounded, color: teal),
            ),
          ],
        ),
      ),
    ),
  );
  @override
  Widget build(BuildContext context) {
    final a = assignment;
    double? distance;
    if (position != null && a != null) {
      distance = Geolocator.distanceBetween(
        position!.latitude,
        position!.longitude,
        (a['site']['latitude'] as num).toDouble(),
        (a['site']['longitude'] as num).toDouble(),
      );
    }
    return Scaffold(
      appBar: AppBar(title: const Text('Chấm công')),
      body: ListView(
        padding: const EdgeInsets.all(22),
        children: [
          Text(
            'Có mặt. Đúng lúc.',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          const Text(
            'Xác nhận ca làm bằng vị trí, QR và mẫu chuyển động. Vị trí chỉ được lấy khi bạn thao tác.',
            style: TextStyle(color: muted),
          ),
          const SizedBox(height: 24),
          if (assignments == null && error == null)
            const Center(child: CircularProgressIndicator())
          else if (assignments?.isEmpty == true)
            const EmptyState(
              'Bạn chưa có ca đang mở trong hôm nay hoặc hôm qua. Liên hệ quản trị viên để phân ca.',
            )
          else if (assignments != null) ...[
            DropdownButtonFormField<String>(
              initialValue: selected,
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'Ca của bạn'),
              items: assignments!
                  .map(
                    (x) => DropdownMenuItem<String>(
                      value: x['id'],
                      child: Text(
                        '${x['shift']['name']} • ${dateText(x['work_date'])}',
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  )
                  .toList(),
              onChanged: busy
                  ? null
                  : (v) => setState(() {
                      selected = v;
                      qr = null;
                      report = null;
                    }),
            ),
            const SizedBox(height: 18),
            if (a != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 20),
                child: Text(
                  '${a['site']['name']} • ${a['shift']['start_time']} – ${a['shift']['end_time']}\nBán kính cho phép: ${a['site']['radius_m']} m',
                  style: const TextStyle(color: muted),
                ),
              ),
            step(
              1,
              'Vị trí của bạn',
              position == null
                  ? 'Bật GPS và cấp quyền vị trí'
                  : 'Sai số ${position!.accuracy.round()} m${distance == null ? '' : ' • cách điểm ${distance.round()} m'}',
              Icons.my_location,
              locate,
              done: position != null,
            ),
            if (position != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Wrap(
                  spacing: 12,
                  children: [
                    TextButton.icon(
                      onPressed: busy ? null : shareLocation,
                      icon: const Icon(Icons.share_location_outlined),
                      label: const Text('Chia sẻ vị trí'),
                    ),
                    TextButton.icon(
                      onPressed: () async {
                        final ok = await launchUrl(
                          Uri.parse(
                            'https://maps.google.com/?q=${position!.latitude},${position!.longitude}',
                          ),
                          mode: LaunchMode.externalApplication,
                        );
                        if (!ok && context.mounted) {
                          toast(context, 'Không mở được bản đồ.', error: true);
                        }
                      },
                      icon: const Icon(Icons.map_outlined),
                      label: const Text('Bản đồ'),
                    ),
                  ],
                ),
              ),
            step(
              2,
              'Quét QR tại nơi làm việc',
              qr == null
                  ? 'Quét mã đang hiển thị trên thiết bị quản trị'
                  : 'Đã quét • máy chủ sẽ xác minh hạn dùng',
              Icons.qr_code_scanner,
              scan,
              done: qr != null,
            ),
            step(
              3,
              'Đo chuyển động',
              motion == null
                  ? (busy
                        ? '${live.toStringAsFixed(2)} m/s² • đang đo…'
                        : 'Lấy mẫu cảm biến gia tốc trong 3 giây')
                  : 'RMS ${(motion!['motion_rms'] as num).toStringAsFixed(2)} m/s² • ${motion!['motion_samples']} mẫu',
              Icons.sensors_rounded,
              measure,
              done: motion != null,
            ),
            const Text(
              'Khi xác nhận, ứng dụng lấy lại vị trí và chuyển động mới nhất. QR có thời hạn; hãy quét lại nếu cần.',
              style: TextStyle(color: muted, fontSize: 12),
            ),
            const SizedBox(height: 18),
            FilledButton.icon(
              onPressed: busy || a == null || qr == null ? null : submit,
              icon: const Icon(Icons.task_alt_rounded),
              label: Text(
                busy
                    ? 'Đang lấy mẫu và xác nhận…'
                    : a?['attendance']?['check_in'] == null
                    ? 'Xác nhận vào ca'
                    : 'Xác nhận ra ca',
              ),
            ),
          ],
          if (error != null) ...[
            const SizedBox(height: 18),
            Text(error!, style: const TextStyle(color: Color(0xFFAD3939))),
            if (assignments == null)
              OutlinedButton(onPressed: load, child: const Text('Thử lại')),
          ],
          if (report != null) ...[
            const SizedBox(height: 18),
            EvidenceView(report!),
          ],
          if (a != null && !busy)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: OutlinedButton.icon(
                onPressed: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => CorrectionEditor(
                      assignment: a,
                      initialEvidence: lastPayload,
                    ),
                  ),
                ),
                icon: const Icon(Icons.edit_note_rounded),
                label: const Text('Gửi giải trình / đề nghị điều chỉnh'),
              ),
            ),
        ],
      ),
    );
  }
}

class ScannerScreen extends StatefulWidget {
  const ScannerScreen({super.key});
  @override
  State<ScannerScreen> createState() => _ScannerScreenState();
}

class _ScannerScreenState extends State<ScannerScreen>
    with WidgetsBindingObserver {
  final controller = MobileScannerController(
    formats: const [BarcodeFormat.qrCode],
  );
  bool completed = false;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && !completed) {
      controller.start();
    } else if (state == AppLifecycleState.inactive ||
        state == AppLifecycleState.paused) {
      controller.stop();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: navy,
    appBar: AppBar(
      title: const Text('Quét QR chấm công'),
      actions: [
        IconButton(
          onPressed: controller.toggleTorch,
          icon: const Icon(Icons.flashlight_on_outlined),
        ),
      ],
    ),
    body: Stack(
      children: [
        MobileScanner(
          controller: controller,
          errorBuilder: (context, error) => const Center(
            child: Padding(
              padding: EdgeInsets.all(24),
              child: Text(
                'Không mở được camera. Hãy cấp quyền Camera trong Cài đặt ứng dụng.',
                style: TextStyle(color: Colors.white),
                textAlign: TextAlign.center,
              ),
            ),
          ),
          onDetect: (capture) {
            final value = capture.barcodes.firstOrNull?.rawValue;
            if (value != null && value.isNotEmpty && !completed) {
              completed = true;
              Navigator.pop(context, value);
            }
          },
        ),
        Center(
          child: IgnorePointer(
            child: Container(
              width: 270,
              height: 270,
              decoration: BoxDecoration(
                border: Border.all(color: Colors.white, width: 3),
                borderRadius: BorderRadius.circular(28),
              ),
            ),
          ),
        ),
        const Positioned(
          left: 24,
          right: 24,
          bottom: 48,
          child: Text(
            'Đưa QR của điểm chấm công vào khung.\nMã sẽ được máy chủ xác minh.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white, fontSize: 16),
          ),
        ),
      ],
    ),
  );
}

class MotionScreen extends StatefulWidget {
  const MotionScreen({super.key});
  @override
  State<MotionScreen> createState() => _MotionScreenState();
}

class _MotionScreenState extends State<MotionScreen> {
  final samples = <double>[];
  Json? result;
  String? error;
  bool busy = false;
  Future<void> measure() async {
    setState(() {
      busy = true;
      samples.clear();
      result = null;
      error = null;
    });
    try {
      final value = await captureMotion(
        onSample: (x) {
          if (mounted) setState(() => samples.add(x));
        },
      );
      if (mounted) setState(() => result = value);
    } catch (e) {
      if (mounted) setState(() => error = '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Chuyển động thiết bị')),
    body: ListView(
      padding: const EdgeInsets.all(24),
      children: [
        const StatusPill('CẢM BIẾN GIA TỐC'),
        const SizedBox(height: 24),
        Text(
          'Chuyển động\nthành dữ liệu.',
          style: Theme.of(context).textTheme.headlineLarge,
        ),
        const SizedBox(height: 12),
        const Text(
          'Đo gia tốc không bao gồm trọng lực trong 3 giây. Di chuyển nhẹ điện thoại để quan sát đồ thị.',
          style: TextStyle(color: muted),
        ),
        const SizedBox(height: 26),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                Text(
                  '${(samples.lastOrNull ?? 0).toStringAsFixed(2)} m/s²',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 20),
                SizedBox(
                  height: 180,
                  width: double.infinity,
                  child: CustomPaint(painter: MotionPainter(List.of(samples))),
                ),
                const SizedBox(height: 10),
                Text(
                  '${samples.length} mẫu đã nhận',
                  style: const TextStyle(color: muted),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 22),
        FilledButton.icon(
          onPressed: busy ? null : measure,
          icon: const Icon(Icons.sensors_rounded),
          label: Text(busy ? 'Đang đo trong 3 giây…' : 'Bắt đầu đo'),
        ),
        if (error != null)
          Padding(
            padding: const EdgeInsets.only(top: 16),
            child: Text(error!, style: const TextStyle(color: Colors.red)),
          ),
        if (result != null) ...[
          const SectionTitle('Kết quả đo'),
          DetailLine(
            'RMS',
            '${(result!['motion_rms'] as num).toStringAsFixed(3)} m/s²',
          ),
          DetailLine('Thời gian', '${result!['motion_duration_ms']} ms'),
          DetailLine('Số mẫu', '${result!['motion_samples']}'),
          const SizedBox(height: 16),
          const Text(
            'Mẫu chuyển động hỗ trợ giải trình trạng thái thiết bị khi chấm công. Dữ liệu này không xác minh danh tính người cầm máy.',
            style: TextStyle(color: muted),
          ),
        ],
      ],
    ),
  );
}

class MotionPainter extends CustomPainter {
  final List<double> values;
  MotionPainter(this.values);
  @override
  void paint(Canvas canvas, Size size) {
    final grid = Paint()
      ..color = const Color(0xFFE1E9E5)
      ..strokeWidth = 1;
    for (var i = 0; i <= 4; i++) {
      canvas.drawLine(
        Offset(0, size.height * i / 4),
        Offset(size.width, size.height * i / 4),
        grid,
      );
    }
    if (values.length < 2) return;
    final maxValue = max(1.0, values.reduce(max));
    final path = Path();
    for (var i = 0; i < values.length; i++) {
      final x = size.width * i / (values.length - 1),
          y = size.height * (1 - values[i] / maxValue);
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }
    canvas.drawPath(
      path,
      Paint()
        ..color = teal
        ..strokeWidth = 2.5
        ..style = PaintingStyle.stroke,
    );
  }

  @override
  bool shouldRepaint(covariant MotionPainter oldDelegate) => true;
}
