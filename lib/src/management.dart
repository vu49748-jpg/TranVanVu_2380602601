import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:qr_flutter/qr_flutter.dart';

import 'api.dart';
import 'session.dart';
import 'device.dart';
import 'theme.dart';
import 'widgets.dart';

class ResourceScreen extends StatefulWidget {
  final String resource, title;
  const ResourceScreen(this.resource, this.title, {super.key});
  @override
  State<ResourceScreen> createState() => _ResourceScreenState();
}

class _ResourceScreenState extends State<ResourceScreen> {
  List<Json>? rows;
  Object? error;
  String search = '';
  Api get api => context.read<Session>().api!;
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      final list = await api.list('/${widget.resource}');
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

  String title(Json row) => switch (widget.resource) {
    'employees' => row['full_name'],
    'assignments' => row['employee_name'],
    _ => row['name'] ?? '',
  };
  String subtitle(Json r) => switch (widget.resource) {
    'employees' =>
      '${r['username']} • ${statusText(r['role'])}\n${r['email']} • ${r['active'] ? 'Hoạt động' : 'Đã khóa'}',
    'sites' =>
      '${r['address']}\nBán kính ${r['radius_m']} m • ${r['latitude']}, ${r['longitude']}',
    'shifts' =>
      '${r['start_time']} – ${r['end_time']} • ${r['site_name']}\nCho phép trễ ${r['grace_minutes']} phút',
    'assignments' =>
      '${r['shift']['name']} • ${dateText(r['work_date'])}\n${r['shift']['start_time']} – ${r['shift']['end_time']} • ${statusText(r['attendance']?['status'])}',
    _ => '',
  };
  Future<void> edit([Json? row]) async {
    try {
      final fields = <FieldDef>[];
      final r = row ?? <String, dynamic>{};
      final resource = widget.resource;
      if (resource == 'employees') {
        fields.add(FieldDef('full_name', 'Họ và tên', value: r['full_name']));
        if (row == null) {
          fields.addAll([
            FieldDef('username', 'Tên đăng nhập'),
            FieldDef('email', 'Email', kind: 'email'),
            FieldDef(
              'password',
              'Mật khẩu ban đầu (ít nhất 8 ký tự)',
              kind: 'password',
            ),
          ]);
        } else {
          fields.addAll([
            FieldDef(
              'department',
              'Phòng ban',
              value: r['department'],
              required: false,
            ),
            FieldDef('phone', 'Điện thoại', value: r['phone'], required: false),
            FieldDef(
              'role',
              'Vai trò',
              value: r['role'],
              options: const {
                'employee': 'Nhân viên',
                'admin': 'Quản trị viên',
              },
            ),
            FieldDef(
              'active',
              'Tài khoản hoạt động',
              value: r['active'],
              kind: 'bool',
            ),
          ]);
        }
      } else if (resource == 'sites') {
        fields.addAll([
          FieldDef('name', 'Tên điểm chấm công', value: r['name']),
          FieldDef('address', 'Địa chỉ', value: r['address'], required: false),
          FieldDef('latitude', 'Vĩ độ', value: r['latitude'], kind: 'number'),
          FieldDef(
            'longitude',
            'Kinh độ',
            value: r['longitude'],
            kind: 'number',
          ),
          FieldDef(
            'radius_m',
            'Bán kính cho phép (20–2000 m)',
            value: r['radius_m'] ?? 150,
            kind: 'int',
          ),
        ]);
      } else if (resource == 'shifts') {
        final sites = await api.list('/sites');
        if (sites.isEmpty) {
          throw ApiError('Hãy tạo điểm chấm công trước khi tạo ca làm.');
        }
        fields.addAll([
          FieldDef('name', 'Tên ca làm', value: r['name']),
          FieldDef(
            'site_id',
            'Điểm chấm công',
            value: r['site_id'],
            options: {for (final x in sites) x['id']: x['name']},
          ),
          FieldDef(
            'start_time',
            'Giờ vào',
            value: r['start_time'] ?? '08:00',
            kind: 'time',
          ),
          FieldDef(
            'end_time',
            'Giờ ra',
            value: r['end_time'] ?? '17:00',
            kind: 'time',
          ),
          FieldDef(
            'grace_minutes',
            'Số phút cho phép trễ',
            value: r['grace_minutes'] ?? 10,
            kind: 'int',
          ),
        ]);
      } else if (resource == 'assignments') {
        final lists = await Future.wait([
          api.list('/employees'),
          api.list('/shifts'),
        ]);
        final employees = lists[0].where((e) => e['active'] == true).toList(),
            shifts = lists[1];
        if (employees.isEmpty || shifts.isEmpty) {
          throw ApiError('Cần nhân viên và ca làm trước khi phân ca.');
        }
        fields.addAll([
          FieldDef(
            'user_id',
            'Nhân viên',
            value: r['user_id'],
            options: {
              for (final x in employees)
                x['id']: '${x['full_name']} (${x['username']})',
            },
          ),
          FieldDef(
            'shift_id',
            'Ca làm',
            value: r['shift_id'],
            options: {
              for (final x in shifts)
                x['id']: '${x['name']} • ${x['start_time']}–${x['end_time']}',
            },
          ),
          FieldDef(
            'work_date',
            'Ngày bắt đầu ca',
            value: r['work_date'] ?? todayIso(),
            kind: 'date',
          ),
        ]);
      }
      if (!mounted) return;
      final result = await Navigator.push<bool>(
        context,
        MaterialPageRoute(
          builder: (_) => FormEditor(
            title:
                '${row == null ? 'Thêm' : 'Sửa'} ${widget.title.toLowerCase()}',
            fields: fields,
            useGps: resource == 'sites',
            onSave: (data) async {
              await api.call(
                '/$resource${row == null ? '' : '/${row['id']}'}',
                method: row == null ? 'POST' : 'PUT',
                body: data,
              );
            },
          ),
        ),
      );
      if (result == true) {
        await load();
      }
    } catch (e) {
      if (mounted) toast(context, '$e', error: true);
    }
  }

