import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/datasources/api_client.dart';

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient();
});

class OnboardingState {
  final int currentStep;
  final String email;
  final String bedtime;
  final String wakeTime;
  final double weeklyFoodBudget;
  final String targetWakeTime;
  final String targetBedtime;
  final int durationDays;
  final int? effectiveDurationDays;
  final List<Map<String, dynamic>> constraints;
  final Map<String, dynamic>? feasibilityResult;
  final bool isLoading;
  final String? errorMessage;
  final String? createdRoadmapId;

  const OnboardingState({
    this.currentStep = 0,
    this.email = 'user@chronos.local',
    this.bedtime = '02:00',
    this.wakeTime = '10:00',
    this.weeklyFoodBudget = 350000.0,
    this.targetWakeTime = '07:00',
    this.targetBedtime = '23:00',
    this.durationDays = 30,
    this.effectiveDurationDays,
    this.constraints = const [],
    this.feasibilityResult,
    this.isLoading = false,
    this.errorMessage,
    this.createdRoadmapId,
  });

  OnboardingState copyWith({
    int? currentStep,
    String? email,
    String? bedtime,
    String? wakeTime,
    double? weeklyFoodBudget,
    String? targetWakeTime,
    String? targetBedtime,
    int? durationDays,
    int? effectiveDurationDays,
    List<Map<String, dynamic>>? constraints,
    Map<String, dynamic>? feasibilityResult,
    bool? isLoading,
    String? errorMessage,
    String? createdRoadmapId,
  }) {
    return OnboardingState(
      currentStep: currentStep ?? this.currentStep,
      email: email ?? this.email,
      bedtime: bedtime ?? this.bedtime,
      wakeTime: wakeTime ?? this.wakeTime,
      weeklyFoodBudget: weeklyFoodBudget ?? this.weeklyFoodBudget,
      targetWakeTime: targetWakeTime ?? this.targetWakeTime,
      targetBedtime: targetBedtime ?? this.targetBedtime,
      durationDays: durationDays ?? this.durationDays,
      effectiveDurationDays: effectiveDurationDays ?? this.effectiveDurationDays,
      constraints: constraints ?? this.constraints,
      feasibilityResult: feasibilityResult ?? this.feasibilityResult,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: errorMessage,
      createdRoadmapId: createdRoadmapId ?? this.createdRoadmapId,
    );
  }
}

final onboardingProvider = NotifierProvider<OnboardingNotifier, OnboardingState>(
  OnboardingNotifier.new,
);

class OnboardingNotifier extends Notifier<OnboardingState> {
  @override
  OnboardingState build() {
    return const OnboardingState();
  }

  void updateEmail(String email) => state = state.copyWith(email: email);
  void updateBedtime(String time) => state = state.copyWith(bedtime: time);
  void updateWakeTime(String time) => state = state.copyWith(wakeTime: time);
  void updateWeeklyFoodBudget(double budget) => state = state.copyWith(weeklyFoodBudget: budget);
  void updateTargetWakeTime(String time) => state = state.copyWith(targetWakeTime: time);
  void updateTargetBedtime(String time) => state = state.copyWith(targetBedtime: time);
  void updateDurationDays(int days) => state = state.copyWith(durationDays: days, effectiveDurationDays: days);
  void setEffectiveDurationDays(int days) => state = state.copyWith(effectiveDurationDays: days);

  void addConstraint(Map<String, dynamic> constraint) {
    state = state.copyWith(constraints: [...state.constraints, constraint]);
  }

  void removeConstraint(int index) {
    final updated = List<Map<String, dynamic>>.from(state.constraints)..removeAt(index);
    state = state.copyWith(constraints: updated);
  }

  void nextStep() {
    if (state.currentStep < 3) {
      final next = state.currentStep + 1;
      state = state.copyWith(currentStep: next);
      if (next == 3) {
        evaluateFeasibility();
      }
    }
  }

  void previousStep() {
    if (state.currentStep > 0) {
      state = state.copyWith(currentStep: state.currentStep - 1);
    }
  }

  Future<void> evaluateFeasibility() async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    try {
      final client = ref.read(apiClientProvider);
      final result = await client.checkFeasibility(
        baselineWake: state.wakeTime,
        targetWake: state.targetWakeTime,
        durationDays: state.durationDays,
        baselineBedtime: state.bedtime,
        targetBedtime: state.targetBedtime,
      );
      final recDays = result['recommended_duration_days'] as int? ?? state.durationDays;
      state = state.copyWith(
        isLoading: false,
        feasibilityResult: result,
        effectiveDurationDays: recDays,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, errorMessage: e.toString());
    }
  }

  Future<bool> submitOnboarding() async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    try {
      final client = ref.read(apiClientProvider);
      final finalDuration = state.effectiveDurationDays ?? state.durationDays;
      final response = await client.onboardUser(
        email: state.email,
        baseline: {
          'bedtime': state.bedtime,
          'wake_time': state.wakeTime,
          'weekly_food_budget': state.weeklyFoodBudget,
        },
        goal: {
          'target_wake_time': state.targetWakeTime,
          'target_bedtime': state.targetBedtime,
          'duration_days': finalDuration,
        },
        constraints: state.constraints,
      );

      final roadmapId = response['roadmap_id'] as String;
      state = state.copyWith(isLoading: false, createdRoadmapId: roadmapId);
      return true;
    } catch (e) {
      state = state.copyWith(isLoading: false, errorMessage: e.toString());
      return false;
    }
  }
}
