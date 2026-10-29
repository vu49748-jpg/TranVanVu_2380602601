import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:share_plus/share_plus.dart';

import 'api.dart';
import 'session.dart';
import 'theme.dart';
import 'widgets.dart';
import 'management.dart';
import 'checkin.dart';
import 'corrections.dart';

class AppShell extends StatefulWidget {
  const AppShell({super.key});
  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int index = 0;
  @override
  Widget build(BuildContext context) {
    final s = context.watch<Session>();
    final titles = [
      s.admin ? 'Trang quản trị' : 'Ngày làm việc',
      'Lịch & bảng công',
      s.admin ? 'Duyệt giải trình' : 'Yêu cầu của tôi',
      'Tài khoản',
    ];
    return Scaffold(
      appBar: AppBar(
        title: Text(titles[index]),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 20),
            child: Center(child: StatusPill(s.admin ? 'ADMIN' : 'NHÂN VIÊN')),
          ),
        ],
      ),
      body: [
        const DashboardPage(),
        const HistoryPage(),
        const CorrectionsPage(),
        const AccountPage(),
      ][index],
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        onDestinationSelected: (i) => setState(() => index = i),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.grid_view_outlined),
            selectedIcon: Icon(Icons.grid_view_rounded),
            label: 'Tổng quan',
          ),
          NavigationDestination(
            icon: Icon(Icons.calendar_month_outlined),
            selectedIcon: Icon(Icons.calendar_month_rounded),
            label: 'Bảng công',
          ),
          NavigationDestination(
            icon: Icon(Icons.inbox_outlined),
            selectedIcon: Icon(Icons.inbox_rounded),
            label: 'Giải trình',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Tài khoản',
          ),
        ],
      ),
    );
  }
}

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});
  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  Json? data;
  Object? error;
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      final value = await context.read<Session>().api!.call('/dashboard');
      if (mounted) {
        setState(() {
          data = Json.from(value);
          error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => error = e);
    }
  }

  Future<void> checkin([String? id]) async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => CheckinScreen(assignmentId: id)),
    );
    await load();
  }

  Future<void> qr() async {
    try {
      final sites = await context.read<Session>().api!.list('/sites');
      if (!mounted) return;
      if (sites.isEmpty) {
        toast(context, 'Tạo điểm chấm công trước.');
        return;
      }
      final site = await showModalBottomSheet<Json>(
        context: context,
        showDragHandle: true,
        builder: (_) => SafeArea(
          child: ListView(
            shrinkWrap: true,
            children: [
              const ListTile(title: Text('Chọn điểm hiển thị QR')),
              ...sites.map(
                (s) => ListTile(
                  title: Text(s['name']),
                  leading: const Icon(Icons.qr_code_rounded),
                  onTap: () => Navigator.pop(context, s),
                ),
              ),
            ],
          ),
        ),
      );
      if (site != null && mounted) {
        await showDialog(
          context: context,
          builder: (_) => QrDialog(site: site),
        );
      }
    } catch (e) {
      if (mounted) toast(context, '$e', error: true);
    }
  }

  Future<void> resource(String path, String title) async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => ResourceScreen(path, title)),
    );
    await load();
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<Session>();
    if (error != null) return Failure(error!, load);
    if (data == null) return const Center(child: CircularProgressIndicator());
    final all = (data!['assignments'] as List)
        .map((x) => Json.from(x))
        .toList();
    final own = all.where((x) => x['user_id'] == session.user!['id']).toList();
    final rows = session.admin ? all : own;
    return RefreshIndicator(
      onRefresh: load,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(22, 12, 22, 30),
        children: [
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: navy,
              borderRadius: BorderRadius.circular(26),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.wb_sunny_outlined, size: 16, color: amber),
                    const SizedBox(width: 8),
                    Text(
                      dateText(data!['date']),
                      style: const TextStyle(
                        color: Colors.white70,
                        fontSize: 12,
                      ),
                    ),
                    const Spacer(),
                    const Text(
                      'HÔM NAY',
                      style: TextStyle(
                        color: Colors.white54,
                        fontSize: 10,
                        letterSpacing: 1,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                Text(
                  'Xin chào, ${session.user!['full_name']}.',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                    fontSize: 25,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  session.admin
                      ? 'Một nơi để theo dõi ca làm và chăm sóc đội ngũ.'
                      : 'Một ngày mới. Một ca làm trọn vẹn.',
                  style: const TextStyle(color: Colors.white70),
                ),
                const SizedBox(height: 22),
                FilledButton.icon(
                  style: FilledButton.styleFrom(
                    backgroundColor: amber,
                    foregroundColor: navy,
                  ),
                  onPressed: session.admin ? qr : () => checkin(),
                  icon: Icon(
                    session.admin ? Icons.qr_code_rounded : Icons.login_rounded,
                  ),
                  label: Text(
                    session.admin ? 'Hiển thị QR chấm công' : 'Chấm công ngay',
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          LayoutBuilder(
            builder: (context, c) => Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                stat(
                  c.maxWidth,
                  'Ca hôm nay',
                  '${data!['scheduled']}',
                  Icons.calendar_today_outlined,
                ),
                stat(
                  c.maxWidth,
                  'Đã vào ca',
                  '${data!['checked_in']}',
                  Icons.task_alt_rounded,
                ),
                stat(
                  c.maxWidth,
                  'Đi muộn',
                  '${data!['late']}',
                  Icons.schedule_rounded,
                ),
                stat(
                  c.maxWidth,
                  'Chờ duyệt',
                  '${data!['pending']}',
                  Icons.mark_email_unread_outlined,
                ),
              ],
            ),
          ),
          if (session.admin) ...[
            const SectionTitle(
              'Quản lý đội ngũ',
              subtitle: 'Thêm, xem, sửa và xóa dữ liệu',
            ),
            Card(
              child: Column(
                children: [
                  menu(
                    Icons.people_outline_rounded,
                    'Nhân viên',
                    'Tài khoản, phòng ban và phân quyền',
                    () => resource('employees', 'Nhân viên'),
                  ),
                  menu(
                    Icons.location_on_outlined,
                    'Điểm chấm công',
                    'Tọa độ, bán kính và QR',
                    () => resource('sites', 'Điểm chấm công'),
                  ),
                  menu(
                    Icons.schedule_rounded,
                    'Ca làm',
                    'Giờ vào, giờ ra và thời gian cho phép trễ',
                    () => resource('shifts', 'Ca làm'),
                  ),
                  menu(
                    Icons.event_available_outlined,
                    'Phân ca',
                    'Xếp lịch theo nhân viên và ngày',
                    () => resource('assignments', 'Phân ca'),
                  ),
                ],
              ),
            ),
          ],
          SectionTitle(
            session.admin ? 'Ca gần đây' : 'Lịch làm việc của bạn',
            subtitle: 'Hôm nay và ca đêm bắt đầu hôm qua',
            action: IconButton(
              onPressed: load,
              icon: const Icon(Icons.refresh_rounded),
            ),
          ),
          if (rows.isEmpty)
            const EmptyState(
              'Chưa có ca làm. Quản trị viên cần phân ca để bắt đầu.',
            ),
          ...rows.map(
            (a) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: AssignmentCard(
                a,
                admin: session.admin,
                onTap: () {
                  if (a['user_id'] == session.user!['id'] &&
                      a['attendance']?['check_out'] == null) {
                    checkin(a['id']);
                  } else {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => AttendanceDetail(a)),
                    );
                  }
                },
              ),
            ),
          ),
          const SectionTitle('Khám phá cảm biến'),
          Card(
            child: menu(
              Icons.sensors_rounded,
              'Đo chuyển động',
              'Xem dữ liệu gia tốc thật trong 3 giây',
              () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const MotionScreen()),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget stat(double width, String label, String value, IconData icon) =>
      SizedBox(
        width: (width - 12) / 2,
        child: Card(
          child: Padding(
            padding: const EdgeInsets.all(17),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(icon, size: 19, color: teal),
                    const Spacer(),
                    Text(
                      value,
                      style: const TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.w800,
                        color: navy,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(label, style: const TextStyle(fontSize: 12, color: muted)),
              ],
            ),
          ),
        ),
      );
  Widget menu(IconData icon, String title, String subtitle, VoidCallback tap) =>
      ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 5),
        leading: Icon(icon, color: teal),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Text(
          subtitle,
          style: const TextStyle(fontSize: 12, color: muted),
        ),
        trailing: const Icon(Icons.chevron_right_rounded, color: muted),
        onTap: tap,
      );
}

