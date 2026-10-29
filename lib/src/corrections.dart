import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import 'api.dart';
import 'session.dart';
import 'theme.dart';
import 'widgets.dart';

class CorrectionsPage extends StatefulWidget {
  const CorrectionsPage({super.key});
  @override
  State<CorrectionsPage> createState() => _CorrectionsPageState();
}

class _CorrectionsPageState extends State<CorrectionsPage> {
  List<Json>? rows;
  Object? error;
  String filter = 'all';
  Api get api => context.read<Session>().api!;
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      final list = await api.list('/corrections');
      if (mounted) {
        setState(() {
          rows = list;
          error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => error = e);
    }
  }

  Future<void> add() async {
    try {
      final assignments = await api.list('/assignments');
      final own = assignments
          .where((x) => x['user_id'] == context.read<Session>().user!['id'])
          .toList();
      if (!mounted) return;
      if (own.isEmpty) {
        toast(context, 'Bạn chưa được phân ca để gửi yêu cầu.');
        return;
      }
      final chosen = await showModalBottomSheet<Json>(
        context: context,
        showDragHandle: true,
        builder: (_) => SafeArea(
          child: ListView(
            shrinkWrap: true,
            children: [
              const ListTile(
                title: Text(
                  'Chọn ca cần giải trình',
                  style: TextStyle(fontWeight: FontWeight.w800),
                ),
              ),
              ...own.map(
                (a) => ListTile(
                  title: Text(a['shift']['name']),
                  subtitle: Text(dateText(a['work_date'])),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => Navigator.pop(context, a),
                ),
              ),
            ],
          ),
        ),
      );
      if (chosen != null && mounted) {
        await Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => CorrectionEditor(assignment: chosen),
          ),
        );
        await load();
      }
    } catch (e) {
      if (mounted) toast(context, '$e', error: true);
    }
  }

  Future<void> detail(Json row) async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => CorrectionDetail(row)),
    );
    await load();
  }

  @override
  Widget build(BuildContext context) {
    final admin = context.watch<Session>().admin;
    final list = (rows ?? [])
        .where((x) => filter == 'all' || x['status'] == filter)
        .toList();
    return Scaffold(
      backgroundColor: canvas,
      floatingActionButton: admin
          ? null
          : FloatingActionButton.extended(
              onPressed: add,
              icon: const Icon(Icons.add_rounded),
              label: const Text('Gửi yêu cầu'),
            ),
      body: error != null
          ? Failure(error!, load)
          : rows == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: load,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(22, 12, 22, 100),
                children: [
                  Text(
                    admin
                        ? 'Mỗi yêu cầu,\nmột quyết định rõ ràng.'
                        : 'Cần điều chỉnh?\nHãy chia sẻ lý do.',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Giờ đề xuất, lý do và bằng chứng được lưu cùng kết quả xử lý.',
                    style: TextStyle(color: muted),
                  ),
                  const SizedBox(height: 18),
                  Wrap(
                    spacing: 8,
                    children: [
                      for (final value in [
                        'all',
                        'pending',
                        'approved',
                        'rejected',
                      ])
                        ChoiceChip(
                          label: Text(
                            value == 'all' ? 'Tất cả' : statusText(value),
                          ),
                          selected: filter == value,
                          onSelected: (_) => setState(() => filter = value),
                        ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  if (list.isEmpty)
                    const EmptyState('Chưa có yêu cầu phù hợp.'),
                  ...list.map(
                    (r) => Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Card(
                        child: InkWell(
                          borderRadius: BorderRadius.circular(22),
                          onTap: () => detail(r),
                          child: Padding(
                            padding: const EdgeInsets.all(18),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Expanded(
                                      child: Text(
                                        r['employee_name'],
                                        style: const TextStyle(
                                          fontWeight: FontWeight.w800,
                                        ),
                                      ),
                                    ),
                                    StatusPill(
                                      statusText(r['status']),
                                      color: r['status'] == 'pending'
                                          ? const Color(0xFFAA731D)
                                          : r['status'] == 'rejected'
                                          ? Colors.red
                                          : teal,
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  '${r['assignment']['shift']['name']} • ${dateText(r['assignment']['work_date'])}',
                                  style: const TextStyle(
                                    color: muted,
                                    fontSize: 12,
                                  ),
                                ),
                                const SizedBox(height: 10),
                                Text(
                                  r['reason'],
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                ),
                                if (r['evidence'] != null)
                                  const Padding(
                                    padding: EdgeInsets.only(top: 12),
                                    child: StatusPill(
                                      'Có hồ sơ bằng chứng',
                                      color: navy,
                                    ),
                                  ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}

class CorrectionEditor extends StatefulWidget {
  final Json assignment;
  final Json? existing, initialEvidence;
  const CorrectionEditor({
    required this.assignment,
    this.existing,
    this.initialEvidence,
    super.key,
  });
  @override
  State<CorrectionEditor> createState() => _CorrectionEditorState();
}

class _CorrectionEditorState extends State<CorrectionEditor> {
  final key = GlobalKey<FormState>();
  final reason = TextEditingController(),
      inTime = TextEditingController(),
      outTime = TextEditingController();
  bool includeOut = false, busy = false;
  String? error;
  @override
  void initState() {
    super.initState();
    final row = widget.existing;
    final a = widget.assignment;
    String input(dynamic v) =>
        DateFormat('yyyy-MM-dd HH:mm')
            .format(DateTime.parse(v).toUtc().add(const Duration(hours: 7)));
    inTime.text = row != null
        ? input(row['requested_in'])
        : a['attendance']?['check_in'] != null
        ? input(a['attendance']['check_in'])
        : '${a['work_date']} ${a['shift']['start_time']}';
    final end = a['shift']['end_time'] as String,
        start = a['shift']['start_time'] as String;
    final endDate = DateTime.parse(a['work_date'])
        .add(Duration(days: end.compareTo(start) <= 0 ? 1 : 0));
    outTime.text = row?['requested_out'] != null
        ? input(row!['requested_out'])
        : '${DateFormat('yyyy-MM-dd').format(endDate)} $end';
    reason.text = row?['reason'] ?? '';
    includeOut = row?['requested_out'] != null;
  }

  @override
  void dispose() {
    reason.dispose();
    inTime.dispose();
    outTime.dispose();
    super.dispose();
  }

  Future<void> pick(TextEditingController controller) async {
    final initial =
        DateTime.tryParse(controller.text.replaceFirst(' ', 'T')) ??
        DateTime.now();
    final date = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(2020),
      lastDate: DateTime(2100),
    );
    if (date == null || !mounted) return;
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(initial),
    );
    if (time != null) {
      controller.text =
          '${DateFormat('yyyy-MM-dd').format(date)} ${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}';
    }
  }

  Future<void> save() async {
    if (!key.currentState!.validate()) return;
    setState(() {
      busy = true;
      error = null;
    });
    String utc(String input) =>
        DateTime.parse('${input.replaceFirst(' ', 'T')}+07:00')
            .toUtc()
            .toIso8601String();
    try {
      await context.read<Session>().api!.call(
        '/corrections${widget.existing == null ? '' : '/${widget.existing!['id']}'}',
        method: widget.existing == null ? 'POST' : 'PUT',
        body: {
          'assignment_id': widget.assignment['id'],
          'requested_in': utc(inTime.text),
          'requested_out': includeOut ? utc(outTime.text) : null,
          'reason': reason.text.trim(),
          if (widget.initialEvidence != null)
            'evidence': widget.initialEvidence,
        },
      );
      if (mounted) {
        toast(context, 'Đã lưu yêu cầu. Quản trị viên sẽ xem xét.');
        Navigator.pop(context, true);
      }
    } catch (e) {
      if (mounted) setState(() => error = '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text(
        widget.existing == null ? 'Gửi giải trình' : 'Sửa giải trình',
      ),
    ),
    body: Form(
      key: key,
      child: ListView(
        padding: const EdgeInsets.all(22),
        children: [
          Text(
            '${widget.assignment['shift']['name']} • ${dateText(widget.assignment['work_date'])}',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          const Text(
            'Đề xuất thời gian thực tế theo giờ Việt Nam (GMT+7). Yêu cầu chỉ thay đổi bảng công sau khi quản trị viên duyệt.',
            style: TextStyle(color: muted),
          ),
          const SizedBox(height: 24),
          TextFormField(
            controller: inTime,
            readOnly: true,
            onTap: busy ? null : () => pick(inTime),
            decoration: const InputDecoration(
              labelText: 'Giờ vào đề xuất',
              suffixIcon: Icon(Icons.calendar_month_outlined),
            ),
          ),
          const SizedBox(height: 12),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Đề xuất cả giờ ra'),
            value: includeOut,
            onChanged: busy ? null : (v) => setState(() => includeOut = v),
          ),
          if (includeOut) ...[
            TextFormField(
              controller: outTime,
              readOnly: true,
              onTap: busy ? null : () => pick(outTime),
              decoration: const InputDecoration(
                labelText: 'Giờ ra đề xuất',
                suffixIcon: Icon(Icons.calendar_month_outlined),
              ),
            ),
            const SizedBox(height: 16),
          ],
          TextFormField(
            controller: reason,
            maxLines: 5,
            maxLength: 1000,
            decoration: const InputDecoration(
              labelText: 'Lý do và hoàn cảnh thực tế',
              alignLabelWithHint: true,
            ),
            validator: (v) => (v?.trim().length ?? 0) >= 10
                ? null
                : 'Vui lòng giải thích ít nhất 10 ký tự',
          ),
          if (widget.initialEvidence != null)
            const Padding(
              padding: EdgeInsets.only(bottom: 18),
              child: StatusPill(
                'Đính kèm vị trí, QR và mẫu chuyển động đã lấy',
              ),
            ),
          if (error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Text(error!, style: const TextStyle(color: Colors.red)),
            ),
          FilledButton.icon(
            onPressed: busy ? null : save,
            icon: const Icon(Icons.send_outlined),
            label: Text(busy ? 'Đang gửi…' : 'Lưu yêu cầu'),
          ),
        ],
      ),
    ),
  );
}

class CorrectionDetail extends StatefulWidget {
  final Json initial;
  const CorrectionDetail(this.initial, {super.key});
  @override
  State<CorrectionDetail> createState() => _CorrectionDetailState();
}

class _CorrectionDetailState extends State<CorrectionDetail> {
  late Json row;
  bool busy = false;
  @override
  void initState() {
    super.initState();
    row = widget.initial;
  }

  Future<void> review(bool approve) async {
    final note = TextEditingController();
    final result = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(approve ? 'Duyệt điều chỉnh?' : 'Từ chối yêu cầu?'),
        content: TextField(
          controller: note,
          maxLines: 3,
          decoration: const InputDecoration(
            labelText: 'Nhận xét (ít nhất 3 ký tự)',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Hủy'),
          ),
          FilledButton(
            onPressed: () {
              if (note.text.trim().length >= 3) {
                Navigator.pop(context, note.text.trim());
              }
            },
            child: const Text('Xác nhận'),
          ),
        ],
      ),
    );
    // The dialog's exit animation may still reference its controller.
    await Future<void>.delayed(const Duration(milliseconds: 250));
    note.dispose();
    if (result == null || !mounted) return;
    setState(() => busy = true);
    try {
      final value = await context.read<Session>().api!.call(
        '/corrections/${row['id']}/review',
        method: 'POST',
        body: {'decision': approve ? 'approved' : 'rejected', 'note': result},
      );
      if (mounted) setState(() => row = Json.from(value));
    } catch (e) {
      if (mounted) toast(context, '$e', error: true);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> edit() async {
    final changed = await Navigator.push<bool>(
      context,
      MaterialPageRoute(
        builder: (_) => CorrectionEditor(
          assignment: Json.from(row['assignment']),
          existing: row,
        ),
      ),
    );
    if (changed == true && mounted) Navigator.pop(context);
  }

  Future<void> remove() async {
    if (!await confirmDelete(context) || !mounted) return;
    setState(() => busy = true);
    try {
      await context.read<Session>().api!.call(
        '/corrections/${row['id']}',
        method: 'DELETE',
      );
      if (mounted) Navigator.pop(context);
    } catch (e) {
      if (mounted) toast(context, '$e', error: true);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<Session>(),
        pending = row['status'] == 'pending';
    final mine = row['user_id'] == session.user!['id'];
    return Scaffold(
      appBar: AppBar(title: const Text('Chi tiết giải trình')),
      body: ListView(
        padding: const EdgeInsets.all(22),
        children: [
          StatusPill(statusText(row['status'])),
          const SizedBox(height: 18),
          Text(
            row['employee_name'],
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 16),
          DetailLine('Ca làm', row['assignment']['shift']['name']),
          DetailLine('Ngày', dateText(row['assignment']['work_date'])),
          DetailLine(
            'Giờ vào đề xuất',
            dateText(row['requested_in'], full: true),
          ),
          DetailLine(
            'Giờ ra đề xuất',
            dateText(row['requested_out'], full: true),
          ),
          DetailLine('Gửi lúc', dateText(row['created_at'], full: true)),
          const SectionTitle('Lý do'),
          Text(row['reason']),
          if (row['evidence'] != null) ...[
            const SizedBox(height: 20),
            EvidenceView(Json.from(row['evidence'])),
          ] else
            const Padding(
              padding: EdgeInsets.only(top: 18),
              child: Text(
                'Yêu cầu này không có mẫu cảm biến đính kèm.',
                style: TextStyle(color: muted),
              ),
            ),
          if (!pending) ...[
            const SectionTitle('Kết quả xử lý'),
            Text(row['review_note']),
          ],
          const SizedBox(height: 24),
          if (pending && session.admin && !mine) ...[
            FilledButton.icon(
              onPressed: busy ? null : () => review(true),
              icon: const Icon(Icons.check_rounded),
              label: const Text('Duyệt và cập nhật bảng công'),
            ),
            const SizedBox(height: 10),
            OutlinedButton(
              onPressed: busy ? null : () => review(false),
              child: const Text('Từ chối yêu cầu'),
            ),
          ],
          if (pending && mine) ...[
            FilledButton(
              onPressed: busy ? null : edit,
              child: const Text('Sửa yêu cầu'),
            ),
            TextButton(
              onPressed: busy ? null : remove,
              child: const Text(
                'Xóa yêu cầu',
                style: TextStyle(color: Colors.red),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
