import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

class ApiClient {
  final String baseUrl;
  final http.Client _client;

  ApiClient({
    String? baseUrl,
    http.Client? client,
  })  : baseUrl = baseUrl ?? _defaultBaseUrl(),
        _client = client ?? http.Client();

  static String _defaultBaseUrl() {
    if (kIsWeb) {
      return 'http://localhost:8000/api/v1';
    }
    if (Platform.isAndroid) {
      return 'http://10.0.2.2:8000/api/v1';
    }
    return 'http://localhost:8000/api/v1';
  }

  Future<Map<String, dynamic>> checkFeasibility({
    required String baselineWake,
    required String targetWake,
    required int durationDays,
    required String baselineBedtime,
    required String targetBedtime,
  }) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/engine/feasibility'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'baseline_wake_time': baselineWake,
        'target_wake_time': targetWake,
        'duration_days': durationDays,
        'baseline_bedtime': baselineBedtime,
        'target_bedtime': targetBedtime,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception('Gagal memeriksa kelayakan target (${response.statusCode}): ${response.body}');
    }
  }

  Future<Map<String, dynamic>> onboardUser({
    required String email,
    required Map<String, dynamic> baseline,
    required Map<String, dynamic> goal,
    List<Map<String, dynamic>> constraints = const [],
    String? startDate,
  }) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/roadmaps/onboard'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': email,
        'baseline': baseline,
        'goal': goal,
        'constraints': constraints,
        'start_date': startDate,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception('Gagal melakukan onboarding (${response.statusCode}): ${response.body}');
    }
  }

  Future<Map<String, dynamic>> getTodayPlan({
    required String roadmapId,
    int? dayNumber,
  }) async {
    final uri = Uri.parse('$baseUrl/roadmaps/$roadmapId/today').replace(
      queryParameters: dayNumber != null ? {'day': dayNumber.toString()} : null,
    );
    final response = await _client.get(uri);

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception('Gagal memuat rencana harian (${response.statusCode}): ${response.body}');
    }
  }

  Future<Map<String, dynamic>> checkinItem({
    required String itemId,
    String? actualTime,
    double? actualCost,
    bool isLate = false,
  }) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/roadmaps/checkin'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'item_id': itemId,
        'actual_time': actualTime,
        'actual_cost': actualCost,
        'is_late': isLate,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception('Gagal menyimpan check-in (${response.statusCode}): ${response.body}');
    }
  }

  Future<Map<String, dynamic>> evaluateDay({
    required String dailyPlanId,
    bool didOpenApp = true,
  }) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/roadmaps/evaluate'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'daily_plan_id': dailyPlanId,
        'did_open_app': didOpenApp,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception('Gagal mengevaluasi rencana harian (${response.statusCode}): ${response.body}');
    }
  }
}
