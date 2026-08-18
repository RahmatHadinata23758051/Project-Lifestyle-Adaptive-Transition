import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';
import '../providers/onboarding_provider.dart';
import 'daily_plan_screen.dart';

class OnboardingScreen extends ConsumerWidget {
  const OnboardingScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(onboardingProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Inisiasi Pola Hidup'),
        elevation: 0,
        backgroundColor: isDark ? AppColors.darkBackground : AppColors.lightBackground,
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Step Progress Bar
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              child: Row(
                children: List.generate(4, (index) {
                  final isActive = index <= state.currentStep;
                  return Expanded(
                    child: Container(
                      height: 4,
                      margin: EdgeInsets.only(right: index < 3 ? 8 : 0),
                      decoration: BoxDecoration(
                        color: isActive
                            ? AppColors.primary
                            : (isDark ? AppColors.darkSurfaceSecondary : AppColors.lightSurfaceSecondary),
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                  );
                }),
              ),
            ),

            // Step Content
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(20),
                child: _buildStepContent(context, ref, state, isDark),
              ),
            ),

            // Error Banner if any
            if (state.errorMessage != null)
              Container(
                margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.red.shade900.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.red.shade400, width: 1),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline, color: Colors.red, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        state.errorMessage!,
                        style: AppTypography.caption.copyWith(color: Colors.red),
                      ),
                    ),
                  ],
                ),
              ),

            // Bottom Navigation Buttons
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
              decoration: BoxDecoration(
                color: isDark ? AppColors.darkSurface : AppColors.lightSurface,
                border: Border(
                  top: BorderSide(
                    color: isDark ? AppColors.darkBorder : AppColors.lightBorder,
                    width: 1,
                  ),
                ),
              ),
              child: Row(
                children: [
                  if (state.currentStep > 0) ...[
                    OutlinedButton(
                      onPressed: state.isLoading
                          ? null
                          : () {
                              ref.read(onboardingProvider.notifier).previousStep();
                            },
                      style: OutlinedButton.styleFrom(
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                      ),
                      child: const Text('Kembali'),
                    ),
                    const SizedBox(width: 12),
                  ],
                  Expanded(
                    child: ElevatedButton(
                      onPressed: state.isLoading
                          ? null
                          : () async {
                              if (state.currentStep < 3) {
                                ref.read(onboardingProvider.notifier).nextStep();
                              } else {
                                final success = await ref.read(onboardingProvider.notifier).submitOnboarding();
                                if (success && context.mounted) {
                                  Navigator.pushReplacement(
                                    context,
                                    MaterialPageRoute(builder: (_) => const DailyPlanScreen()),
                                  );
                                }
                              }
                            },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.primary,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                      child: state.isLoading
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                            )
                          : Text(state.currentStep == 3 ? 'Mulai Transisi' : 'Lanjutkan'),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStepContent(BuildContext context, WidgetRef ref, OnboardingState state, bool isDark) {
    switch (state.currentStep) {
      case 0:
        return _Step1Baseline(state: state, ref: ref);
      case 1:
        return _Step2Goal(state: state, ref: ref);
      case 2:
        return _Step3Constraints(state: state, ref: ref, isDark: isDark);
      case 3:
        return _Step4Feasibility(state: state, ref: ref, isDark: isDark);
      default:
        return const SizedBox.shrink();
    }
  }
}

class _Step1Baseline extends StatelessWidget {
  final OnboardingState state;
  final WidgetRef ref;

  const _Step1Baseline({required this.state, required this.ref});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Langkah 1: Pola Hidup Saat Ini', style: AppTypography.h2),
        const SizedBox(height: 6),
        const Text(
          'Jawab apa adanya tanpa rasa bersalah. Chronos menggunakan data ini sebagai baseline adaptasi.',
          style: AppTypography.body,
        ),
        const SizedBox(height: 24),
        _InputField(
          label: 'Jam Tidur Saat Ini (HH:MM)',
          initialValue: state.bedtime,
          hintText: 'Contoh: 02:00',
          onChanged: (v) => ref.read(onboardingProvider.notifier).updateBedtime(v),
        ),
        const SizedBox(height: 16),
        _InputField(
          label: 'Jam Bangun Saat Ini (HH:MM)',
          initialValue: state.wakeTime,
          hintText: 'Contoh: 10:00',
          onChanged: (v) => ref.read(onboardingProvider.notifier).updateWakeTime(v),
        ),
        const SizedBox(height: 16),
        _InputField(
          label: 'Alokasi Budget Makan Mingguan (Rp)',
          initialValue: state.weeklyFoodBudget.toInt().toString(),
          hintText: 'Contoh: 350000',
          keyboardType: TextInputType.number,
          onChanged: (v) {
            final val = double.tryParse(v) ?? 350000.0;
            ref.read(onboardingProvider.notifier).updateWeeklyFoodBudget(val);
          },
        ),
      ],
    );
  }
}

