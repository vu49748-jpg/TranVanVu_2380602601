import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import 'api.dart';
import 'theme.dart';

String dateText(dynamic value, {bool full = false}) {
  final dt = DateTime.tryParse('$value');
  if (dt == null) return '—';
  final business = '$value'.contains('T')
      ? dt.toUtc().add(const Duration(hours: 7))
      : dt;
  return DateFormat(full ? 'dd/MM/yyyy • HH:mm' : 'dd/MM/yyyy')
      .format(business);
}

String clockText(dynamic value) {
  final dt = DateTime.tryParse('$value');
  return dt == null
      ? '—'
      : DateFormat('HH:mm').format(dt.toUtc().add(const Duration(hours: 7)));
}

String todayIso() =>
    DateFormat('yyyy-MM-dd')
        .format(DateTime.now().toUtc().add(const Duration(hours: 7)));
String statusText(dynamic value) =>
    const {
      'present': 'Đúng giờ',
      'late': 'Đi muộn',
      'adjusted': 'Đã điều chỉnh',
      'pending': 'Chờ duyệt',
      'approved': 'Đã duyệt',
      'rejected': 'Từ chối',
      'employee': 'Nhân viên',
      'admin': 'Quản trị viên',
    }[value] ??
    '${value ?? 'Chưa chấm công'}';
void toast(BuildContext context, String message, {bool error = false}) =>
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: error ? const Color(0xFFAD3939) : navy,
        behavior: SnackBarBehavior.floating,
      ),
    );

class SectionTitle extends StatelessWidget {
  final String title;
  final String? subtitle;
  final Widget? action;
  const SectionTitle(this.title, {this.subtitle, this.action, super.key});
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 24, bottom: 14),
    child: Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: Theme.of(context).textTheme.titleLarge),
              if (subtitle != null)
                Text(
                  subtitle!,
                  style: const TextStyle(color: muted, fontSize: 12),
                ),
            ],
          ),
        ),
        ?action,
      ],
    ),
  );
}

class StatusPill extends StatelessWidget {
  final String text;
  final Color color;
  const StatusPill(this.text, {this.color = teal, super.key});
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
    decoration: BoxDecoration(
      color: color.withValues(alpha: .1),
      borderRadius: BorderRadius.circular(9),
    ),
    child: Text(
      text,
      style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w700),
    ),
  );
}

class EmptyState extends StatelessWidget {
  final String text;
  final IconData icon;
  const EmptyState(this.text, {this.icon = Icons.inbox_outlined, super.key});
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 32, horizontal: 20),
    child: Column(
      children: [
        Icon(icon, color: muted, size: 42),
        const SizedBox(height: 12),
        Text(
          text,
          textAlign: TextAlign.center,
          style: const TextStyle(color: muted),
        ),
      ],
    ),
  );
}

class Failure extends StatelessWidget {
  final Object error;
  final VoidCallback retry;
  const Failure(this.error, this.retry, {super.key});
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.all(24),
    child: Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Icon(Icons.cloud_off_rounded, size: 40, color: muted),
        const SizedBox(height: 12),
        Text('$error', textAlign: TextAlign.center),
        const SizedBox(height: 12),
        OutlinedButton(onPressed: retry, child: const Text('Thử lại')),
      ],
    ),
  );
}

class DetailLine extends StatelessWidget {
  final String label, value;
  const DetailLine(this.label, this.value, {super.key});
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 6),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 112,
          child: Text(label, style: const TextStyle(color: muted)),
        ),
        Expanded(
          child: Text(
            value,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
        ),
      ],
    ),
  );
}

Future<bool> confirmDelete(BuildContext context) async =>
    await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Xóa dữ liệu?'),
        content: const Text('Thao tác này sẽ xóa dữ liệu đã chọn.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Hủy'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Xóa'),
          ),
        ],
      ),
    ) ??
    false;

class EvidenceView extends StatelessWidget {
  final Json evidence;
  const EvidenceView(this.evidence, {super.key});
  @override
  Widget build(BuildContext context) {
    final flags = List<String>.from(evidence['flags'] ?? []);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Hồ sơ bằng chứng',
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 17),
            ),
            const SizedBox(height: 8),
            DetailLine('Khoảng cách', '${evidence['distance_m'] ?? '—'} m'),
            DetailLine('Sai số GPS', '${evidence['accuracy_m'] ?? '—'} m'),
            DetailLine(
              'Vị trí',
              '${evidence['latitude']}, ${evidence['longitude']}',
            ),
            DetailLine(
              'Chuyển động',
              '${evidence['motion_label'] ?? '—'} • ${evidence['motion_rms']} m/s²',
            ),
            DetailLine(
              'Mẫu cảm biến',
              '${evidence['motion_samples']} mẫu / ${evidence['motion_duration_ms']} ms',
            ),
            DetailLine(
              'QR lúc gửi',
              evidence['qr_valid'] == true ? 'Hợp lệ' : 'Chưa hợp lệ',
            ),
            DetailLine(
              'Ghi nhận',
              dateText(evidence['captured_at'], full: true),
            ),
            if (flags.isEmpty)
              const StatusPill('GPS và QR đạt kiểm tra')
            else
              ...flags.map(
                (x) => Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text(
                    '• $x',
                    style: const TextStyle(color: Color(0xFFAD3939)),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
