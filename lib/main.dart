import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';

import 'src/session.dart';
import 'src/theme.dart';
import 'src/auth.dart';
import 'src/shell.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    ChangeNotifierProvider(
      create: (_) => Session()..boot(),
      child: const AttendanceApp(),
    ),
  );
}

class AttendanceApp extends StatelessWidget {
  const AttendanceApp({super.key});
  @override
  Widget build(BuildContext context) {
    final s = context.watch<Session>();
    return MaterialApp(
      key: ValueKey(
        '${s.api?.dio.options.baseUrl}|${s.user?['id'] ?? 'guest'}',
      ),
      locale: const Locale('vi'),
      supportedLocales: const [Locale('vi'), Locale('en')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      title: 'TranVanVu_2380602601',
      debugShowCheckedModeBanner: false,
      theme: appTheme,
      home: s.loading
          ? const Scaffold(body: Center(child: CircularProgressIndicator()))
          : s.api == null
          ? const ServerScreen()
          : s.bootError != null
          ? Scaffold(
              body: SafeArea(
                child: Center(
                  child: Padding(
                    padding: const EdgeInsets.all(28),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.cloud_off_rounded, size: 60),
                        const SizedBox(height: 20),
                        Text(s.bootError!, textAlign: TextAlign.center),
                        const SizedBox(height: 20),
                        FilledButton(
                          onPressed: s.boot,
                          child: const Text('Thử lại'),
                        ),
                        TextButton(
                          onPressed: s.changeServer,
                          child: const Text('Thiết lập máy chủ'),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            )
          : s.user == null
          ? const AuthScreen()
          : const AppShell(),
    );
  }
}