class _Step2Goal extends StatelessWidget {
  final OnboardingState state;
  final WidgetRef ref;

  const _Step2Goal({required this.state, required this.ref});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Langkah 2: Target Impian Anda', style: AppTypography.h2),
        const SizedBox(height: 6),
        const Text(
          'Tentukan jam bangun dan durasi transisi yang Anda inginkan.',
          style: AppTypography.body,
        ),
        const SizedBox(height: 24),
        _InputField(
          label: 'Target Jam Bangun (HH:MM)',
          initialValue: state.targetWakeTime,
          hintText: 'Contoh: 07:00',
          onChanged: (v) => ref.read(onboardingProvider.notifier).updateTargetWakeTime(v),
        ),
        const SizedBox(height: 16),
        _InputField(
          label: 'Target Jam Tidur (HH:MM)',
          initialValue: state.targetBedtime,
          hintText: 'Contoh: 23:00',
          onChanged: (v) => ref.read(onboardingProvider.notifier).updateTargetBedtime(v),
        ),
        const SizedBox(height: 16),
        _InputField(
          label: 'Durasi Transisi yang Diminta (Hari)',
          initialValue: state.durationDays.toString(),
          hintText: 'Contoh: 30',
          keyboardType: TextInputType.number,
          onChanged: (v) {
            final val = int.tryParse(v) ?? 30;
            ref.read(onboardingProvider.notifier).updateDurationDays(val);
          },
        ),
      ],
    );
  }
}

class _Step3Constraints extends StatelessWidget {
  final OnboardingState state;
  final WidgetRef ref;
  final bool isDark;

  const _Step3Constraints({required this.state, required this.ref, required this.isDark});

  void _showAddConstraintModal(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: isDark ? AppColors.darkSurface : AppColors.lightSurface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) => _AddConstraintBottomSheet(
        onAdd: (newConstraint) {
          ref.read(onboardingProvider.notifier).addConstraint(newConstraint);
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Langkah 3: Batasan Jadwal Wajib', style: AppTypography.h2),
        const SizedBox(height: 6),
        const Text(
          'Masukkan jam kuliah atau jam kerja agar jadwal to-do adaptif tidak pernah bertabrakan.',
          style: AppTypography.body,
        ),
        const SizedBox(height: 20),
        if (state.constraints.isEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: isDark ? AppColors.darkSurfaceSecondary : AppColors.lightSurfaceSecondary,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: isDark ? AppColors.darkBorder : AppColors.lightBorder,
                width: 1,
              ),
            ),
            child: const Text(
              'Belum ada batasan jadwal wajib. Anda bisa menambahkan kuliah, kerja, atau aktivitas rutin lainnya.',
              style: AppTypography.caption,
            ),
          )
        else
          ...state.constraints.asMap().entries.map((entry) {
            final idx = entry.key;
            final c = entry.value;
            return Card(
              margin: const EdgeInsets.only(bottom: 10),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
                side: BorderSide(
                  color: isDark ? AppColors.darkBorder : AppColors.lightBorder,
                  width: 1,
                ),
              ),
              child: ListTile(
                title: Text(c['title'] ?? '', style: AppTypography.bodyMedium),
                subtitle: Text(
                  '${_translateDay(c['day_of_week'])} • ${c['start_time']} - ${c['end_time']}',
                  style: AppTypography.caption,
                ),
                trailing: IconButton(
                  icon: const Icon(Icons.delete_outline, size: 20, color: Colors.redAccent),
                  onPressed: () => ref.read(onboardingProvider.notifier).removeConstraint(idx),
                ),
              ),
            );
          }),
        const SizedBox(height: 16),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton.icon(
            onPressed: () => _showAddConstraintModal(context),
            icon: const Icon(Icons.add, size: 18),
            label: const Text('Tambah Jadwal Kegiatan Baru'),
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 14),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            ),
          ),
        ),
      ],
    );
  }

  String _translateDay(String? dow) {
    switch (dow) {
      case 'MONDAY':
        return 'Senin';
      case 'TUESDAY':
        return 'Selasa';
      case 'WEDNESDAY':
        return 'Rabu';
      case 'THURSDAY':
        return 'Kamis';
      case 'FRIDAY':
        return 'Jumat';
      case 'SATURDAY':
        return 'Sabtu';
      case 'SUNDAY':
        return 'Minggu';
      default:
        return dow ?? '';
    }
  }
}

