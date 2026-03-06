import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/theme.dart';
import '../../../models/models.dart';
import '../../../services/api_service.dart';
import '../../../services/websocket_service.dart';

/// Displays all connected agents in a card grid with an expandable
/// activity feed for the currently selected agent.
class AgentGrid extends StatefulWidget {
  final String? selectedAgentId;
  final ValueChanged<String> onAgentSelected;

  const AgentGrid({
    super.key,
    this.selectedAgentId,
    required this.onAgentSelected,
  });

  @override
  State<AgentGrid> createState() => _AgentGridState();
}

class _AgentGridState extends State<AgentGrid> {
  List<Map<String, dynamic>> _activity = [];
  bool _activityLoading = false;
  bool _activityExpanded = false;
  Timer? _refreshTimer;
  String? _loadedAgentId;

  @override
  void initState() {
    super.initState();
    if (widget.selectedAgentId != null) {
      _startActivityPolling(widget.selectedAgentId!);
    }
  }

  @override
  void didUpdateWidget(covariant AgentGrid oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.selectedAgentId != oldWidget.selectedAgentId) {
      _refreshTimer?.cancel();
      if (widget.selectedAgentId != null) {
        _startActivityPolling(widget.selectedAgentId!);
      } else {
        setState(() {
          _activity = [];
          _activityLoading = false;
          _loadedAgentId = null;
        });
      }
    }
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  void _startActivityPolling(String agentId) {
    _fetchActivity(agentId);
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 30),
      (_) => _fetchActivity(agentId),
    );
  }

  Future<void> _fetchActivity(String agentId) async {
    if (!mounted) return;
    setState(() => _activityLoading = true);

    try {
      final limit = _activityExpanded ? 30 : 8;
      final result = await ApiService().getAgentActivity(agentId, limit: limit);
      if (!mounted) return;
      final rawActivity = result['activity'] as List<dynamic>? ?? [];
      setState(() {
        _activity = rawActivity.cast<Map<String, dynamic>>();
        _activityLoading = false;
        _loadedAgentId = agentId;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _activityLoading = false;
        _loadedAgentId = agentId;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: ThroneTheme.void1,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _header(),
          const Divider(height: 1, color: ThroneTheme.void3),
          Expanded(child: _agentList(context)),
        ],
      ),
    );
  }

  Widget _header() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Row(
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: const BoxDecoration(
              color: ThroneTheme.accent,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 10),
          const Text(
            'SPIRITS',
            style: TextStyle(
              color: ThroneTheme.textSecondary,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.5,
            ),
          ),
        ],
      ),
    );
  }

  Widget _agentList(BuildContext context) {
    return Consumer<WebSocketService>(
      builder: (context, ws, _) {
        if (ws.agents.isEmpty) {
          return const Center(
            child: Text(
              'Awaiting state...',
              style: TextStyle(color: ThroneTheme.textMuted, fontSize: 13),
            ),
          );
        }
        return ListView.builder(
          padding: const EdgeInsets.symmetric(vertical: 4),
          itemCount: ws.agents.length,
          itemBuilder: (context, i) {
            final agent = ws.agents[i];
            final isSelected = agent.id == widget.selectedAgentId;
            return Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                _agentCard(agent),
                if (isSelected) _activitySection(),
              ],
            );
          },
        );
      },
    );
  }

  Widget _agentCard(AgentState agent) {
    final isSelected = agent.id == widget.selectedAgentId;
    return InkWell(
      onTap: () => widget.onAgentSelected(agent.id),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: isSelected
              ? ThroneTheme.accent.withValues(alpha: 0.1)
              : ThroneTheme.void2,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isSelected ? ThroneTheme.accent : Colors.transparent,
            width: 1,
          ),
        ),
        child: Row(
          children: [
            // Status indicator
            Container(
              width: 10,
              height: 10,
              decoration: BoxDecoration(
                color: _moodColor(agent.mood),
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: _moodColor(agent.mood).withValues(alpha: 0.4),
                    blurRadius: 6,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    agent.name,
                    style: TextStyle(
                      color: isSelected
                          ? ThroneTheme.accentGlow
                          : ThroneTheme.textPrimary,
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  if (agent.designation.isNotEmpty)
                    Text(
                      agent.designation,
                      style: const TextStyle(
                        color: ThroneTheme.textMuted,
                        fontSize: 11,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                ],
              ),
            ),
            // Mood badge
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: _moodColor(agent.mood).withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                agent.mood,
                style: TextStyle(
                  color: _moodColor(agent.mood),
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _activitySection() {
    final showLoading = _activityLoading && _activity.isEmpty;

    return AnimatedSize(
      duration: const Duration(milliseconds: 250),
      curve: Curves.easeInOut,
      child: Container(
        margin: const EdgeInsets.only(left: 24, right: 8, bottom: 6),
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: ThroneTheme.void1,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: ThroneTheme.void3.withValues(alpha: 0.6),
            width: 1,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                const Text(
                  'RECENT ACTIVITY',
                  style: TextStyle(
                    color: ThroneTheme.textMuted,
                    fontSize: 9,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.2,
                  ),
                ),
                if (_activityLoading && _activity.isNotEmpty) ...[
                  const SizedBox(width: 8),
                  const SizedBox(
                    width: 8,
                    height: 8,
                    child: CircularProgressIndicator(
                      strokeWidth: 1.5,
                      color: ThroneTheme.textMuted,
                    ),
                  ),
                ],
                const Spacer(),
                TextButton.icon(
                  onPressed: () {
                    setState(() => _activityExpanded = !_activityExpanded);
                    if (widget.selectedAgentId != null) {
                      _fetchActivity(widget.selectedAgentId!);
                    }
                  },
                  style: TextButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 6,
                      vertical: 2,
                    ),
                    minimumSize: Size.zero,
                    tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  ),
                  icon: Icon(
                    _activityExpanded
                        ? Icons.unfold_less_rounded
                        : Icons.unfold_more_rounded,
                    size: 14,
                    color: ThroneTheme.accent,
                  ),
                  label: Text(
                    _activityExpanded ? 'Collapse' : 'Expand',
                    style: const TextStyle(
                      color: ThroneTheme.accent,
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                const SizedBox(width: 4),
                TextButton.icon(
                  onPressed: _openActivityLogDialog,
                  style: TextButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 6,
                      vertical: 2,
                    ),
                    minimumSize: Size.zero,
                    tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  ),
                  icon: const Icon(
                    Icons.open_in_new_rounded,
                    size: 13,
                    color: ThroneTheme.textSecondary,
                  ),
                  label: const Text(
                    'Open Log',
                    style: TextStyle(
                      color: ThroneTheme.textSecondary,
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            if (showLoading)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 12),
                child: Center(
                  child: SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: ThroneTheme.accent,
                    ),
                  ),
                ),
              )
            else if (_activity.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 8),
                child: Text(
                  'No activity recorded.',
                  style: TextStyle(
                    color: ThroneTheme.textMuted,
                    fontSize: 11,
                    fontStyle: FontStyle.italic,
                  ),
                ),
              )
            else
              SizedBox(
                height: _activityExpanded ? 280 : 104,
                child: Scrollbar(
                  thumbVisibility: _activityExpanded,
                  child: ListView.builder(
                    padding: EdgeInsets.zero,
                    itemCount: _activity.length,
                    itemBuilder: (context, index) => _activityRow(
                      _activity[index],
                      expanded: _activityExpanded,
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Future<void> _openActivityLogDialog() async {
    final agentId = widget.selectedAgentId;
    if (agentId == null || !mounted) return;

    List<Map<String, dynamic>> actionEntries = [];
    List<Map<String, dynamic>> thoughtEntries = [];
    var loading = true;
    var requested = false;
    var showThoughts = true;

    Future<void> load() async {
      try {
        final api = ApiService();
        final activityResult = await api.getAgentActivity(agentId, limit: 200);
        final rawActivity = activityResult['activity'] as List<dynamic>? ?? [];
        actionEntries = rawActivity.cast<Map<String, dynamic>>();

        // Pull full thought content from system thought logs, then filter by spirit.
        final allThoughts = await api.getSystemThoughts(limit: 300);
        thoughtEntries = allThoughts
            .where((entry) {
              final logAgent =
                  ((entry['agent_id'] ?? '') as String).toLowerCase();
              return logAgent == agentId.toLowerCase();
            })
            .map((entry) {
              return {
                'timestamp': (entry['timestamp'] ?? '') as String,
                'action': (entry['trigger'] ?? 'THOUGHT') as String,
                'details':
                    (entry['thought_content'] ?? '[No thought content]') as String,
              };
            })
            .toList();

        if (thoughtEntries.isEmpty && actionEntries.isNotEmpty) {
          showThoughts = false;
        }
      } catch (_) {
        actionEntries = [];
        thoughtEntries = [];
      } finally {
        loading = false;
      }
    }

    await showDialog<void>(
      context: context,
      barrierDismissible: true,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            if (loading && !requested) {
              requested = true;
              load().then((_) {
                if (context.mounted) setDialogState(() {});
              });
            }

            return Dialog(
              insetPadding: const EdgeInsets.symmetric(
                horizontal: 20,
                vertical: 20,
              ),
              backgroundColor: ThroneTheme.void1,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
                side: BorderSide(
                  color: ThroneTheme.void3.withValues(alpha: 0.8),
                  width: 1,
                ),
              ),
              child: SizedBox(
                width: 980,
                height: 700,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(14, 12, 8, 8),
                      child: Row(
                        children: [
                          const Text(
                            'THOUGHT LOG',
                            style: TextStyle(
                              color: ThroneTheme.textPrimary,
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 1.2,
                            ),
                          ),
                          const SizedBox(width: 10),
                          Text(
                            agentId,
                            style: const TextStyle(
                              color: ThroneTheme.textMuted,
                              fontSize: 11,
                            ),
                          ),
                          const Spacer(),
                          if (!loading)
                            SegmentedButton<bool>(
                              style: ButtonStyle(
                                visualDensity: VisualDensity.compact,
                                side: WidgetStateProperty.all(
                                  const BorderSide(color: ThroneTheme.void3),
                                ),
                              ),
                              selected: {showThoughts},
                              onSelectionChanged: (selection) {
                                setDialogState(() {
                                  showThoughts = selection.first;
                                });
                              },
                              segments: const [
                                ButtonSegment<bool>(
                                  value: true,
                                  label: Text('Thoughts'),
                                ),
                                ButtonSegment<bool>(
                                  value: false,
                                  label: Text('Actions'),
                                ),
                              ],
                            ),
                          IconButton(
                            icon: const Icon(
                              Icons.close_rounded,
                              color: ThroneTheme.textMuted,
                            ),
                            onPressed: () => Navigator.of(context).pop(),
                          ),
                        ],
                      ),
                    ),
                    const Divider(height: 1, color: ThroneTheme.void3),
                    Expanded(
                      child: loading
                          ? const Center(
                              child: CircularProgressIndicator(
                                color: ThroneTheme.accent,
                              ),
                            )
                          : (showThoughts ? thoughtEntries : actionEntries)
                                  .isEmpty
                              ? const Center(
                                  child: Text(
                                    'No activity recorded.',
                                    style: TextStyle(
                                      color: ThroneTheme.textMuted,
                                      fontSize: 12,
                                    ),
                                  ),
                                )
                              : Scrollbar(
                                  thumbVisibility: true,
                                  child: ListView.separated(
                                    padding: const EdgeInsets.all(12),
                                    itemCount: (showThoughts
                                            ? thoughtEntries
                                            : actionEntries)
                                        .length,
                                    separatorBuilder: (_, __) => const Divider(
                                      height: 14,
                                      color: ThroneTheme.void3,
                                    ),
                                    itemBuilder: (context, index) {
                                      final entry = (showThoughts
                                          ? thoughtEntries
                                          : actionEntries)[index];
                                      final action =
                                          (entry['action'] as String?) ?? '';
                                      final details =
                                          (entry['details'] as String?) ?? '';
                                      final ts =
                                          (entry['timestamp'] as String?) ?? '';
                                      final actionColor = _actionColor(action);
                                      return Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            children: [
                                              Text(
                                                _formatTime(ts),
                                                style: const TextStyle(
                                                  color: ThroneTheme.textMuted,
                                                  fontSize: 11,
                                                  fontFamily: 'monospace',
                                                ),
                                              ),
                                              const SizedBox(width: 8),
                                              Text(
                                                action,
                                                style: TextStyle(
                                                  color: actionColor,
                                                  fontSize: 11,
                                                  fontWeight: FontWeight.w700,
                                                ),
                                              ),
                                              const SizedBox(width: 6),
                                              const Text(
                                                '\u2192',
                                                style: TextStyle(
                                                  color: ThroneTheme.textMuted,
                                                  fontSize: 11,
                                                ),
                                              ),
                                            ],
                                          ),
                                          const SizedBox(height: 6),
                                          SelectableText(
                                            details.isEmpty
                                                ? '[No thought content]'
                                                : details,
                                            style: const TextStyle(
                                              color: ThroneTheme.textSecondary,
                                              fontSize: 12,
                                              height: 1.35,
                                            ),
                                          ),
                                        ],
                                      );
                                    },
                                  ),
                                ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  Widget _activityRow(Map<String, dynamic> entry, {bool expanded = false}) {
    final action = (entry['action'] as String?) ?? '';
    final details = (entry['details'] as String?) ?? '';
    final timestamp = entry['timestamp'] as String? ?? '';
    final timeLabel = _formatTime(timestamp);
    final actionColor = _actionColor(action);

    if (expanded) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(
                  width: 40,
                  child: Text(
                    timeLabel,
                    style: const TextStyle(
                      color: ThroneTheme.textMuted,
                      fontSize: 10,
                      fontFamily: 'monospace',
                    ),
                  ),
                ),
                const SizedBox(width: 4),
                Text(
                  action,
                  style: TextStyle(
                    color: actionColor,
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(width: 4),
                const Text(
                  '\u2192',
                  style: TextStyle(
                    color: ThroneTheme.textMuted,
                    fontSize: 10,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 2),
            Padding(
              padding: const EdgeInsets.only(left: 48),
              child: Text(
                details,
                style: const TextStyle(
                  color: ThroneTheme.textSecondary,
                  fontSize: 10,
                  height: 1.25,
                ),
                softWrap: true,
              ),
            ),
          ],
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 40,
            child: Text(
              timeLabel,
              style: const TextStyle(
                color: ThroneTheme.textMuted,
                fontSize: 10,
                fontFamily: 'monospace',
              ),
            ),
          ),
          const SizedBox(width: 4),
          Text(
            action,
            style: TextStyle(
              color: actionColor,
              fontSize: 10,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(width: 4),
          const Text(
            '\u2192',
            style: TextStyle(
              color: ThroneTheme.textMuted,
              fontSize: 10,
            ),
          ),
          const SizedBox(width: 4),
          Expanded(
            child: Text(
              details,
              style: const TextStyle(
                color: ThroneTheme.textSecondary,
                fontSize: 10,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }

  /// Parse ISO-8601 timestamp and return HH:MM in local time.
  String _formatTime(String timestamp) {
    if (timestamp.isEmpty) return '--:--';
    try {
      final dt = DateTime.parse(timestamp).toLocal();
      final h = dt.hour.toString().padLeft(2, '0');
      final m = dt.minute.toString().padLeft(2, '0');
      return '$h:$m';
    } catch (_) {
      return '--:--';
    }
  }

  /// Color-code by action type.
  Color _actionColor(String action) {
    final upper = action.toUpperCase();
    if (upper.startsWith('ACT')) return ThroneTheme.statusOnline;
    if (upper.startsWith('PONDER')) return ThroneTheme.tether;
    if (upper == 'SLEEP') return ThroneTheme.textMuted;
    if (upper == 'MUSE') return ThroneTheme.accent;
    return ThroneTheme.textSecondary;
  }

  Color _moodColor(String mood) {
    switch (mood.toLowerCase()) {
      case 'focused':
      case 'driven':
        return ThroneTheme.accent;
      case 'curious':
      case 'contemplative':
        return ThroneTheme.tether;
      case 'idle':
      case 'resting':
        return ThroneTheme.statusIdle;
      case 'alert':
      case 'excited':
        return ThroneTheme.warning;
      default:
        return ThroneTheme.textSecondary;
    }
  }
}
