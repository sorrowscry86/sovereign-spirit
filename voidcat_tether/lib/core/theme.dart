import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// The Throne's visual identity — dark, premium, VoidCat-branded.
class ThroneTheme {
  ThroneTheme._();

  // ── Brand Palette ──
  static const Color void0 = Color(0xFF0A0A0F);
  static const Color void1 = Color(0xFF12121A);
  static const Color void2 = Color(0xFF1A1A26);
  static const Color void3 = Color(0xFF242436);
  static const Color void4 = Color(0xFF2E2E44);

  static const Color accent = Color(0xFF6C63FF);
  static const Color accentDim = Color(0xFF4A44B2);
  static const Color accentGlow = Color(0xFF8B83FF);

  static const Color tether = Color(0xFF00E5A0);
  static const Color tetherDim = Color(0xFF00B37D);

  static const Color warning = Color(0xFFFFB347);
  static const Color danger = Color(0xFFFF6B6B);
  static const Color success = Color(0xFF51CF66);

  static const Color textPrimary = Color(0xFFE8E6F0);
  static const Color textSecondary = Color(0xFF9590B0);
  static const Color textMuted = Color(0xFF5C5880);

  // ── Status Colors ──
  static const Color statusOnline = Color(0xFF51CF66);
  static const Color statusIdle = Color(0xFFFFB347);
  static const Color statusOffline = Color(0xFF5C5880);
  static const Color statusPending = Color(0xFF6C63FF);
  static const Color statusRead = Color(0xFF00E5A0);
  static const Color statusDelivered = Color(0xFF4A44B2);

  // ── Bifrost Colors ──
  static const Color bifrostLocal = Color(0xFF3B82F6);
  static const Color bifrostCloud = Color(0xFF06B6D4);
  static const Color bifrostAuto = Color(0xFF8B5CF6);
  static const Color bifrostBridge = Color(0xFFD4A017);

  // ── Typography ──
  static TextTheme _textTheme() {
    return GoogleFonts.interTextTheme().apply(
      bodyColor: textPrimary,
      displayColor: textPrimary,
    );
  }

  // ── The Dark Theme ──
  static ThemeData get dark {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: void0,
      canvasColor: void1,
      cardColor: void2,
      textTheme: _textTheme(),
      colorScheme: const ColorScheme.dark(
        primary: accent,
        secondary: tether,
        surface: void1,
        error: danger,
        onPrimary: void0,
        onSecondary: void0,
        onSurface: textPrimary,
        onError: void0,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: void1,
        elevation: 0,
        titleTextStyle: GoogleFonts.inter(
          fontSize: 18,
          fontWeight: FontWeight.w600,
          color: textPrimary,
        ),
        iconTheme: const IconThemeData(color: textSecondary),
      ),
      dividerColor: void3,
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: void2,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: void3),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: void3),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: accent, width: 1.5),
        ),
        hintStyle: const TextStyle(color: textMuted),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 12,
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: accent,
          foregroundColor: void0,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        ),
      ),
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(foregroundColor: textSecondary),
      ),
      tooltipTheme: TooltipThemeData(
        decoration: BoxDecoration(
          color: void3,
          borderRadius: BorderRadius.circular(6),
        ),
        textStyle: const TextStyle(color: textPrimary, fontSize: 12),
      ),
    );
  }
}
