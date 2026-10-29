import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import 'api.dart';
import 'session.dart';
import 'theme.dart';
import 'widgets.dart';

class BrandMark extends StatelessWidget {
  const BrandMark({super.key});
  @override
  Widget build(BuildContext context) => Row(
    children: [
      Container(
        width: 46,
        height: 46,
        decoration: BoxDecoration(
          color: teal,
          borderRadius: BorderRadius.circular(15),
        ),
        child: const Icon(
          Icons.schedule_rounded,
          color: Colors.white,
          size: 31,
        ),
      ),
      const SizedBox(width: 12),
      const Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'VŨ • CHẤM CÔNG',
              style: TextStyle(
                fontWeight: FontWeight.w900,
                letterSpacing: 1,
                color: navy,
              ),
            ),
            Text(
              'Mỗi ca làm, một dấu ấn.',
              style: TextStyle(color: muted, fontSize: 11),
            ),
          ],
        ),
      ),
    ],
  );
}

class ServerScreen extends StatefulWidget {
  const ServerScreen({super.key});
  @override
  State<ServerScreen> createState() => _ServerScreenState();
}

class _ServerScreenState extends State<ServerScreen> {
  final url = TextEditingController();
  bool busy = false;
  String? error;
  @override
  void dispose() {
    url.dispose();
    super.dispose();
  }

