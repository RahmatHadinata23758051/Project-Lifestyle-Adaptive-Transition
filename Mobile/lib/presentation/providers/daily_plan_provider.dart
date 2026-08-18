import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../domain/models/plan_domain.dart';
import '../../domain/models/plan_item_model.dart';
import 'onboarding_provider.dart';

class DailyPlanState {
  final String dailyPlanId;
  final String roadmapId;
  final int dayNumber;
  final int totalDays;
  final String planDate;
  final String targetWakeTime;
  final String targetBedtime;
  final String baselineWakeTime;
  final String baselineBedtime;
  final String finalTargetWakeTime;
  final String finalTargetBedtime;
  final String transitionState;
  final double weeklyBudget;
  final double dailyBudget;
  final double totalSpentToday;
  final double remainingBudget;
  final String? actualWakeTime;
  final bool isWakeRecorded;
  final List<PlanItemModel> items;
  final bool isLoading;
  final String? errorMessage;

  const DailyPlanState({
    this.dailyPlanId = 'plan-1',
    this.roadmapId = 'mock-roadmap-1',
    this.dayNumber = 1,
    this.totalDays = 30,
    this.planDate = 'Hari Ini',
    this.targetWakeTime = '10:00',
    this.targetBedtime = '02:00',
    this.baselineWakeTime = '10:00',
    this.baselineBedtime = '02:00',
    this.finalTargetWakeTime = '07:00',
    this.finalTargetBedtime = '23:00',
    this.transitionState = 'BASELINE',
    this.weeklyBudget = 350000.0,
    this.dailyBudget = 50000.0,
    this.totalSpentToday = 0.0,
    this.remainingBudget = 50000.0,
    this.actualWakeTime,
    this.isWakeRecorded = false,
    this.items = const [],
    this.isLoading = false,
    this.errorMessage,
  });

  int get completedCount => items.where((i) => i.status == PlanItemStatus.completed || i.status == PlanItemStatus.lateCompleted).length;

  DailyPlanState copyWith({
    String? dailyPlanId,
    String? roadmapId,
    int? dayNumber,
    int? totalDays,
    String? planDate,
    String? targetWakeTime,
    String? targetBedtime,
    String? baselineWakeTime,
    String? baselineBedtime,
    String? finalTargetWakeTime,
    String? finalTargetBedtime,
    String? transitionState,
    double? weeklyBudget,
    double? dailyBudget,
    double? totalSpentToday,
    double? remainingBudget,
    String? actualWakeTime,
    bool? isWakeRecorded,
    List<PlanItemModel>? items,
    bool? isLoading,
    String? errorMessage,
  }) {
    return DailyPlanState(
      dailyPlanId: dailyPlanId ?? this.dailyPlanId,
      roadmapId: roadmapId ?? this.roadmapId,
      dayNumber: dayNumber ?? this.dayNumber,
      totalDays: totalDays ?? this.totalDays,
      planDate: planDate ?? this.planDate,
      targetWakeTime: targetWakeTime ?? this.targetWakeTime,
      targetBedtime: targetBedtime ?? this.targetBedtime,
      baselineWakeTime: baselineWakeTime ?? this.baselineWakeTime,
      baselineBedtime: baselineBedtime ?? this.baselineBedtime,
      finalTargetWakeTime: finalTargetWakeTime ?? this.finalTargetWakeTime,
      finalTargetBedtime: finalTargetBedtime ?? this.finalTargetBedtime,
      transitionState: transitionState ?? this.transitionState,
      weeklyBudget: weeklyBudget ?? this.weeklyBudget,
      dailyBudget: dailyBudget ?? this.dailyBudget,
      totalSpentToday: totalSpentToday ?? this.totalSpentToday,
      remainingBudget: remainingBudget ?? this.remainingBudget,
      actualWakeTime: actualWakeTime ?? this.actualWakeTime,
      isWakeRecorded: isWakeRecorded ?? this.isWakeRecorded,
      items: items ?? this.items,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: errorMessage,
    );
  }
}

final dailyPlanProvider = NotifierProvider<DailyPlanNotifier, DailyPlanState>(
  DailyPlanNotifier.new,
);

class DailyPlanNotifier extends Notifier<DailyPlanState> {
  @override
  DailyPlanState build() {
    return _buildMockInitialState();
  }

  DailyPlanState _buildMockInitialState() {
    return const DailyPlanState(
      dayNumber: 1,
      totalDays: 30,
      targetWakeTime: '10:00',
      targetBedtime: '02:00',
      baselineWakeTime: '10:00',
      baselineBedtime: '02:00',
      finalTargetWakeTime: '07:00',
      finalTargetBedtime: '23:00',
      transitionState: 'BASELINE',
      weeklyBudget: 350000.0,
      dailyBudget: 50000.0,
      remainingBudget: 50000.0,
      items: [
        PlanItemModel(
          id: 'item-1',
          domain: PlanDomain.wake,
          title: 'Bangun Tidur (Target: 10:00)',
          scheduledTime: '10:00',
          isCritical: true,
        ),
        PlanItemModel(
          id: 'item-2',
          domain: PlanDomain.nutrition,
          title: 'Minum 1 Gelas Air Setelah Bangun',
          scheduledTime: '10:00',
        ),
        PlanItemModel(
          id: 'item-3',
          domain: PlanDomain.nutrition,
          title: 'Meal 1 (Makan Siang)',
          scheduledTime: '12:30',
        ),
        PlanItemModel(
          id: 'item-4',
          domain: PlanDomain.movement,
          title: 'Micro-Movement (15 Menit)',
          scheduledTime: '16:30',
        ),
        PlanItemModel(
          id: 'item-5',
          domain: PlanDomain.nutrition,
          title: 'Meal 2 (Makan Malam)',
          scheduledTime: '19:00',
        ),
        PlanItemModel(
          id: 'item-6',
          domain: PlanDomain.sleep,
          title: 'Persiapan Tidur (Redupkan Lampu)',
          scheduledTime: '02:00',
          isCritical: true,
        ),
      ],
    );
  }

