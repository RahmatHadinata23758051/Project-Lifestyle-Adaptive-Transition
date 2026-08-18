import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:chronos/domain/models/plan_domain.dart';
import 'package:chronos/presentation/providers/daily_plan_provider.dart';
import 'package:chronos/presentation/screens/daily_plan_screen.dart';

void main() {
  group('DailyPlanNotifier Unit Tests', () {
    test('Initial state has 5 items and 0 spent', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final state = container.read(dailyPlanProvider);
      expect(state.items.length, 5);
      expect(state.completedCount, 0);
      expect(state.totalSpentToday, 0.0);
      expect(state.remainingBudget, 50000.0);
    });

    test('toggleCheckIn marks item as completed', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container.read(dailyPlanProvider.notifier).toggleCheckIn('item-1');
      final state = container.read(dailyPlanProvider);

      expect(state.items.first.status, PlanItemStatus.completed);
      expect(state.completedCount, 1);
      expect(state.items.first.actualTime, isNotNull);
    });

    test('toggleCheckIn with spending recalculates budget', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container.read(dailyPlanProvider.notifier).toggleCheckIn('item-2', spentCost: 20000.0);
      final state = container.read(dailyPlanProvider);

      expect(state.items[1].status, PlanItemStatus.completed);
      expect(state.totalSpentToday, 20000.0);
      expect(state.remainingBudget, 30000.0);
    });

    test('toggleCheckIn with isLate marks as lateCompleted', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container.read(dailyPlanProvider.notifier).toggleCheckIn('item-1', isLate: true);
      final state = container.read(dailyPlanProvider);

      expect(state.items.first.status, PlanItemStatus.lateCompleted);
      expect(state.completedCount, 1);
    });
  });

  group('DailyPlanScreen Widget Tests', () {
    testWidgets('Renders header, target pills, budget indicator, and tasks', (tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: DailyPlanScreen(),
          ),
        ),
      );

      // Verify header and target pills
      expect(find.text('Rencana Hari Ini'), findsOneWidget);
      expect(find.text('Target Bangun'), findsOneWidget);
      expect(find.text('09:45'), findsAtLeastNWidgets(1));
      expect(find.text('Target Tidur'), findsOneWidget);

      // Verify budget indicator
      expect(find.text('Alokasi Makan Hari Ini'), findsOneWidget);

      // Verify first task
      expect(find.text('Bangun & Hidrasi (Target 09:45)'), findsOneWidget);

      // Tap first task to complete
      await tester.tap(find.text('Bangun & Hidrasi (Target 09:45)'));
      await tester.pump();

      // Verify progress updated
      expect(find.text('1 / 5 Selesai'), findsOneWidget);
    });
  });
}
