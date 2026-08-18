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
                      onPressed: () {
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
        return _Step4Feasibility(state: state, isDark: isDark);
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
          onChanged: (v) => ref.read(onboardingProvider.notifier).updateBedtime(v),
        ),
        const SizedBox(height: 16),
        _InputField(
          label: 'Jam Bangun Saat Ini (HH:MM)',
          initialValue: state.wakeTime,
          onChanged: (v) => ref.read(onboardingProvider.notifier).updateWakeTime(v),
        ),
        const SizedBox(height: 16),
        _InputField(
          label: 'Alokasi Budget Makan Mingguan (Rp)',
          initialValue: state.weeklyFoodBudget.toInt().toString(),
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
          onChanged: (v) => ref.read(onboardingProvider.notifier).updateTargetWakeTime(v),
        ),
        const SizedBox(height: 16),
        _InputField(
          label: 'Target Jam Tidur (HH:MM)',
          initialValue: state.targetBedtime,
          onChanged: (v) => ref.read(onboardingProvider.notifier).updateTargetBedtime(v),
        ),
        const SizedBox(height: 16),
        _InputField(
          label: 'Durasi Transisi yang Diminta (Hari)',
          initialValue: state.durationDays.toString(),
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

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Langkah 3: Batasan Jadwal Wajib', style: AppTypography.h2),
        const SizedBox(height: 6),
        const Text(
          'Masukkan jam kuliah atau jam kerja agar to-do adaptif tidak pernah bertabrakan.',
          style: AppTypography.body,
        ),
        const SizedBox(height: 20),
        if (state.constraints.isEmpty)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: isDark ? AppColors.darkSurfaceSecondary : AppColors.lightSurfaceSecondary,
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Text('Belum ada batasan jadwal yang ditambahkan.'),
          )
        else
          ...state.constraints.asMap().entries.map((entry) {
            final idx = entry.key;
            final c = entry.value;
            return Card(
              child: ListTile(
                title: Text(c['title'] ?? ''),
                subtitle: Text('${c['day_of_week']} • ${c['start_time']} - ${c['end_time']}'),
                trailing: IconButton(
                  icon: const Icon(Icons.delete_outline, size: 20),
                  onPressed: () => ref.read(onboardingProvider.notifier).removeConstraint(idx),
                ),
              ),
            );
          }),
        const SizedBox(height: 16),
        OutlinedButton.icon(
          onPressed: () {
            ref.read(onboardingProvider.notifier).addConstraint({
              'title': 'Jadwal Kuliah Pagi',
              'category': 'UNIVERSITY',
              'day_of_week': 'MONDAY',
              'start_time': '08:00',
              'end_time': '12:00',
              'is_flexible': false,
            });
          },
          icon: const Icon(Icons.add, size: 18),
          label: const Text('Tambah Jadwal Kuliah/Kerja'),
        ),
      ],
    );
  }
}

class _Step4Feasibility extends StatelessWidget {
  final OnboardingState state;
  final bool isDark;

  const _Step4Feasibility({required this.state, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final feas = state.feasibilityResult;
    final isFeasible = feas?['is_feasible'] ?? true;
    final message = feas?['feedback_message'] ?? 'Memeriksa kelayakan transisi...';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Langkah 4: Evaluasi Kelayakan', style: AppTypography.h2),
        const SizedBox(height: 6),
        const Text(
          'Hasil kalkulasi matematis terhadap batas pergeseran alami tubuh.',
          style: AppTypography.body,
        ),
        const SizedBox(height: 24),
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
                    isFeasible ? 'Target Realistis & Aman' : 'Penyesuaian Direkomendasikan',
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
        const SizedBox(height: 20),
        const Text(
          'Klik tombol di bawah untuk membuat roadmap transisi yang terpersonalisasi.',
          style: AppTypography.caption,
        ),
      ],
    );
  }
}

class _InputField extends StatelessWidget {
  final String label;
  final String initialValue;
  final ValueChanged<String> onChanged;
  final TextInputType keyboardType;

  const _InputField({
    required this.label,
    required this.initialValue,
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
            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
          ),
        ),
      ],
    );
  }
}
