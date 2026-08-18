import 'package:flutter/material.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';
import '../../domain/models/plan_domain.dart';
import '../../domain/models/plan_item_model.dart';

class TaskCardWidget extends StatelessWidget {
  final PlanItemModel item;
  final VoidCallback onToggle;

  const TaskCardWidget({
    super.key,
    required this.item,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final isDone = item.status.isDone;

    Color badgeBgColor;
    Color badgeTextColor;
    switch (item.domain) {
      case PlanDomain.wake:
      case PlanDomain.sleep:
        badgeBgColor = isDark ? const Color(0xFF1E3A8A) : const Color(0xFFDBEAFE);
        badgeTextColor = isDark ? const Color(0xFF93C5FD) : const Color(0xFF1E40AF);
        break;
      case PlanDomain.nutrition:
        badgeBgColor = isDark ? const Color(0xFF064E3B) : const Color(0xFFD1FAE5);
        badgeTextColor = isDark ? const Color(0xFF6EE7B7) : const Color(0xFF065F46);
        break;
      case PlanDomain.movement:
        badgeBgColor = isDark ? const Color(0xFF78350F) : const Color(0xFFFEF3C7);
        badgeTextColor = isDark ? const Color(0xFFFCD34D) : const Color(0xFF92400E);
        break;
      default:
        badgeBgColor = isDark ? const Color(0xFF334155) : const Color(0xFFF1F5F9);
        badgeTextColor = isDark ? const Color(0xFF94A3B8) : const Color(0xFF475569);
    }

    return Card(
      child: InkWell(
        onTap: onToggle,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              // 1-Tap Toggle Circle
              Container(
                width: 28,
                height: 28,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: isDone
                      ? (item.status == PlanItemStatus.lateCompleted
                          ? AppColors.warning
                          : AppColors.success)
                      : Colors.transparent,
                  border: Border.all(
                    color: isDone
                        ? (item.status == PlanItemStatus.lateCompleted
                            ? AppColors.warning
                            : AppColors.success)
                        : (isDark ? AppColors.darkBorder : AppColors.lightBorder),
                    width: 2,
                  ),
                ),
                child: isDone
                    ? const Icon(
                        Icons.check,
                        size: 18,
                        color: Colors.white,
                      )
                    : null,
              ),
              const SizedBox(width: 14),

              // Title and Subtitle
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        // Domain Badge
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: badgeBgColor,
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            item.domain.label,
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                              color: badgeTextColor,
                            ),
                          ),
                        ),
                        if (item.status == PlanItemStatus.lateCompleted) ...[
                          const SizedBox(width: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: AppColors.warning.withOpacity(0.15),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: const Text(
                              'Telat Input',
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w600,
                                color: AppColors.warning,
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      item.title,
                      style: AppTypography.bodyMedium.copyWith(
                        decoration: isDone ? TextDecoration.lineThrough : null,
                        color: isDone
                            ? (isDark ? AppColors.darkTextMuted : AppColors.lightTextMuted)
                            : (isDark ? AppColors.darkTextPrimary : AppColors.lightTextPrimary),
                      ),
                    ),
                    if (item.subtitle != null) ...[
                      const SizedBox(height: 2),
                      Text(
                        item.subtitle!,
                        style: AppTypography.caption.copyWith(
                          color: isDark ? AppColors.darkTextMuted : AppColors.lightTextMuted,
                        ),
                      ),
                    ],
                  ],
                ),
              ),

              // Scheduled Time
              Text(
                item.scheduledTime,
                style: AppTypography.timeNumeric.copyWith(
                  color: isDark ? AppColors.darkTextSecondary : AppColors.lightTextSecondary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
