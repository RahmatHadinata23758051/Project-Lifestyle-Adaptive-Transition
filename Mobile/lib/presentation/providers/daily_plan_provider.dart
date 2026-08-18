import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../domain/models/plan_domain.dart';
import '../../domain/models/plan_item_model.dart';
import '../../domain/models/daily_plan_model.dart';

final dailyPlanProvider = NotifierProvider<DailyPlanNotifier, DailyPlanModel>(
  DailyPlanNotifier.new,
);

class DailyPlanNotifier extends Notifier<DailyPlanModel> {
  @override
  DailyPlanModel build() {
    return _initialMockPlan();
  }

  static DailyPlanModel _initialMockPlan() {
    return const DailyPlanModel(
      id: 'plan-01',
      dateString: '2026-08-18',
      dayNumber: 1,
      totalDays: 45,
      targetWakeTime: '09:45',
      targetBedtime: '01:45',
      dailyBudgetAllocated: 50000.0,
      totalSpentToday: 0.0,
      items: [
        PlanItemModel(
          id: 'item-1',
          domain: PlanDomain.wake,
          title: 'Bangun & Hidrasi (Target 09:45)',
          scheduledTime: '09:45',
          subtitle: 'Minum 1 gelas air putih setelah bangun',
          isCritical: true,
        ),
        PlanItemModel(
          id: 'item-2',
          domain: PlanDomain.nutrition,
          title: 'Makan Siang / Sarapan Awal',
          scheduledTime: '12:30',
          subtitle: 'Alokasi budget max Rp25.000',
        ),
        PlanItemModel(
          id: 'item-3',
          domain: PlanDomain.movement,
          title: 'Micro-Movement (5 Menit)',
          scheduledTime: '16:00',
          subtitle: 'Peregangan tubuh ringan atau jalan kaki',
        ),
        PlanItemModel(
          id: 'item-4',
          domain: PlanDomain.nutrition,
          title: 'Makan Malam Terjadwal',
          scheduledTime: '19:30',
          subtitle: 'Makan malam sebelum jam 20:00',
        ),
        PlanItemModel(
          id: 'item-5',
          domain: PlanDomain.sleep,
          title: 'Persiapan Tidur (Target 01:45)',
          scheduledTime: '01:45',
          subtitle: 'Redupkan lampu dan matikan layar 15m sebelumnya',
          isCritical: true,
        ),
      ],
    );
  }

  /// 1-Tap Toggle Check-In
  void toggleCheckIn(String itemId, {double? spentCost, bool isLate = false}) {
    final updatedItems = state.items.map((item) {
      if (item.id == itemId) {
        if (item.status.isDone) {
          // Revert to planned
          return item.copyWith(
            status: PlanItemStatus.planned,
            actualTime: null,
            actualCost: null,
          );
        } else {
          final nowTime = _currentTimeString();
          final newStatus = isLate ? PlanItemStatus.lateCompleted : PlanItemStatus.completed;
          return item.copyWith(
            status: newStatus,
            actualTime: nowTime,
            actualCost: spentCost,
          );
        }
      }
      return item;
    }).toList();

    // Recalculate spending
    double newSpent = 0.0;
    for (final item in updatedItems) {
      if (item.actualCost != null) {
        newSpent += item.actualCost!;
      }
    }

    state = state.copyWith(
      items: updatedItems,
      totalSpentToday: newSpent,
    );
  }

  static String _currentTimeString() {
    final now = DateTime.now();
    final hour = now.hour.toString().padLeft(2, '0');
    final minute = now.minute.toString().padLeft(2, '0');
    return '$hour:$minute';
  }
}
