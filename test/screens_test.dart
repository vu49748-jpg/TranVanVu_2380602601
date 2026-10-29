import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:tranvanvu_2380602601/src/api.dart';
import 'package:tranvanvu_2380602601/src/session.dart';
import 'package:tranvanvu_2380602601/src/shell.dart';
import 'package:tranvanvu_2380602601/src/theme.dart';

class FixtureAdapter implements HttpClientAdapter {
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    final user = {
      'id': 'employee',
      'username': 'staff',
      'email': 'staff@example.com',
      'full_name': 'Nguyễn Trần Hoàng Minh Anh',
      'role': 'employee',
      'active': true,
      'department': 'Phòng kinh doanh',
      'phone': '',
    };
    final assignment = {
      'id': 'assignment',
      'user_id': 'employee',
      'employee_name': user['full_name'],
      'work_date': '2026-10-29',
      'shift': {
        'id': 'shift',
        'name': 'Ca hành chính tại văn phòng',
        'start_time': '08:00',
        'end_time': '17:00',
        'grace_minutes': 10,
      },
      'site': {
        'id': 'site',
        'name': 'Văn phòng công ty',
        'latitude': 10.8,
        'longitude': 106.7,
        'radius_m': 150,
      },
      'attendance': null,
    };
    final data = switch (options.path) {
      '/dashboard' => {
        'date': '2026-10-29',
        'scheduled': 1,
        'checked_in': 0,
        'late': 0,
        'pending': 1,
        'assignments': [assignment],
      },
      '/assignments' => [assignment],
      '/employees' => [user],
      '/corrections' => [],
      '/audit' => [],
      _ => [],
    };
    return ResponseBody.fromString(
      jsonEncode(data),
      200,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  for (final admin in [true, false]) {
    testWidgets(
      '${admin ? 'Admin' : 'Employee'} dashboard, tabs and profile fit a narrow Android screen',
      (tester) async {
        tester.view.physicalSize = const Size(360, 740);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        final session = Session()
          ..loading = false
          ..user = {
            'id': 'employee',
            'username': 'staff',
            'email': 'staff@example.com',
            'full_name': 'Nguyễn Trần Hoàng Minh Anh',
            'role': admin ? 'admin' : 'employee',
            'department': 'Phòng kinh doanh',
            'phone': '',
          };
        session.api = Api('https://fixture.example.com');
        session.api!.dio.httpClientAdapter = FixtureAdapter();
        await tester.pumpWidget(
          ChangeNotifierProvider.value(
            value: session,
            child: MaterialApp(theme: appTheme, home: const AppShell()),
          ),
        );
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        if (admin) {
        await tester.scrollUntilVisible(find.text('Nhân viên'), 260,
          scrollable: find.byType(Scrollable).first);
          await tester.tap(find.text('Nhân viên'));
          await tester.pumpAndSettle();
          expect(find.text('Nguyễn Trần Hoàng Minh Anh'), findsOneWidget);
          expect(tester.takeException(), isNull);
          await tester.pageBack();
          await tester.pumpAndSettle();
        }
        await tester.tap(find.text('Bảng công'));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        await tester.tap(find.text('Giải trình'));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        await tester.tap(find.text('Tài khoản'));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        expect(find.text('staff@example.com'), findsOneWidget);
      },
    );
  }
}
