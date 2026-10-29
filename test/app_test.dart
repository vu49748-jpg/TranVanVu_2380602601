import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:tranvanvu_2380602601/src/api.dart';
import 'package:tranvanvu_2380602601/src/auth.dart';
import 'package:tranvanvu_2380602601/src/session.dart';
import 'package:tranvanvu_2380602601/src/theme.dart';
import 'package:tranvanvu_2380602601/src/widgets.dart';

void main() {
  test('Only public HTTPS server addresses are accepted', () {
    expect(validServer('https://attendance.onrender.com'), isTrue);
    for (final url in [
      'http://attendance.onrender.com',
      'https://localhost',
      'https://127.0.0.1',
      'https://192.168.1.10',
      'https://10.0.2.2',
      'https://172.16.0.1',
      'https://[::1]',
      'https://user:password@example.com',
      'https://example.com?token=secret',
    ]) {
      expect(validServer(url), isFalse, reason: url);
    }
  });
  test('Business times always use UTC+7', () {
    expect(clockText('2026-10-29T08:00:00Z'), '15:00');
    expect(dateText('2026-10-29'), '29/10/2026');
    expect(dateText('2026-10-29T18:00:00Z'), '30/10/2026');
    expect(clockText(null), '—');
  });
  testWidgets(
    'Small Android screen shows login, registration and validation without overflow',
    (tester) async {
      tester.view.physicalSize = const Size(360, 720);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(
        ChangeNotifierProvider(
          create: (_) => Session()..loading = false,
          child: MaterialApp(theme: appTheme, home: const AuthScreen()),
        ),
      );
      expect(find.text('Đăng nhập & nhận OTP'), findsOneWidget);
      await tester.tap(find.text('Đăng nhập & nhận OTP'));
      await tester.pumpAndSettle();
      expect(
        find.text('Dùng 3–40 chữ không dấu, số hoặc dấu _'),
        findsOneWidget,
      );
      await tester.ensureVisible(find.text('Chưa có tài khoản? Đăng ký'));
      await tester.tap(find.text('Chưa có tài khoản? Đăng ký'));
      await tester.pumpAndSettle();
      expect(find.text('Họ và tên'), findsOneWidget);
      expect(find.text('Email'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );
}
