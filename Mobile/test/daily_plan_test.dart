import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:chronos/domain/models/plan_domain.dart';
import 'package:chronos/presentation/providers/daily_plan_provider.dart';
import 'package:chronos/presentation/screens/daily_plan_screen.dart';

void main() {
  group('DailyPlanNotifier Unit Tests', () {
    test('Initial state has 6 items and Day 1 is Baseline Day', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final state = container.read(dailyPlanProvider);
      expect(state.items.length, 6);
      expect(state.dayNumber, 1);
      expect(state.transitionState, 'BASELINE');
      expect(state.targetWakeTime, '10:00');
      expect(state.completedCount, 0);
      expect(state.totalSpentToday, 0.0);
      expect(state.remainingBudget, 50000.0);
    });

    test('recordWakeMeasurement updates measurement status', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container.read(dailyPlanProvider.notifier).recordWakeMeasurement('09:55');
      final state = container.read(dailyPlanProvider);

      expect(state.actualWakeTime, '09:55');
      expect(state.isWakeRecorded, true);
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

      container.read(dailyPlanProvider.notifier).toggleCheckIn('item-3', spentCost: 20000.0);
      final state = container.read(dailyPlanProvider);

      expect(state.items[2].status, PlanItemStatus.completed);
      expect(state.totalSpentToday, 20000.0);
      expect(state.remainingBudget, 30000.0);
    });
  });

  group('DailyPlanScreen Widget Tests', () {
    testWidgets('Renders transition context, wake measurement card, and tasks', (tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: DailyPlanScreen(),
          ),
        ),
      );

      // Verify header and transition context
      expect(find.text('Day 1 dari 30'), findsOneWidget);
      expect(find.text('Konteks Transisi Bangun Tidur'), findsOneWidget);
      expect(find.text('PENGUKURAN BANGUN TIDUR'), findsOneWidget);

      // Verify budget indicator
      expect(find.text('Konteks Alokasi Budget Makan'), findsOneWidget);

      // Verify task item
      final questFinder = find.text('Minum 1 Gelas Air Setelah Bangun');
      expect(questFinder, findsOneWidget);

      // Tap checkbox for first item
      final checkboxFinder = find.byType(Checkbox).first;
      await tester.ensureVisible(checkboxFinder);
      await tester.tap(checkboxFinder);
      await tester.pumpAndSettle();

      // Verify progress updated
      expect(find.text('Rutinitas bebas bentrok jadwal kuliah dan kerja (1/6 selesai)'), findsOneWidget);
    });
  });
}
