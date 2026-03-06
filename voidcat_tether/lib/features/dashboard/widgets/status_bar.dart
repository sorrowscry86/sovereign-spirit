import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/theme.dart';
import '../../../services/websocket_service.dart';

/// Top status bar showing connection state and system info.
class StatusBar extends StatelessWidget {
  const StatusBar({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<WebSocketService>(
      builder: (context, ws, _) {
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
          color: ThroneTheme.void1,
          child: Row(
            children: [
              // ── Brand ──
              const Text(
                'THE THRONE',
                style: TextStyle(
                  color: ThroneTheme.textPrimary,
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 2,
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: ThroneTheme.accent.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: const Text(
                  'v2.0',
                  style: TextStyle(
                    color: ThroneTheme.accent,
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),

              const Spacer(),

              // ── Agent Count ──
              Icon(
                Icons.smart_toy_outlined,
                size: 14,
                color: ThroneTheme.textMuted,
              ),
              const SizedBox(width: 4),
              Text(
                '${ws.agents.length} spirits',
                style: const TextStyle(
                  color: ThroneTheme.textSecondary,
                  fontSize: 12,
                ),
              ),

              const SizedBox(width: 20),

              // ── Connection Indicator ──
              AnimatedContainer(
                duration: const Duration(milliseconds: 400),
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  color: ws.isConnected
                      ? ThroneTheme.statusOnline
                      : ThroneTheme.danger,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color:
                          (ws.isConnected
                                  ? ThroneTheme.statusOnline
                                  : ThroneTheme.danger)
                              .withValues(alpha: 0.5),
                      blurRadius: 8,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 6),
              Text(
                ws.isConnected ? 'TETHERED' : 'DISCONNECTED',
                style: TextStyle(
                  color: ws.isConnected
                      ? ThroneTheme.statusOnline
                      : ThroneTheme.danger,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 1,
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
