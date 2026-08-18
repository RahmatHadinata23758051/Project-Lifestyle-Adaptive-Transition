import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';
import '../providers/daily_plan_provider.dart';
import '../widgets/task_card_widget.dart';
import '../widgets/budget_indicator_widget.dart';

class DailyPlanScreen extends ConsumerWidget {
  const DailyPlanScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dailyPlan = ref.watch(dailyPlanProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Rencana Hari Ini'),
        elevation: 0,
        backgroundColor: isDark ? AppColors.darkBackground : AppColors.lightBackground,
        actions: [
          Center(
            child: Padding(
              padding: const EdgeInsets.only(right: 16),
              child: Text(
                'Hari ${dailyPlan.dayNumber}/${dailyPlan.totalDays}',
                style: AppTypography.caption.copyWith(
                  fontWeight: FontWeight.w600,
                  color: isDark ? AppColors.darkTextSecondary : AppColors.lightTextSecondary,
                ),
              ),
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Target Wake & Sleep Strip
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Row(
                children: [
                  Expanded(
                    child: _TargetPill(
                      label: 'Target Bangun',
                      time: dailyPlan.targetWakeTime,
                      isDark: isDark,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _TargetPill(
                      label: 'Target Tidur',
                      time: dailyPlan.targetBedtime,
                      isDark: isDark,
                    ),
                  ),
                ],
              ),
            ),

            // Daily Food Budget Widget
            BudgetIndicatorWidget(
              dailyAllocated: dailyPlan.dailyBudgetAllocated,
              totalSpent: dailyPlan.totalSpentToday,
            ),

            // Progress Bar (Non-Judgmental)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Progres Rutinitas',
                        style: AppTypography.caption.copyWith(
                          color: isDark ? AppColors.darkTextMuted : AppColors.lightTextMuted,
                        ),
                      ),
                      Text(
                        '${dailyPlan.completedCount} / ${dailyPlan.totalCount} Selesai',
                        style: AppTypography.caption.copyWith(
                          fontWeight: FontWeight.w600,
                          color: isDark ? AppColors.darkTextPrimary : AppColors.lightTextPrimary,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: dailyPlan.progressRatio,
                      minHeight: 6,
                      backgroundColor: isDark
                          ? AppColors.darkSurfaceSecondary
                          : AppColors.lightSurfaceSecondary,
                      valueColor: const AlwaysStoppedAnimation<Color>(AppColors.primary),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 8),

            // Task Checklist
            Expanded(
              child: ListView.builder(
                itemCount: dailyPlan.items.length,
                itemBuilder: (context, index) {
                  final item = dailyPlan.items[index];
                  return TaskCardWidget(
                    item: item,
                    onToggle: () {
                      ref.read(dailyPlanProvider.notifier).toggleCheckIn(item.id);
                    },
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TargetPill extends StatelessWidget {
  final String label;
  final String time;
  final bool isDark;

  const _TargetPill({
    required this.label,
    required this.time,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkSurface : AppColors.lightSurface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isDark ? AppColors.darkBorder : AppColors.lightBorder,
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              fontSize: 11,
              color: isDark ? AppColors.darkTextMuted : AppColors.lightTextMuted,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            time,
            style: AppTypography.timeNumeric.copyWith(
              color: isDark ? AppColors.darkTextPrimary : AppColors.lightTextPrimary,
            ),
          ),
        ],
      ),
    );
  }
}