  Future<void> remove(Json row) async {
    if (!await confirmDelete(context)) return;
    try {
      await api.call('/${widget.resource}/${row['id']}', method: 'DELETE');
      await load();
    } catch (e) {
      if (mounted) toast(context, '$e', error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final filtered = (rows ?? [])
        .where(
          (r) => '${title(r)} ${subtitle(r)}'.toLowerCase().contains(
            search.toLowerCase(),
          ),
        )
        .toList();
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title),
        actions: [
          IconButton(onPressed: load, icon: const Icon(Icons.refresh_rounded)),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => edit(),
        icon: const Icon(Icons.add_rounded),
        label: const Text('Thêm mới'),
      ),
      body: error != null
          ? Failure(error!, load)
          : rows == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: load,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 110),
                children: [
                  TextField(
                    decoration: const InputDecoration(
                      hintText: 'Tìm kiếm…',
                      prefixIcon: Icon(Icons.search_rounded),
                    ),
                    onChanged: (v) => setState(() => search = v),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    child: Text(
                      '${filtered.length} bản ghi',
                      style: const TextStyle(color: muted),
                    ),
                  ),
                  if (filtered.isEmpty)
                    const EmptyState(
                      'Chưa có dữ liệu. Nhấn “Thêm mới” để bắt đầu.',
                    ),
                  ...filtered.map(
                    (r) => Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Card(
                        child: ListTile(
                          contentPadding: const EdgeInsets.fromLTRB(
                            18,
                            10,
                            6,
                            10,
                          ),
                          leading: CircleAvatar(
                            backgroundColor: teal.withValues(alpha: .1),
                            foregroundColor: teal,
                            child: Icon(switch (widget.resource) {
                              'employees' => Icons.person_outline,
                              'sites' => Icons.place_outlined,
                              'shifts' => Icons.schedule,
                              _ => Icons.calendar_month_outlined,
                            }),
                          ),
                          title: Text(
                            title(r),
                            style: const TextStyle(fontWeight: FontWeight.w700),
                          ),
                          subtitle: Text(subtitle(r)),
                          isThreeLine: true,
                          trailing: PopupMenuButton<String>(
                            onSelected: (v) {
                              if (v == 'edit') edit(r);
                              if (v == 'delete') remove(r);
                              if (v == 'qr') {
                                showDialog(
                                  context: context,
                                  builder: (_) => QrDialog(site: r),
                                );
                              }
                            },
                            itemBuilder: (_) => [
                              const PopupMenuItem(
                                value: 'edit',
                                child: Text('Chỉnh sửa'),
                              ),
                              if (widget.resource == 'sites')
                                const PopupMenuItem(
                                  value: 'qr',
                                  child: Text('Hiển thị QR chấm công'),
                                ),
                              const PopupMenuItem(
                                value: 'delete',
                                child: Text('Xóa'),
                              ),
                            ],
                          ),
                          onTap: () => edit(r),
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

class FieldDef {
  final String keyName, label, kind;
  final dynamic value;
  final bool required;
  final Map<String, String>? options;
  FieldDef(
    this.keyName,
    this.label, {
    this.kind = 'text',
    this.value,
    this.required = true,
    this.options,
  });
}

class FormEditor extends StatefulWidget {
  final String title;
  final List<FieldDef> fields;
  final Future<void> Function(Json) onSave;
  final bool useGps;
  const FormEditor({
    required this.title,
    required this.fields,
    required this.onSave,
    this.useGps = false,
    super.key,
  });
  @override
  State<FormEditor> createState() => _FormEditorState();
}

class _FormEditorState extends State<FormEditor> {
  final key = GlobalKey<FormState>();
  final controllers = <String, TextEditingController>{};
  final choices = <String, dynamic>{};
  bool busy = false;
  String? error;
  @override
  void initState() {
    super.initState();
    for (final f in widget.fields) {
      if (f.kind == 'bool') {
        choices[f.keyName] = f.value ?? true;
      } else if (f.options != null) {
        choices[f.keyName] = f.options!.containsKey(f.value) ? f.value : null;
      } else {
        controllers[f.keyName] = TextEditingController(
          text: '${f.value ?? ''}',
        );
      }
    }
  }

  @override
  void dispose() {
    for (final c in controllers.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> save() async {
    if (!key.currentState!.validate()) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final data = <String, dynamic>{};
      for (final f in widget.fields) {
        if (choices.containsKey(f.keyName)) {
          data[f.keyName] = choices[f.keyName];
        } else {
          final text = controllers[f.keyName]!.text.trim();
          data[f.keyName] = f.kind == 'int'
              ? int.parse(text)
              : f.kind == 'number'
              ? double.parse(text)
              : text;
        }
      }
      await widget.onSave(data);
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) setState(() => error = '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> gps() async {
    setState(() => busy = true);
    try {
      final p = await capturePosition();
      if (mounted) {
        controllers['latitude']!.text = p.latitude.toString();
        controllers['longitude']!.text = p.longitude.toString();
      }
    } catch (e) {
      if (mounted) toast(context, '$e', error: true);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> pick(FieldDef field) async {
    final c = controllers[field.keyName]!;
    if (field.kind == 'date') {
      final d = await showDatePicker(
        context: context,
        initialDate: DateTime.tryParse(c.text) ?? DateTime.now(),
        firstDate: DateTime(2020),
        lastDate: DateTime(2100),
      );
      if (d != null) {
        c.text =
            '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
      }
    } else {
      final parts = c.text.split(':');
      final t = await showTimePicker(
        context: context,
        initialTime: TimeOfDay(
          hour: int.tryParse(parts.first) ?? 8,
          minute: int.tryParse(parts.last) ?? 0,
        ),
      );
      if (t != null) {
        c.text =
            '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(widget.title)),
    body: Form(
      key: key,
      child: ListView(
        padding: const EdgeInsets.all(22),
        children: [
          if (widget.useGps)
            Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: OutlinedButton.icon(
                onPressed: busy ? null : gps,
                icon: const Icon(Icons.my_location_rounded),
                label: const Text('Lấy tọa độ hiện tại'),
              ),
            ),
          ...widget.fields.map(
            (f) => Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: f.kind == 'bool'
                  ? SwitchListTile(
                      title: Text(f.label),
                      value: choices[f.keyName] == true,
                      onChanged: busy
                          ? null
                          : (v) => setState(() => choices[f.keyName] = v),
                    )
                  : f.options != null
                  ? DropdownButtonFormField<String>(
                      initialValue: choices[f.keyName],
                      isExpanded: true,
                      decoration: InputDecoration(labelText: f.label),
                      items: f.options!.entries
                          .map(
                            (e) => DropdownMenuItem(
                              value: e.key,
                              child: Text(
                                e.value,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          )
                          .toList(),
                      onChanged: busy ? null : (v) => choices[f.keyName] = v,
                      validator: (v) => v == null
                          ? 'Hãy chọn ${f.label.toLowerCase()}'
                          : null,
                    )
                  : TextFormField(
                      controller: controllers[f.keyName],
                      enabled: !busy,
                      obscureText: f.kind == 'password',
                      readOnly: f.kind == 'date' || f.kind == 'time',
                      onTap: f.kind == 'date' || f.kind == 'time'
                          ? () => pick(f)
                          : null,
                      keyboardType: f.kind == 'int' || f.kind == 'number'
                          ? const TextInputType.numberWithOptions(
                              decimal: true,
                              signed: true,
                            )
                          : f.kind == 'email'
                          ? TextInputType.emailAddress
                          : TextInputType.text,
                      decoration: InputDecoration(labelText: f.label),
                      validator: (value) {
                        final v = value?.trim() ?? '';
                        if (f.required && v.isEmpty) {
                          return 'Vui lòng nhập ${f.label.toLowerCase()}';
                        }
                        if (f.kind == 'int' && int.tryParse(v) == null) {
                          return 'Nhập một số nguyên';
                        }
                        if (f.kind == 'number' &&
                            (double.tryParse(v)?.isFinite != true)) {
                          return 'Nhập số hợp lệ';
                        }
                        if (f.kind == 'password' && v.length < 8) {
                          return 'Mật khẩu ít nhất 8 ký tự';
                        }
                        return null;
                      },
                    ),
            ),
          ),
          if (error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Text(error!, style: const TextStyle(color: Colors.red)),
            ),
          FilledButton.icon(
            onPressed: busy ? null : save,
            icon: const Icon(Icons.check_rounded),
            label: Text(busy ? 'Đang xử lý…' : 'Lưu dữ liệu'),
          ),
        ],
      ),
    ),
  );
}

class QrDialog extends StatefulWidget {
  final Json site;
  const QrDialog({required this.site, super.key});
  @override
  State<QrDialog> createState() => _QrDialogState();
}

class _QrDialogState extends State<QrDialog> {
  String? token, error;
  Timer? timer;
  int seconds = 0;
  bool fetching = false;
  @override
  void initState() {
    super.initState();
    refresh();
    timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      setState(() => seconds = seconds > 0 ? seconds - 1 : 0);
      if (seconds <= 30 && error == null) refresh();
    });
  }

  @override
  void dispose() {
    timer?.cancel();
    super.dispose();
  }

  Future<void> refresh() async {
    if (fetching) return;
    fetching = true;
    try {
      final data = await context.read<Session>().api!.call(
        '/sites/${widget.site['id']}/qr',
      );
      if (mounted) {
        setState(() {
          token = data['token'];
          seconds = data['expires_in'];
          error = null;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          token = null;
          error = '$e';
        });
      }
    } finally {
      fetching = false;
    }
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(widget.site['name']),
    content: SizedBox(
      width: 280,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (error != null)
            Text(error!)
          else if (token == null)
            const CircularProgressIndicator()
          else if (seconds > 0)
            Container(
              color: Colors.white,
              padding: const EdgeInsets.all(8),
              child: QrImageView(
                data: token!,
                size: 240,
                backgroundColor: Colors.white,
              ),
            )
          else
            const Text('QR đã hết hạn. Hãy làm mới.'),
          const SizedBox(height: 14),
          Text('Mã còn ${seconds}s • tự làm mới'),
          const SizedBox(height: 8),
          const Text(
            'Nhân viên dùng camera quét mã này tại điểm chấm công.',
            style: TextStyle(color: muted, fontSize: 12),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    ),
    actions: [
      TextButton(onPressed: refresh, child: const Text('Làm mới')),
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Đóng'),
      ),
    ],
  );
}