class _AddConstraintBottomSheet extends StatefulWidget {
  final ValueChanged<Map<String, dynamic>> onAdd;

  const _AddConstraintBottomSheet({required this.onAdd});

  @override
  State<_AddConstraintBottomSheet> createState() => _AddConstraintBottomSheetState();
}

class _AddConstraintBottomSheetState extends State<_AddConstraintBottomSheet> {
  final _titleController = TextEditingController(text: 'Kuliah Pagi');
  final _startTimeController = TextEditingController(text: '08:00');
  final _endTimeController = TextEditingController(text: '12:00');
  String _selectedDay = 'MONDAY';
  String _selectedCategory = 'UNIVERSITY';

  final List<Map<String, String>> _days = [
    {'value': 'MONDAY', 'label': 'Senin'},
    {'value': 'TUESDAY', 'label': 'Selasa'},
    {'value': 'WEDNESDAY', 'label': 'Rabu'},
    {'value': 'THURSDAY', 'label': 'Kamis'},
    {'value': 'FRIDAY', 'label': 'Jumat'},
    {'value': 'SATURDAY', 'label': 'Sabtu'},
    {'value': 'SUNDAY', 'label': 'Minggu'},
  ];

  final List<Map<String, String>> _categories = [
    {'value': 'UNIVERSITY', 'label': 'Kuliah / Akademik'},
    {'value': 'WORK', 'label': 'Pekerjaan / Shift'},
    {'value': 'COMMUTE', 'label': 'Perjalanan / Commute'},
    {'value': 'PERSONAL', 'label': 'Aktivitas Pribadi'},
  ];

  @override
  void dispose() {
    _titleController.dispose();
    _startTimeController.dispose();
    _endTimeController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Tambah Batasan Jadwal Wajib', style: AppTypography.h2),
          const SizedBox(height: 16),
          TextField(
            controller: _titleController,
            decoration: const InputDecoration(
              labelText: 'Nama Kegiatan / Kuliah / Kerja',
              hintText: 'Contoh: Kuliah Algoritma Pemrograman',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 14),
          DropdownButtonFormField<String>(
            value: _selectedCategory,
            decoration: const InputDecoration(
              labelText: 'Kategori',
              border: OutlineInputBorder(),
            ),
            items: _categories
                .map((c) => DropdownMenuItem(value: c['value'], child: Text(c['label']!)))
                .toList(),
            onChanged: (val) {
              if (val != null) setState(() => _selectedCategory = val);
            },
          ),
          const SizedBox(height: 14),
          DropdownButtonFormField<String>(
            value: _selectedDay,
            decoration: const InputDecoration(
              labelText: 'Hari Kegiatan',
              border: OutlineInputBorder(),
            ),
            items: _days
                .map((d) => DropdownMenuItem(value: d['value'], child: Text(d['label']!)))
                .toList(),
            onChanged: (val) {
              if (val != null) setState(() => _selectedDay = val);
            },
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _startTimeController,
                  decoration: const InputDecoration(
                    labelText: 'Jam Mulai (HH:MM)',
                    hintText: '08:00',
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: TextField(
                  controller: _endTimeController,
                  decoration: const InputDecoration(
                    labelText: 'Jam Selesai (HH:MM)',
                    hintText: '12:00',
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () {
                final title = _titleController.text.trim();
                final start = _startTimeController.text.trim();
                final end = _endTimeController.text.trim();

                if (title.isNotEmpty && start.isNotEmpty && end.isNotEmpty) {
                  widget.onAdd({
                    'title': title,
                    'category': _selectedCategory,
                    'day_of_week': _selectedDay,
                    'start_time': start,
                    'end_time': end,
                    'is_flexible': false,
                  });
                  Navigator.pop(context);
                }
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              child: const Text('Simpan Jadwal Kegiatan'),
            ),
          ),
        ],
      ),
    );
  }
}

class _Step4Feasibility extends StatelessWidget {
  final OnboardingState state;
  final WidgetRef ref;
  final bool isDark;