  Future<void> fetchTodayPlan(String roadmapId) async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    try {
      final client = ref.read(apiClientProvider);
      final data = await client.getTodayPlan(roadmapId: roadmapId);

      final rawItems = data['items'] as List<dynamic>? ?? [];
      final parsedItems = rawItems.map((item) {
        final domainStr = (item['domain'] as String? ?? 'WAKE').toLowerCase();
        PlanDomain domain = PlanDomain.wake;
        if (domainStr == 'sleep') domain = PlanDomain.sleep;
        if (domainStr == 'nutrition') domain = PlanDomain.nutrition;
        if (domainStr == 'movement') domain = PlanDomain.movement;
        if (domainStr == 'body') domain = PlanDomain.body;

        final statusStr = item['status'] as String? ?? 'PLANNED';
        PlanItemStatus status = PlanItemStatus.planned;
        if (statusStr == 'COMPLETED') status = PlanItemStatus.completed;
        if (statusStr == 'LATE_COMPLETED') status = PlanItemStatus.lateCompleted;
        if (statusStr == 'SKIPPED') status = PlanItemStatus.skipped;

        return PlanItemModel(
          id: item['id'] as String,
          domain: domain,
          title: item['title'] as String,
          scheduledTime: item['scheduled_time'] as String,
          status: status,
          actualTime: item['actual_time'] as String?,
          actualCost: (item['actual_cost'] as num?)?.toDouble(),
          isCritical: item['is_critical'] as bool? ?? false,
        );
      }).toList();

      final wakeMeasurement = data['wake_measurement'] as Map<String, dynamic>?;

      state = state.copyWith(
        dailyPlanId: data['daily_plan_id'] as String,
        roadmapId: roadmapId,
        dayNumber: data['day_number'] as int? ?? 1,
        totalDays: data['total_days'] as int? ?? 30,
        planDate: data['plan_date'] as String? ?? 'Hari Ini',
        targetWakeTime: data['target_wake_time'] as String? ?? '10:00',
        targetBedtime: data['target_bedtime'] as String? ?? '02:00',
        baselineWakeTime: data['baseline_wake_time'] as String? ?? '10:00',
        baselineBedtime: data['baseline_bedtime'] as String? ?? '02:00',
        finalTargetWakeTime: data['final_target_wake_time'] as String? ?? '07:00',
        finalTargetBedtime: data['final_target_bedtime'] as String? ?? '23:00',
        transitionState: data['transition_state'] as String? ?? 'BASELINE',
        weeklyBudget: (data['weekly_budget'] as num?)?.toDouble() ?? 350000.0,
        dailyBudget: (data['daily_budget'] as num?)?.toDouble() ?? 50000.0,
        totalSpentToday: (data['total_spent_today'] as num?)?.toDouble() ?? 0.0,
        remainingBudget: (data['remaining_budget_today'] as num?)?.toDouble() ?? 50000.0,
        actualWakeTime: wakeMeasurement?['actual_time'] as String?,
        isWakeRecorded: wakeMeasurement?['is_recorded'] as bool? ?? false,
        items: parsedItems,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, errorMessage: e.toString());
    }
  }

  void recordWakeMeasurement(String actualTime) {
    state = state.copyWith(
      actualWakeTime: actualTime,
      isWakeRecorded: true,
    );
  }

  void toggleCheckIn(String itemId, {double? spentCost, bool isLate = false}) {
    final updatedItems = state.items.map((item) {
      if (item.id == itemId) {
        if (item.status == PlanItemStatus.completed || item.status == PlanItemStatus.lateCompleted) {
          return item.copyWith(
            status: PlanItemStatus.planned,
            actualTime: null,
            actualCost: null,
          );
        } else {
          final now = DateTime.now();
          final timeStr = '${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}';
          return item.copyWith(
            status: isLate ? PlanItemStatus.lateCompleted : PlanItemStatus.completed,
            actualTime: timeStr,
            actualCost: spentCost,
          );
        }
      }
      return item;
    }).toList();

    double newSpent = 0.0;
    for (final item in updatedItems) {
      if (item.actualCost != null) {
        newSpent += item.actualCost!;
      }
    }

    state = state.copyWith(
      items: updatedItems,
      totalSpentToday: newSpent,
      remainingBudget: state.dailyBudget - newSpent,
    );
  }
}
