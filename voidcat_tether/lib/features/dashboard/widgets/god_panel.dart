import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/theme.dart';
import '../../../services/api_service.dart';
import '../../../services/websocket_service.dart';

/// Right sidebar: GOD MODE command panel.
///
/// Kept separate from the Tether thread flow per WS4 spec.
/// Provides direct agent control:
///   - GOD_SYNC: force identity switch
///   - GOD_MOOD: override mood state
///   - GOD_STIMULI: inject stimuli into inbox
///   - Pulse trigger
class GodPanel extends StatefulWidget {
  final String? selectedAgentId;

  const GodPanel({super.key, this.selectedAgentId});

  @override
  State<GodPanel> createState() => _GodPanelState();
}

class _GodPanelState extends State<GodPanel> {
  final TextEditingController _stimuliCtrl = TextEditingController();
  final TextEditingController _spiritCtrl = TextEditingController();
  final TextEditingController _moodCtrl = TextEditingController();
  String? _lastResult;

  @override
  void dispose() {
    _stimuliCtrl.dispose();
    _spiritCtrl.dispose();
    _moodCtrl.dispose();
    super.dispose();
  }

  String get _agentId => widget.selectedAgentId ?? 'echo';

  @override
  Widget build(BuildContext context) {
    return Container(
      color: ThroneTheme.void1,
      child: Column(
        children: [
          _header(),
          const Divider(height: 1, color: ThroneTheme.void3),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(14),
              children: [
                _targetIndicator(),
                const SizedBox(height: 16),
                _stimuliSection(),
                const SizedBox(height: 16),
                _syncSection(),
                const SizedBox(height: 16),
                _moodSection(),
                const SizedBox(height: 16),
                _pulseSection(),
                if (_lastResult != null) ...[
                  const SizedBox(height: 16),
                  _resultBadge(),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _header() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Row(
        children: [
          Icon(Icons.bolt, size: 16, color: ThroneTheme.warning),
          const SizedBox(width: 8),
          const Text(
            'GOD MODE',
            style: TextStyle(
              color: ThroneTheme.warning,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.5,
            ),
          ),
        ],
      ),
    );
  }

  Widget _targetIndicator() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: ThroneTheme.void2,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: ThroneTheme.void3),
      ),
      child: Row(
        children: [
          const Icon(Icons.gps_fixed, size: 14, color: ThroneTheme.accent),
          const SizedBox(width: 8),
          Text(
            'Target: $_agentId',
            style: const TextStyle(
              color: ThroneTheme.textPrimary,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  // ── GOD_STIMULI ──
  Widget _stimuliSection() {
    return _commandCard(
      title: 'STIMULI',
      icon: Icons.psychology,
      color: ThroneTheme.accent,
      child: Column(
        children: [
          TextField(
            controller: _stimuliCtrl,
            maxLines: 3,
            style: const TextStyle(
              color: ThroneTheme.textPrimary,
              fontSize: 13,
            ),
            decoration: const InputDecoration(
              hintText: 'Inject thought or directive...',
              isDense: true,
            ),
          ),
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _sendStimuli,
              icon: const Icon(Icons.bolt, size: 16),
              label: const Text('Inject'),
              style: ElevatedButton.styleFrom(
                backgroundColor: ThroneTheme.accent,
                foregroundColor: ThroneTheme.void0,
                padding: const EdgeInsets.symmetric(vertical: 10),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ── GOD_SYNC ──
  Widget _syncSection() {
    return _commandCard(
      title: 'SYNC IDENTITY',
      icon: Icons.swap_horiz,
      color: ThroneTheme.tether,
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _spiritCtrl,
              style: const TextStyle(
                color: ThroneTheme.textPrimary,
                fontSize: 13,
              ),
              decoration: const InputDecoration(
                hintText: 'Spirit name...',
                isDense: true,
              ),
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            onPressed: _sendSync,
            icon: const Icon(Icons.sync, size: 20),
            color: ThroneTheme.tether,
            tooltip: 'Sync',
          ),
        ],
      ),
    );
  }

  // ── GOD_MOOD ──
  Widget _moodSection() {
    return _commandCard(
      title: 'OVERRIDE MOOD',
      icon: Icons.mood,
      color: ThroneTheme.warning,
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _moodCtrl,
              style: const TextStyle(
                color: ThroneTheme.textPrimary,
                fontSize: 13,
              ),
              decoration: const InputDecoration(
                hintText: 'Mood state...',
                isDense: true,
              ),
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            onPressed: _sendMood,
            icon: const Icon(Icons.check_circle_outline, size: 20),
            color: ThroneTheme.warning,
            tooltip: 'Apply',
          ),
        ],
      ),
    );
  }

  // ── Pulse ──
  Widget _pulseSection() {
    return _commandCard(
      title: 'TRIGGER PULSE',
      icon: Icons.favorite_border,
      color: ThroneTheme.danger,
      child: SizedBox(
        width: double.infinity,
        child: ElevatedButton.icon(
          onPressed: _triggerPulse,
          icon: const Icon(Icons.favorite, size: 16),
          label: const Text('Pulse'),
          style: ElevatedButton.styleFrom(
            backgroundColor: ThroneTheme.danger.withValues(alpha: 0.8),
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 10),
          ),
        ),
      ),
    );
  }

  Widget _commandCard({
    required String title,
    required IconData icon,
    required Color color,
    required Widget child,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: ThroneTheme.void2,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: ThroneTheme.void3),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 14, color: color),
              const SizedBox(width: 6),
              Text(
                title,
                style: TextStyle(
                  color: color,
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          child,
        ],
      ),
    );
  }

  Widget _resultBadge() {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: ThroneTheme.success.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: ThroneTheme.success.withValues(alpha: 0.3)),
      ),
      child: Text(
        _lastResult!,
        style: const TextStyle(
          color: ThroneTheme.success,
          fontSize: 11,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }

  // ── Actions ──

  void _sendStimuli() {
    final text = _stimuliCtrl.text.trim();
    if (text.isEmpty) return;
    context.read<WebSocketService>().godStimuli(
      agentId: _agentId,
      content: text,
    );
    _stimuliCtrl.clear();
    setState(() => _lastResult = 'GOD_STIMULI → $_agentId');
  }

  void _sendSync() {
    final spirit = _spiritCtrl.text.trim();
    if (spirit.isEmpty) return;
    context.read<WebSocketService>().godSync(agentId: _agentId, spirit: spirit);
    _spiritCtrl.clear();
    setState(() => _lastResult = 'GOD_SYNC → $_agentId → $spirit');
  }

  void _sendMood() {
    final mood = _moodCtrl.text.trim();
    if (mood.isEmpty) return;
    context.read<WebSocketService>().godMood(agentId: _agentId, mood: mood);
    _moodCtrl.clear();
    setState(() => _lastResult = 'GOD_MOOD → $_agentId → $mood');
  }

  Future<void> _triggerPulse() async {
    try {
      await context.read<ApiService>().triggerPulse(agentId: _agentId);
      setState(() => _lastResult = 'Pulse triggered for $_agentId');
    } catch (e) {
      setState(() => _lastResult = 'Pulse failed: $e');
    }
  }
}
