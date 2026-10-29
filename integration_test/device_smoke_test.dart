import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:tranvanvu_2380602601/src/checkin.dart';
import 'package:tranvanvu_2380602601/src/theme.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets('Real Android sensor samples and secure storage', (tester) async {
    const storage = FlutterSecureStorage();
    await storage.write(
      key: 'device_smoke_only',
      value: 'temporary-test-value',
    );
    expect(
      await storage.read(key: 'device_smoke_only'),
      'temporary-test-value',
    );
    await storage.delete(key: 'device_smoke_only');
    await tester.pumpWidget(
      MaterialApp(theme: appTheme, home: const MotionScreen()),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Bắt đầu đo'));
    await tester.pump();
    await tester.runAsync(
      () => Future<void>.delayed(const Duration(seconds: 5)),
    );
    await tester.pumpAndSettle();
    expect(find.text('Kết quả đo'), findsOneWidget);
    expect(find.text('Số mẫu'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