class AssignmentCard extends StatelessWidget {
  final Json a;
  final bool admin;
  final VoidCallback onTap;
  const AssignmentCard(
    this.a, {
    required this.onTap,
    this.admin = false,
    super.key,
  });
  @override
  Widget build(BuildContext context) => Card(
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(22),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    admin ? a['employee_name'] : a['shift']['name'],
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 16,
                    ),
                  ),
                ),
                StatusPill(
                  statusText(a['attendance']?['status']),
                  color: a['attendance']?['status'] == 'late'
                      ? const Color(0xFFAA731D)
                      : teal,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              '${dateText(a['work_date'])} • ${a['shift']['start_time']} – ${a['shift']['end_time']}',
              style: const TextStyle(color: muted, fontSize: 12),
            ),
            Text(
              '${a['site']['name']}${admin ? ' • ${a['shift']['name']}' : ''}',
              style: const TextStyle(color: muted, fontSize: 12),
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                const Icon(Icons.login_rounded, size: 16, color: teal),
                const SizedBox(width: 6),
                Text(clockText(a['attendance']?['check_in'])),
                const SizedBox(width: 24),
                const Icon(Icons.logout_rounded, size: 16, color: muted),
                const SizedBox(width: 6),
                Text(clockText(a['attendance']?['check_out'])),
                const Spacer(),
                const Icon(Icons.arrow_forward_rounded, size: 18, color: teal),
              ],
            ),
          ],
        ),
      ),
    ),
  );
}