  const _Step4Feasibility({
    required this.state,
    required this.ref,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    final feas = state.feasibilityResult;
    final isFeasible = feas?['is_feasible'] ?? true;
    final message = feas?['feedback_message'] ?? 'Memeriksa kelayakan transisi...';
    final recDays = feas?['recommended_duration_days'] as int? ?? state.durationDays;
    final isLonger = recDays > state.durationDays;
    final effectiveDuration = state.effectiveDurationDays ?? recDays;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Langkah 4: Evaluasi Kelayakan Transisi', style: AppTypography.h2),
        const SizedBox(height: 6),
        const Text(
          'Chronos menghitung batasan pergeseran bertahap agar tubuh beradaptasi tanpa kelelahan.',
          style: AppTypography.body,
        ),
        const SizedBox(height: 20),

        // Parameter Review Cards
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: isDark ? AppColors.darkSurfaceSecondary : AppColors.lightSurfaceSecondary,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: isDark ? AppColors.darkBorder : AppColors.lightBorder,
              width: 1,
            ),
          ),
          child: Column(
            children: [
              _buildSummaryRow('Kondisi Saat Ini', 'Bangun ${state.wakeTime} • Tidur ${state.bedtime}'),
              const Divider(height: 20),
              _buildSummaryRow('Target Impian', 'Bangun ${state.targetWakeTime} • Tidur ${state.targetBedtime}'),
              const Divider(height: 20),
              _buildSummaryRow('Durasi Diminta', '${state.durationDays} Hari'),
              if (isLonger) ...[
                const Divider(height: 20),
                _buildSummaryRow('Rekomendasi Chronos', '$recDays Hari', isHighlighted: true),
              ],
            ],
          ),
        ),

        const SizedBox(height: 20),

        // Feasibility Decision Feedback
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: isFeasible
                ? (isDark ? const Color(0xFF064E3B) : const Color(0xFFD1FAE5))
                : (isDark ? const Color(0xFF78350F) : const Color(0xFFFEF3C7)),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: isFeasible ? AppColors.success : AppColors.warning,
              width: 1,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    isFeasible ? Icons.check_circle_outline : Icons.info_outline,
                    color: isFeasible ? AppColors.success : AppColors.warning,
                    size: 20,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    isFeasible
                        ? 'Sesuai dengan Policy Transisi Chronos'
                        : 'Penyesuaian Durasi Direkomendasikan',
                    style: AppTypography.bodyMedium.copyWith(
                      fontWeight: FontWeight.w700,
                      color: isFeasible
                          ? (isDark ? const Color(0xFF6EE7B7) : const Color(0xFF065F46))
                          : (isDark ? const Color(0xFFFCD34D) : const Color(0xFF92400E)),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                message,
                style: AppTypography.body.copyWith(
                  color: isDark ? Colors.white70 : Colors.black87,
                ),
              ),
            ],
          ),
        ),

        // Explicit Decision Selection if recommendation is longer
        if (isLonger) ...[
          const SizedBox(height: 20),
          const Text('Konfirmasi Durasi Roadmap:', style: AppTypography.h3),
          const SizedBox(height: 10),
          RadioListTile<int>(
            value: recDays,
            groupValue: effectiveDuration,
            onChanged: (val) {
              if (val != null) ref.read(onboardingProvider.notifier).setEffectiveDurationDays(val);
            },
            title: Text('Gunakan $recDays Hari (Direkomendasikan agar adaptasi bertahap)', style: AppTypography.bodyMedium),
            activeColor: AppColors.primary,
            contentPadding: EdgeInsets.zero,
          ),
          RadioListTile<int>(
            value: state.durationDays,
            groupValue: effectiveDuration,
            onChanged: (val) {
              if (val != null) ref.read(onboardingProvider.notifier).setEffectiveDurationDays(val);
            },
            title: Text('Tetap Gunakan ${state.durationDays} Hari (Pergeseran lebih intensif)', style: AppTypography.bodyMedium),
            activeColor: AppColors.primary,
            contentPadding: EdgeInsets.zero,
          ),
        ],

        const SizedBox(height: 20),
        Text(
          'Roadmap akan dibuat dengan total durasi $effectiveDuration hari. Hari 1 akan dimulai sebagai Stabilization Day.',
          style: AppTypography.caption,
        ),
      ],
    );
  }

  Widget _buildSummaryRow(String label, String value, {bool isHighlighted = false}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: AppTypography.body),
        Text(
          value,
          style: AppTypography.bodyMedium.copyWith(
            fontWeight: FontWeight.w700,
            color: isHighlighted ? AppColors.primary : null,
          ),
        ),
      ],
    );
  }
}

class _InputField extends StatelessWidget {
  final String label;
  final String initialValue;
  final String? hintText;
  final ValueChanged<String> onChanged;
  final TextInputType keyboardType;

  const _InputField({
    required this.label,
    required this.initialValue,
    this.hintText,
    required this.onChanged,
    this.keyboardType = TextInputType.text,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: AppTypography.caption),
        const SizedBox(height: 6),
        TextFormField(
          initialValue: initialValue,
          keyboardType: keyboardType,
          onChanged: onChanged,
          decoration: InputDecoration(
            hintText: hintText,
            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
          ),
        ),
      ],
    );
  }
}