  Future<void> connect() async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await context.read<Session>().connect(url.text.trim());
    } catch (e) {
      if (mounted) setState(() => error = '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: SafeArea(
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(28),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 460),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const BrandMark(),
                const SizedBox(height: 32),
                Text(
                  'Kết nối để\nbắt đầu ca mới.',
                  style: Theme.of(context).textTheme.headlineLarge,
                ),
                const SizedBox(height: 14),
                const Text(
                  'Nhập địa chỉ máy chủ chấm công do quản trị viên cung cấp. Thiết lập một lần trên thiết bị này.',
                  style: TextStyle(color: muted),
                ),
                const SizedBox(height: 28),
                TextField(
                  controller: url,
                  keyboardType: TextInputType.url,
                  autocorrect: false,
                  decoration: const InputDecoration(
                    labelText: 'Địa chỉ API HTTPS',
                    hintText: 'https://ten-may-chu.onrender.com',
                  ),
                ),
                if (error != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: Text(
                      error!,
                      style: const TextStyle(color: Colors.red),
                    ),
                  ),
                const SizedBox(height: 20),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: busy ? null : connect,
                    icon: const Icon(Icons.link_rounded),
                    label: Text(
                      busy ? 'Đang kiểm tra kết nối…' : 'Kết nối máy chủ',
                    ),
                  ),
                ),
                const SizedBox(height: 28),
                const Text(
                  'TranVanVu_2380602601\nNhóm 7 • Ứng dụng chấm công nhân viên',
                  style: TextStyle(color: muted, fontSize: 12),
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});
  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final form = GlobalKey<FormState>();
  final username = TextEditingController(),
      password = TextEditingController(),
      email = TextEditingController(),
      name = TextEditingController(),
      code = TextEditingController();
  bool registering = false, busy = false, obscured = true;
  Json? challenge;
  String? error;
  int seconds = 0;
  Timer? timer;
  @override
  void dispose() {
    for (final c in [username, password, email, name, code]) {
      c.dispose();
    }
    timer?.cancel();
    super.dispose();
  }

  void countdown() {
    seconds = 60;
    timer?.cancel();
    timer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (!mounted || seconds <= 1) {
        t.cancel();
      }
      if (mounted) setState(() => seconds = seconds > 0 ? seconds - 1 : 0);
    });
  }

  Future<void> submit() async {
    if (!form.currentState!.validate()) return;
    setState(() {
      busy = true;
      error = null;
    });
    final session = context.read<Session>();
    try {
      if (challenge != null) {
        final result = Json.from(
          await session.api!.call(
            '/auth/verify',
            method: 'POST',
            body: {
              'challenge_id': challenge!['challenge_id'],
              'code': code.text.trim(),
            },
          ),
        );
        if (result['access_token'] != null) {
          await session.authenticate(result);
        } else if (mounted) {
          setState(() {
            challenge = null;
            registering = false;
            code.clear();
          });
          toast(context, result['message']);
        }
      } else {
        final result = await session.api!.call(
          registering ? '/auth/register' : '/auth/login',
          method: 'POST',
          body: {
            'username': username.text.trim(),
            'password': password.text,
            if (registering) 'email': email.text.trim(),
            if (registering) 'full_name': name.text.trim(),
          },
        );
        if (mounted) {
          setState(() {
            challenge = Json.from(result);
            code.clear();
          });
          countdown();
        }
      }
    } catch (e) {
      if (mounted) setState(() => error = '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> resend() async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await context.read<Session>().api!.call(
        '/auth/resend',
        method: 'POST',
        body: {'challenge_id': challenge!['challenge_id']},
      );
      if (mounted) {
        countdown();
        toast(context, 'Đã gửi lại mã đến email.');
      }
    } catch (e) {
      if (mounted) setState(() => error = '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: SafeArea(
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(26),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 460),
            child: Form(
              key: form,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const BrandMark(),
                  const SizedBox(height: 34),
                  Text(
                    challenge != null
                        ? 'Xác nhận\nđó là bạn.'
                        : registering
                        ? 'Cùng bắt đầu\nngày làm việc.'
                        : 'Chào bạn,\nsẵn sàng ca mới?',
                    style: Theme.of(context).textTheme.headlineLarge,
                  ),
                  const SizedBox(height: 12),
                  Text(
                    challenge != null
                        ? 'Mã 6 số đã gửi đến ${challenge!['email_hint']}. Có hiệu lực 10 phút; kiểm tra cả thư rác.'
                        : registering
                        ? 'Tạo tài khoản nhân viên bằng email. Quản trị viên sẽ phân ca cho bạn.'
                        : 'Đăng nhập bằng mật khẩu và mã xác thực email.',
                    style: const TextStyle(color: muted),
                  ),
                  const SizedBox(height: 26),
                  if (challenge != null)
                    TextFormField(
                      controller: code,
                      autofocus: true,
                      keyboardType: TextInputType.number,
                      inputFormatters: [
                        FilteringTextInputFormatter.digitsOnly,
                        LengthLimitingTextInputFormatter(6),
                      ],
                      autofillHints: const [AutofillHints.oneTimeCode],
                      style: const TextStyle(
                        fontSize: 25,
                        letterSpacing: 9,
                        fontWeight: FontWeight.w700,
                      ),
                      decoration: const InputDecoration(
                        labelText: 'Mã xác thực',
                        prefixIcon: Icon(Icons.verified_user_outlined),
                      ),
                      validator: (v) => RegExp(r'^\d{6}$').hasMatch(v ?? '')
                          ? null
                          : 'Nhập đủ mã gồm 6 số',
                    )
                  else ...[
                    if (registering) ...[
                      TextFormField(
                        controller: name,
                        decoration: const InputDecoration(
                          labelText: 'Họ và tên',
                          prefixIcon: Icon(Icons.badge_outlined),
                        ),
                        validator: (v) =>
                            (v?.trim().length ?? 0) >= 2 ? null : 'Nhập họ tên',
                      ),
                      const SizedBox(height: 14),
                      TextFormField(
                        controller: email,
                        keyboardType: TextInputType.emailAddress,
                        autocorrect: false,
                        decoration: const InputDecoration(
                          labelText: 'Email',
                          prefixIcon: Icon(Icons.alternate_email_rounded),
                        ),
                        validator: (v) =>
                            RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
                                .hasMatch(v?.trim() ?? '')
                            ? null
                            : 'Email chưa hợp lệ',
                      ),
                      const SizedBox(height: 14),
                    ],
                    TextFormField(
                      controller: username,
                      autocorrect: false,
                      decoration: const InputDecoration(
                        labelText: 'Tên đăng nhập',
                        prefixIcon: Icon(Icons.person_outline_rounded),
                      ),
                      validator: (v) =>
                          RegExp(r'^[a-zA-Z0-9_]{3,40}$')
                              .hasMatch(v?.trim() ?? '')
                          ? null
                          : 'Dùng 3–40 chữ không dấu, số hoặc dấu _',
                    ),
                    const SizedBox(height: 14),
                    TextFormField(
                      controller: password,
                      obscureText: obscured,
                      decoration: InputDecoration(
                        labelText: 'Mật khẩu',
                        prefixIcon: const Icon(Icons.lock_outline_rounded),
                        suffixIcon: IconButton(
                          onPressed: () => setState(() => obscured = !obscured),
                          icon: Icon(
                            obscured
                                ? Icons.visibility_off_outlined
                                : Icons.visibility_outlined,
                          ),
                        ),
                      ),
                      validator: (v) =>
                          (v?.length ?? 0) >= (registering ? 8 : 1)
                          ? null
                          : 'Mật khẩu cần ít nhất 8 ký tự',
                    ),
                  ],
                  if (error != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 14),
                      child: Text(
                        error!,
                        style: const TextStyle(color: Color(0xFFAD3939)),
                      ),
                    ),
                  const SizedBox(height: 22),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      onPressed: busy ? null : submit,
                      icon: const Icon(Icons.arrow_forward_rounded),
                      label: Text(
                        busy
                            ? 'Đang xử lý…'
                            : challenge != null
                            ? 'Xác thực OTP'
                            : registering
                            ? 'Đăng ký qua email'
                            : 'Đăng nhập & nhận OTP',
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Center(
                    child: challenge != null
                        ? Column(
                            children: [
                              TextButton(
                                onPressed: busy || seconds > 0 ? null : resend,
                                child: Text(
                                  seconds > 0
                                      ? 'Gửi lại mã sau ${seconds}s'
                                      : 'Gửi lại mã OTP',
                                ),
                              ),
                              TextButton(
                                onPressed: busy
                                    ? null
                                    : () => setState(() {
                                        challenge = null;
                                        error = null;
                                      }),
                                child: const Text('Quay lại'),
                              ),
                            ],
                          )
                        : TextButton(
                            onPressed: busy
                                ? null
                                : () => setState(() {
                                    registering = !registering;
                                    error = null;
                                    form.currentState?.reset();
                                  }),
                            child: Text(
                              registering
                                  ? 'Đã có tài khoản? Đăng nhập'
                                  : 'Chưa có tài khoản? Đăng ký',
                            ),
                          ),
                  ),
                  const SizedBox(height: 22),
                  Center(
                    child: TextButton(
                      onPressed: busy
                          ? null
                          : context.read<Session>().changeServer,
                      child: const Text(
                        'Thiết lập kết nối',
                        style: TextStyle(color: muted, fontSize: 12),
                      ),
                    ),
                  ),
                  const Center(
                    child: Text(
                      'TranVanVu_2380602601',
                      style: TextStyle(color: muted, fontSize: 10),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    ),
  );
}
