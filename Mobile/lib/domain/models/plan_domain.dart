enum PlanDomain {
  sleep,
  wake,
  nutrition,
  movement,
  body;

  String get label {
    switch (this) {
      case PlanDomain.sleep:
        return 'Tidur';
      case PlanDomain.wake:
        return 'Bangun';
      case PlanDomain.nutrition:
        return 'Nutrisi & Makan';
      case PlanDomain.movement:
        return 'Aktivitas Fisik';
      case PlanDomain.body:
        return 'Target Fisik';
    }
  }
}

enum PlanItemStatus {
  planned,
  completed,
  lateCompleted,
  skipped,
  missed;

  bool get isDone => this == PlanItemStatus.completed || this == PlanItemStatus.lateCompleted;
}
