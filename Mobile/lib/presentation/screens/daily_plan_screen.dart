import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';
import '../../domain/models/plan_domain.dart';
import '../../domain/models/plan_item_model.dart';
import '../providers/daily_plan_provider.dart';
import '../providers/onboarding_provider.dart';

class DailyPlanScreen extends ConsumerWidget {
  const DailyPlanScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(dailyPlanProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Project Chronos'),
        elevation: 0,
        backgroundColor: isDark ? AppColors.darkBackground : AppColors.lightBackground,
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () async {
            final onboarding = ref.read(onboardingProvider);
            if (onboarding.createdRoadmapId != null) {
              await ref.read(dailyPlanProvider.notifier).fetchTodayPlan(onboarding.createdRoadmapId!);
            }
          },
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 1. Transition Header & Day Position
                _buildTransitionHeader(state, isDark),
                const SizedBox(height: 16),

                // 2. Transition Context Flow (Baseline -> Today -> Goal)
                _buildTransitionContextCard(state, isDark),
                const SizedBox(height: 16),

                // 3. P0.3 Wake Measurement Card
                _buildWakeMeasurementCard(context, ref, state, isDark),
                const SizedBox(height: 16),

                // 4. P1.4 Budget Context Card
                _buildBudgetContextCard(state, isDark),
                const SizedBox(height: 24),

                // 5. Today's Plan Routine & Micro-Quests
                const Text('Jadwal & Micro-Quest Hari Ini', style: AppTypography.h2),
                const SizedBox(height: 4),
                Text(
                  'Rutinitas bebas bentrok jadwal kuliah dan kerja (${state.completedCount}/${state.items.length} selesai)',
                  style: AppTypography.caption,
                ),
                const SizedBox(height: 12),

                ...state.items.map((item) => _buildTaskItem(context, ref, item, isDark)),
                const SizedBox(height: 32),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildTransitionHeader(DailyPlanState state, bool isDark) {
    String stateLabel = 'Stabilizing (Baseline Day)';
    Color badgeColor = AppColors.primary;
    if (state.transitionState == 'PROGRESSING') {
      stateLabel = 'Progressing (Pergeseran Target)';
      badgeColor = AppColors.success;
    } else if (state.transitionState == 'HOLD') {
      stateLabel = 'Hold (Menjaga Konsistensi)';
      badgeColor = AppColors.warning;
    } else if (state.transitionState == 'RECOVERY') {
      stateLabel = 'Recovery (Langkah Penyesuaian)';
      badgeColor = Colors.orange;
    }

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('HARI INI', style: AppTypography.caption),
            Text('Day ${state.dayNumber} dari ${state.totalDays}', style: AppTypography.h1),
          ],
        ),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: badgeColor.withOpacity(0.12),
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: badgeColor, width: 1),
          ),
          child: Text(
            stateLabel,
            style: AppTypography.caption.copyWith(
              color: badgeColor,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildTransitionContextCard(DailyPlanState state, bool isDark) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkSurfaceSecondary : AppColors.lightSurfaceSecondary,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isDark ? AppColors.darkBorder : AppColors.lightBorder,
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Konteks Transisi Bangun Tidur', style: AppTypography.caption),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _buildContextCol('Baseline', state.baselineWakeTime),
              ),
              const Icon(Icons.arrow_forward, size: 16, color: Colors.grey),
              Expanded(
                child: _buildContextCol('Target Hari Ini', state.targetWakeTime, isHighlight: true),
              ),
              const Icon(Icons.arrow_forward, size: 16, color: Colors.grey),
              Expanded(
                child: _buildContextCol('Goal Akhir', state.finalTargetWakeTime),
              ),
            ],
          ),
          if (state.dayNumber == 1) ...[
            const SizedBox(height: 10),
            const Text(
              'Hari pertama berfokus pada stabilisasi baseline tanpa pergeseran paksa.',
              style: AppTypography.caption,
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildContextCol(String label, String time, {bool isHighlight = false}) {
    return Column(
      children: [
        Text(label, style: const TextStyle(fontSize: 11, color: Colors.grey)),
        const SizedBox(height: 2),
        Text(
          time,
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w700,
            color: isHighlight ? AppColors.primary : null,
          ),
        ),
      ],
    );
  }

  Widget _buildWakeMeasurementCard(BuildContext context, WidgetRef ref, DailyPlanState state, bool isDark) {
    final isRecorded = state.isWakeRecorded || state.actualWakeTime != null;
    final actual = state.actualWakeTime ?? '--:--';

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkSurface : AppColors.lightSurface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isRecorded ? AppColors.success : (isDark ? AppColors.darkBorder : AppColors.lightBorder),
          width: 1.5,
        ),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.alarm, color: AppColors.primary, size: 24),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('PENGUKURAN BANGUN TIDUR', style: AppTypography.caption),
                const SizedBox(height: 2),
                Text(
                  'Target: ${state.targetWakeTime} • Aktual: $actual',
                  style: AppTypography.bodyMedium.copyWith(fontWeight: FontWeight.w700),
                ),
                Text(
                  isRecorded ? 'Tercatat • Siap untuk evaluasi malam' : 'Belum dicatat hari ini',
                  style: AppTypography.caption.copyWith(
                    color: isRecorded ? AppColors.success : Colors.grey,
                  ),
                ),
              ],
            ),
          ),
          OutlinedButton(
            onPressed: () => _showRecordWakeDialog(context, ref, state.targetWakeTime),
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            ),
            child: Text(isRecorded ? 'Ubah' : 'Catat'),
          ),
        ],
      ),
    );
  }

  void _showRecordWakeDialog(BuildContext context, WidgetRef ref, String targetTime) {
    final controller = TextEditingController(text: targetTime);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Catat Jam Bangun Aktual'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Masukkan waktu nyata saat Anda bangun tidur:', style: AppTypography.caption),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              decoration: const InputDecoration(
                labelText: 'Jam Bangun (HH:MM)',
                hintText: 'Contoh: 09:55',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Batal'),
          ),
          ElevatedButton(
            onPressed: () {
              final val = controller.text.trim();
              if (val.isNotEmpty) {
                ref.read(dailyPlanProvider.notifier).recordWakeMeasurement(val);
                Navigator.pop(ctx);
              }
            },
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.primary, foregroundColor: Colors.white),
            child: const Text('Simpan'),
          ),
        ],
      ),
    );
  }

  Widget _buildBudgetContextCard(DailyPlanState state, bool isDark) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkSurfaceSecondary : AppColors.lightSurfaceSecondary,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isDark ? AppColors.darkBorder : AppColors.lightBorder,
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Konteks Alokasi Budget Makan', style: AppTypography.caption),
              Text('Mingguan: Rp${_formatRupiah(state.weeklyBudget)}', style: AppTypography.caption),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(child: _buildBudgetMetric('Plafon Hari Ini', 'Rp${_formatRupiah(state.dailyBudget)}')),
              Expanded(child: _buildBudgetMetric('Terpakai', 'Rp${_formatRupiah(state.totalSpentToday)}')),
              Expanded(
                child: _buildBudgetMetric(
                  'Sisa Hari Ini',
                  'Rp${_formatRupiah(state.remainingBudget)}',
                  isSuccess: state.remainingBudget >= 0,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildBudgetMetric(String label, String value, {bool? isSuccess}) {
    Color? valColor;
    if (isSuccess == true) valColor = AppColors.success;
    if (isSuccess == false) valColor = AppColors.warning;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 11, color: Colors.grey)),
        const SizedBox(height: 2),
        Text(
          value,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w700,
            color: valColor,
          ),
        ),
      ],
    );
  }

  Widget _buildTaskItem(BuildContext context, WidgetRef ref, PlanItemModel item, bool isDark) {
    final isDone = item.status == PlanItemStatus.completed || item.status == PlanItemStatus.lateCompleted;

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkSurface : AppColors.lightSurface,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: isDone
              ? AppColors.success.withOpacity(0.4)
              : (isDark ? AppColors.darkBorder : AppColors.lightBorder),
          width: 1,
        ),
      ),
      child: Row(
        children: [
          Checkbox(
            value: isDone,
            activeColor: AppColors.success,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
            onChanged: (_) {
              if (item.domain == PlanDomain.nutrition && !isDone) {
                _showRecordMealSpendingDialog(context, ref, item.id);
              } else {
                ref.read(dailyPlanProvider.notifier).toggleCheckIn(item.id);
              }
            },
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.title,
                  style: AppTypography.bodyMedium.copyWith(
                    decoration: isDone ? TextDecoration.lineThrough : null,
                    color: isDone ? Colors.grey : null,
                    fontWeight: item.isCritical ? FontWeight.w700 : FontWeight.w500,
                  ),
                ),
                Text(
                  '${item.scheduledTime}${item.actualCost != null ? ' • Pengeluaran: Rp${_formatRupiah(item.actualCost!)}' : ''}',
                  style: AppTypography.caption,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  void _showRecordMealSpendingDialog(BuildContext context, WidgetRef ref, String itemId) {
    final costController = TextEditingController(text: '20000');
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Catat Pengeluaran Makan'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Berapa biaya makan untuk menu ini? (Kosongkan jika Rp0)', style: AppTypography.caption),
            const SizedBox(height: 12),
            TextField(
              controller: costController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Nominal (Rp)',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              ref.read(dailyPlanProvider.notifier).toggleCheckIn(itemId, spentCost: 0.0);
              Navigator.pop(ctx);
            },
            child: const Text('Lewati (Rp0)'),
          ),
          ElevatedButton(
            onPressed: () {
              final cost = double.tryParse(costController.text.trim()) ?? 0.0;
              ref.read(dailyPlanProvider.notifier).toggleCheckIn(itemId, spentCost: cost);
              Navigator.pop(ctx);
            },
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.primary, foregroundColor: Colors.white),
            child: const Text('Simpan'),
          ),
        ],
      ),
    );
  }

  String _formatRupiah(double val) {
    return val.toInt().toString().replaceAllMapped(
          RegExp(r'(\d{1,3})(?=(\d{3})+(?!\d))'),
          (Match m) => '${m[1]}.',
        );
  }
}
