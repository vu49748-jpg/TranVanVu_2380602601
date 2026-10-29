import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:tranvanvu_2380602601/main.dart';
import 'package:tranvanvu_2380602601/src/auth.dart';
import 'package:tranvanvu_2380602601/src/session.dart';

void main() {
  testWidgets(
    'Vietnamese time input accepts 23:59 when Android uses a 12-hour clock',
    (tester) async {
      tester.binding.platformDispatcher.alwaysUse24HourFormatTestValue = false;
      addTearDown(
        tester.binding.platformDispatcher.clearAlwaysUse24HourTestValue,
      );
      await tester.pumpWidget(
        ChangeNotifierProvider(
          create: (_) => Session()..loading = false,
          child: const AttendanceApp(),
        ),
      );
      await tester.pumpAndSettle();

      final selected = showTimePicker(
        context: tester.element(find.byType(ServerScreen)),
        initialTime: const TimeOfDay(hour: 8, minute: 0),
        initialEntryMode: TimePickerEntryMode.input,
      );
      await tester.pumpAndSettle();
      final dialog = find.byType(TimePickerDialog);
      final fields = find.descendant(
        of: dialog,
        matching: find.byType(TextField),
      );
      expect(fields, findsNWidgets(2));
      final labels = MaterialLocalizations.of(tester.element(dialog));
      await tester.enterText(fields.at(0), '23');
      await tester.enterText(fields.at(1), '59');
      await tester.tap(find.text(labels.okButtonLabel));
      await tester.pumpAndSettle();

      expect(find.text(labels.invalidTimeLabel), findsNothing);
      expect(dialog, findsNothing);
      expect(await selected, const TimeOfDay(hour: 23, minute: 59));
      expect(tester.takeException(), isNull);
    },
  );
}
