import 'plan_domain.dart';

class PlanItemModel {
  final String id;
  final PlanDomain domain;
  final String title;
  final String scheduledTime; // HH:mm
  final PlanItemStatus status;
  final String? actualTime;
  final double? actualCost;
  final String? subtitle;
  final bool isCritical;

  const PlanItemModel({
    required this.id,
    required this.domain,
    required this.title,
    required this.scheduledTime,
    this.status = PlanItemStatus.planned,
    this.actualTime,
    this.actualCost,
    this.subtitle,
    this.isCritical = false,
  });

  PlanItemModel copyWith({
    String? id,
    PlanDomain? domain,
    String? title,
    String? scheduledTime,
    PlanItemStatus? status,
    String? actualTime,
    double? actualCost,
    String? subtitle,
    bool? isCritical,
  }) {
    return PlanItemModel(
      id: id ?? this.id,
      domain: domain ?? this.domain,
      title: title ?? this.title,
      scheduledTime: scheduledTime ?? this.scheduledTime,
      status: status ?? this.status,
      actualTime: actualTime ?? this.actualTime,
      actualCost: actualCost ?? this.actualCost,
      subtitle: subtitle ?? this.subtitle,
      isCritical: isCritical ?? this.isCritical,
    );
  }
}
