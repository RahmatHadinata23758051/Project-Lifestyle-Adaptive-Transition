import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/theme/app_theme.dart';
import 'presentation/screens/daily_plan_screen.dart';

void main() {
  runApp(const ChronosApp());
}

class ChronosApp extends StatelessWidget {
  const ChronosApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ProviderScope(
      child: MaterialApp(
        title: 'Project Chronos',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.lightTheme,
        darkTheme: AppTheme.darkTheme,
        themeMode: ThemeMode.system,
        home: const DailyPlanScreen(),
      ),
    );
  }
}
