import 'package:flutter/material.dart';

/// Zero-AI-Slop Color Tokens
/// Purposely avoids purple-to-blue neon gradients and glassmorphism.
abstract final class AppColors {
  // Light Mode Surfaces
  static const Color lightBackground = Color(0xFFF8FAFC);
  static const Color lightSurface = Color(0xFFFFFFFF);
  static const Color lightSurfaceSecondary = Color(0xFFF1F5F9);
  static const Color lightBorder = Color(0xFFE2E8F0);
  
  // Light Mode Text
  static const Color lightTextPrimary = Color(0xFF0F172A);
  static const Color lightTextSecondary = Color(0xFF475569);
  static const Color lightTextMuted = Color(0xFF94A3B8);

  // Dark Mode Surfaces
  static const Color darkBackground = Color(0xFF0F172A);
  static const Color darkSurface = Color(0xFF1E293B);
  static const Color darkSurfaceSecondary = Color(0xFF334155);
  static const Color darkBorder = Color(0xFF334155);

  // Dark Mode Text
  static const Color darkTextPrimary = Color(0xFFF8FAFC);
  static const Color darkTextSecondary = Color(0xFFCBD5E1);
  static const Color darkTextMuted = Color(0xFF64748B);

  // Semantic Primary Accents
  static const Color primary = Color(0xFF2563EB); // Royal Indigo
  static const Color primaryDark = Color(0xFF1D4ED8);
  static const Color secondary = Color(0xFF0D9488); // Deep Teal

  // Status & Feedback Tokens
  static const Color success = Color(0xFF16A34A);
  static const Color warning = Color(0xFFD97706);
  static const Color error = Color(0xFFDC2626);
  static const Color info = Color(0xFF0284C7);
}
