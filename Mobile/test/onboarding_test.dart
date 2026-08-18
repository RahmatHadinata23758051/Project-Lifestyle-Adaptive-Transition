import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:chronos/presentation/providers/onboarding_provider.dart';
import 'package:chronos/presentation/screens/onboarding_screen.dart';

void main() {
  group('OnboardingNotifier Unit Tests', () {
    test('Initial state starts at step 0', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final state = container.read(onboardingProvider);
      expect(state.currentStep, 0);
      expect(state.bedtime, '02:00');
      expect(state.wakeTime, '10:00');
      expect(state.durationDays, 30);
    });

    test('updateBedtime and updateWakeTime mutate state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container.read(onboardingProvider.notifier).updateBedtime('03:00');
      container.read(onboardingProvider.notifier).updateWakeTime('11:00');

      final state = container.read(onboardingProvider);
      expect(state.bedtime, '03:00');
      expect(state.wakeTime, '11:00');
    });

    test('addConstraint and removeConstraint work correctly', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container.read(onboardingProvider.notifier).addConstraint({
        'title': 'Kuliah Pagi',
        'category': 'UNIVERSITY',
        'day_of_week': 'MONDAY',
        'start_time': '08:00',
        'end_time': '12:00',
        'is_flexible': false,
      });

      var state = container.read(onboardingProvider);
      expect(state.constraints.length, 1);

      container.read(onboardingProvider.notifier).removeConstraint(0);
      state = container.read(onboardingProvider);
      expect(state.constraints.length, 0);
    });

    test('nextStep and previousStep navigate steps properly', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container.read(onboardingProvider.notifier).nextStep();
      expect(container.read(onboardingProvider).currentStep, 1);

      container.read(onboardingProvider.notifier).nextStep();
      expect(container.read(onboardingProvider).currentStep, 2);

      container.read(onboardingProvider.notifier).previousStep();
      expect(container.read(onboardingProvider).currentStep, 1);
    });
  });

  group('OnboardingScreen Widget Tests', () {
    testWidgets('Renders Step 1 and navigates to Step 2', (WidgetTester tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: OnboardingScreen(),
          ),
        ),
      );

      // Verify Step 1 UI
      expect(find.text('Inisiasi Pola Hidup'), findsOneWidget);
      expect(find.text('Langkah 1: Pola Hidup Saat Ini'), findsOneWidget);
      expect(find.text('Jam Tidur Saat Ini (HH:MM)'), findsOneWidget);

      // Tap Lanjutkan
      await tester.tap(find.text('Lanjutkan'));
      await tester.pumpAndSettle();

      // Verify Step 2 UI
      expect(find.text('Langkah 2: Target Impian Anda'), findsOneWidget);
      expect(find.text('Target Jam Bangun (HH:MM)'), findsOneWidget);
    });
  });
}
