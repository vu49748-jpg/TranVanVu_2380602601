import 'package:flutter/material.dart';

const navy = Color(0xFF142D36),
    teal = Color(0xFF087F75),
    canvas = Color(0xFFF3F6F5),
    muted = Color(0xFF6C7F83),
    amber = Color(0xFFE8AD49);
final appTheme = ThemeData(
  useMaterial3: true,
  scaffoldBackgroundColor: canvas,
  colorScheme: ColorScheme.fromSeed(
    seedColor: teal,
    primary: teal,
    secondary: navy,
    surface: Colors.white,
  ),
  appBarTheme: const AppBarTheme(
    backgroundColor: canvas,
    foregroundColor: navy,
    centerTitle: false,
    elevation: 0,
  ),
  textTheme: const TextTheme(
    headlineLarge: TextStyle(
      fontSize: 32,
      fontWeight: FontWeight.w800,
      color: navy,
      letterSpacing: -1,
    ),
    headlineSmall: TextStyle(
      fontSize: 24,
      fontWeight: FontWeight.w800,
      color: navy,
    ),
    titleLarge: TextStyle(
      fontSize: 21,
      fontWeight: FontWeight.w700,
      color: navy,
    ),
    titleMedium: TextStyle(
      fontSize: 16,
      fontWeight: FontWeight.w700,
      color: navy,
    ),
    bodyMedium: TextStyle(fontSize: 14, color: navy, height: 1.45),
  ),
  inputDecorationTheme: InputDecorationTheme(
    filled: true,
    fillColor: const Color(0xFFF6F8F7),
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(16),
      borderSide: const BorderSide(color: Color(0xFFDCE5E2)),
    ),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(16),
      borderSide: const BorderSide(color: Color(0xFFDCE5E2)),
    ),
    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 17),
  ),
  filledButtonTheme: FilledButtonThemeData(
    style: FilledButton.styleFrom(
      minimumSize: const Size(0, 52),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
    ),
  ),
  cardTheme: CardThemeData(
    elevation: 0,
    color: Colors.white,
    margin: EdgeInsets.zero,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(22),
      side: const BorderSide(color: Color(0xFFE1E9E5)),
    ),
  ),
  navigationBarTheme: NavigationBarThemeData(
    backgroundColor: Colors.white,
    indicatorColor: teal.withValues(alpha: .12),
    labelTextStyle: WidgetStateProperty.all(
      const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
    ),
  ),
);