class HistoryPage extends StatefulWidget {
  const HistoryPage({super.key});
  @override
  State<HistoryPage> createState() => _HistoryPageState();
}

class _HistoryPageState extends State<HistoryPage> {
  List<Json>? rows;
  Object? error;
  String filter = 'all', search = '';
  bool exporting = false;
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      final value = await context.read<Session>().api!.list('/assignments');
      if (mounted) {
        setState(() {
          rows = value;
          error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => error = e);
    }
  }

  Future<void> export() async {
    setState(() => exporting = true);
    try {
      final csv = await context.read<Session>().api!.call(
        '/reports/csv',
        type: ResponseType.plain,
      );
      if (!mounted) return;
      final box = context.findRenderObject() as RenderBox?;
      await SharePlus.instance.share(
        ShareParams(
          files: [
            XFile.fromData(
              Uint8List.fromList(utf8.encode(csv)),
              mimeType: 'text/csv',
            ),
          ],
          fileNameOverrides: const ['TranVanVu_2380602601_chamcong.csv'],
          text: 'Bảng chấm công nhân viên',
          sharePositionOrigin: box == null
              ? null
              : box.localToGlobal(Offset.zero) & box.size,
        ),
      );
    } catch (e) {
      if (mounted) toast(context, '$e', error: true);
    } finally {
      if (mounted) setState(() => exporting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final admin = context.watch<Session>().admin;
    if (error != null) return Failure(error!, load);
    if (rows == null) return const Center(child: CircularProgressIndicator());
    final list = rows!
        .where(
          (a) =>
              (filter == 'all' ||
                  filter == 'today' && a['work_date'] == todayIso() ||
                  filter == 'late' && a['attendance']?['status'] == 'late') &&
              '${a['employee_name']} ${a['shift']['name']} ${a['work_date']}'
                  .toLowerCase()
                  .contains(search.toLowerCase()),
        )
        .toList();
    double hours = 0;
    for (final a in list) {
      final i = DateTime.tryParse('${a['attendance']?['check_in']}'),
          o = DateTime.tryParse('${a['attendance']?['check_out']}');
      if (i != null && o != null) hours += o.difference(i).inSeconds / 3600;
    }
    return RefreshIndicator(
      onRefresh: load,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(22, 12, 22, 30),
        children: [
          Text(
            'Dấu ấn từng ca làm.',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 12),
          Text(
            '${list.length} ca • ${hours.toStringAsFixed(1)} giờ công đã hoàn tất',
            style: const TextStyle(color: muted),
          ),
          const SizedBox(height: 20),
          TextField(
            onChanged: (v) => setState(() => search = v),
            decoration: const InputDecoration(
              hintText: 'Tìm tên, ca hoặc yyyy-mm-dd',
              prefixIcon: Icon(Icons.search_rounded),
            ),
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            children: [
              for (final f in ['all', 'today', 'late'])
                ChoiceChip(
                  label: Text(
                    f == 'all'
                        ? 'Tất cả'
                        : f == 'today'
                        ? 'Hôm nay'
                        : 'Đi muộn',
                  ),
                  selected: filter == f,
                  onSelected: (_) => setState(() => filter = f),
                ),
            ],
          ),
          if (admin)
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: exporting ? null : export,
                icon: const Icon(Icons.download_outlined),
                label: Text(exporting ? 'Đang xuất…' : 'Xuất CSV toàn bộ'),
              ),
            ),
          const SizedBox(height: 12),
          if (list.isEmpty) const EmptyState('Chưa có ca phù hợp.'),
          ...list.map(
            (a) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: AssignmentCard(
                a,
                admin: admin,
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => AttendanceDetail(a)),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class AttendanceDetail extends StatelessWidget {
  final Json a;
  const AttendanceDetail(this.a, {super.key});
  @override
  Widget build(BuildContext context) {
    final attendance = a['attendance'];
    return Scaffold(
      appBar: AppBar(title: const Text('Chi tiết ca làm')),
      body: ListView(
        padding: const EdgeInsets.all(22),
        children: [
          Text(
            a['employee_name'],
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 16),
          DetailLine('Ca', a['shift']['name']),
          DetailLine('Ngày', dateText(a['work_date'])),
          DetailLine('Điểm', a['site']['name']),
          DetailLine(
            'Lịch làm',
            '${a['shift']['start_time']} – ${a['shift']['end_time']}',
          ),
          DetailLine(
            'Vào thực tế',
            dateText(attendance?['check_in'], full: true),
          ),
          DetailLine(
            'Ra thực tế',
            dateText(attendance?['check_out'], full: true),
          ),
          DetailLine('Trạng thái', statusText(attendance?['status'])),
          if (attendance?['in_evidence'] != null) ...[
            const SectionTitle('Bằng chứng vào ca'),
            EvidenceView(Json.from(attendance['in_evidence'])),
          ],
          if (attendance?['out_evidence'] != null) ...[
            const SectionTitle('Bằng chứng ra ca'),
            EvidenceView(Json.from(attendance['out_evidence'])),
          ],
          if (a['user_id'] == context.read<Session>().user!['id'])
            Padding(
              padding: const EdgeInsets.only(top: 24),
              child: OutlinedButton.icon(
                onPressed: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => CorrectionEditor(assignment: a),
                  ),
                ),
                icon: const Icon(Icons.edit_note),
                label: const Text('Đề nghị điều chỉnh'),
              ),
            ),
        ],
      ),
    );
  }
}

class AccountPage extends StatefulWidget {
  const AccountPage({super.key});
  @override
  State<AccountPage> createState() => _AccountPageState();
}

class _AccountPageState extends State<AccountPage> {
  bool busy = false;
  Future<void> edit() async {
    final s = context.read<Session>();
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => FormEditor(
          title: 'Hồ sơ cá nhân',
          fields: [
            FieldDef('full_name', 'Họ và tên', value: s.user!['full_name']),
            FieldDef(
              'phone',
              'Điện thoại',
              value: s.user!['phone'],
              required: false,
            ),
          ],
          onSave: s.updateProfile,
        ),
      ),
    );
  }

  Future<void> logout() async {
    setState(() => busy = true);
    try {
      await context.read<Session>().logout();
    } catch (e) {
      if (mounted) toast(context, '$e', error: true);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = context.watch<Session>(), u = s.user!;
    return ListView(
      padding: const EdgeInsets.all(22),
      children: [
        const SizedBox(height: 10),
        Center(
          child: CircleAvatar(
            radius: 40,
            backgroundColor: teal.withValues(alpha: .12),
            child: Text(
              (u['full_name'] as String)
                  .trim()
                  .split(' ')
                  .last
                  .characters
                  .first,
              style: const TextStyle(
                fontSize: 34,
                color: teal,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ),
        const SizedBox(height: 16),
        Text(
          u['full_name'],
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const SizedBox(height: 6),
        Text(
          u['email'],
          textAlign: TextAlign.center,
          style: const TextStyle(color: muted),
        ),
        const SizedBox(height: 26),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              children: [
                DetailLine('Tên đăng nhập', u['username']),
                DetailLine('Vai trò', statusText(u['role'])),
                DetailLine('Phòng ban', '${u['department'] ?? ''}'),
                DetailLine('Điện thoại', '${u['phone'] ?? ''}'),
                const SizedBox(height: 10),
                OutlinedButton.icon(
                  onPressed: edit,
                  icon: const Icon(Icons.edit_outlined),
                  label: const Text('Sửa hồ sơ'),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 18),
        if (s.admin)
          Card(
            child: ListTile(
              leading: const Icon(Icons.history_rounded, color: teal),
              title: const Text('Nhật ký thao tác'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const AuditScreen()),
              ),
            ),
          ),
        const SizedBox(height: 24),
        OutlinedButton.icon(
          onPressed: busy ? null : logout,
          icon: const Icon(Icons.logout_rounded),
          label: Text(busy ? 'Đang đăng xuất…' : 'Đăng xuất'),
        ),
        const SizedBox(height: 26),
        const Text(
          'TranVanVu_2380602601\nTrần Văn Vũ • 2380602601 • Nhóm 7\nỨng dụng Flutter chấm công nhân viên',
          textAlign: TextAlign.center,
          style: TextStyle(color: muted, fontSize: 12),
        ),
      ],
    );
  }
}

class AuditScreen extends StatefulWidget {
  const AuditScreen({super.key});
  @override
  State<AuditScreen> createState() => _AuditScreenState();
}

class _AuditScreenState extends State<AuditScreen> {
  List<Json>? rows;
  Object? error;
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      final list = await context.read<Session>().api!.list('/audit');
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

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Nhật ký thao tác')),
    body: error != null
        ? Failure(error!, load)
        : rows == null
        ? const Center(child: CircularProgressIndicator())
        : RefreshIndicator(
            onRefresh: load,
            child: ListView(
              padding: const EdgeInsets.all(22),
              children: [
                if (rows!.isEmpty) const EmptyState('Chưa có thao tác.'),
                ...rows!.map(
                  (r) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Card(
                      child: ListTile(
                        leading: const Icon(Icons.history_rounded, color: teal),
                        title: Text(
                          r['action'],
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                        subtitle: Text(
                          '${r['actor_name']}\n${dateText(r['created_at'], full: true)}',
                        ),
                        isThreeLine: true,
                        onTap: () => showDialog(
                          context: context,
                          builder: (_) => AlertDialog(
                            title: Text(r['action']),
                            content: SingleChildScrollView(
                              child: SelectableText(
                                const JsonEncoder.withIndent('  ')
                                    .convert(r['details']),
                              ),
                            ),
                            actions: [
                              TextButton(
                                onPressed: () => Navigator.pop(context),
                                child: const Text('Đóng'),
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
