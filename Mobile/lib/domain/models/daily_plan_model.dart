import 'plan_item_model.dart';

class DailyPlanModel {
  final String id;
  final String dateString; // YYYY-MM-DD
  final int dayNumber;
  final int totalDays;
  final String targetWakeTime;
  final String targetBedtime;
  final double dailyBudgetAllocated;
  final double totalSpentToday;
  final List<PlanItemModel> items;

  const DailyPlanModel({
    required this.id,
    required this.dateString,
    required this.dayNumber,
    required this.totalDays,
    required this.targetWakeTime,
    required this.targetBedtime,
    required this.dailyBudgetAllocated,
    this.totalSpentToday = 0.0,
    required this.items,
  });

  double get remainingBudget => dailyBudgetAllocated - totalSpentToday;

  int get completedCount => items.where((i) => i.status.isDone).length;
  int get totalCount => items.length;
  double get progressRatio => totalCount == 0 ? 0.0 : completedCount / totalCount;

  DailyPlanModel copyWith({
    String? id,
    String? dateString,
    int? dayNumber,
    int? totalDays,
    String? targetWakeTime,
    String? targetBedtime,
    double? dailyBudgetAllocated,
    double? totalSpentToday,
    List<PlanItemModel>? items,
  }) {
    return DailyPlanModel(
      id: id ?? this.id,
      dateString: dateString ?? this.dateString,
      dayNumber: dayNumber ?? this.dayNumber,
      totalDays: totalDays ?? this.totalDays,
      targetWakeTime: targetWakeTime ?? this.targetWakeTime,
      targetBedtime: targetBedtime ?? this.targetBedtime,
      dailyBudgetAllocated: dailyBudgetAllocated ?? this.dailyBudgetAllocated,
      totalSpentToday: totalSpentToday ?? this.totalSpentToday,
      items: items ?? this.items,
    );
  }
}
