import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';

class BudgetIndicatorWidget extends StatelessWidget {
  final double dailyAllocated;
  final double totalSpent;

  const BudgetIndicatorWidget({
    super.key,
    required this.dailyAllocated,
    required this.totalSpent,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final currencyFormatter = NumberFormat.currency(
      locale: 'id_ID',
      symbol: 'Rp',
      decimalDigits: 0,
    );

    final remaining = dailyAllocated - totalSpent;
    final isOverbudget = remaining < 0;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkSurfaceSecondary : AppColors.lightSurfaceSecondary,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: isDark ? AppColors.darkBorder : AppColors.lightBorder,
          width: 1,
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Alokasi Makan Hari Ini',
                style: AppTypography.caption.copyWith(
                  color: isDark ? AppColors.darkTextMuted : AppColors.lightTextMuted,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                currencyFormatter.format(dailyAllocated),
                style: AppTypography.bodyMedium.copyWith(
                  color: isDark ? AppColors.darkTextPrimary : AppColors.lightTextPrimary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                isOverbudget ? 'Defisit Anggaran' : 'Sisa Hari Ini',
                style: AppTypography.caption.copyWith(
                  color: isOverbudget
                      ? AppColors.error
                      : (isDark ? AppColors.darkTextMuted : AppColors.lightTextMuted),
                ),
              ),
              const SizedBox(height: 2),
              Text(
                currencyFormatter.format(remaining.abs()),
                style: AppTypography.bodyMedium.copyWith(
                  color: isOverbudget
                      ? AppColors.error
                      : AppColors.success,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
