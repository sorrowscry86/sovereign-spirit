import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme.dart';
import '../../services/websocket_service.dart';
import 'widgets/agent_grid.dart';
import 'widgets/thread_panel.dart';
import 'widgets/god_panel.dart';
import 'widgets/bifrost_panel.dart';
import 'widgets/tools_panel.dart';
import 'widgets/interagent_panel.dart';
import 'widgets/status_bar.dart';

/// The Throne — main dashboard / control center.
///
/// Layout:
///   ┌──────────────────────────────────────────────────┐
///   │  Status Bar                                      │
///   ├────────────┬─────────────────┬───────────────────┤
///   │ Agent Grid │  Thread Panel   │ ⚡│🌈│🔧│💬 Tabs  │
///   │ (sidebar)  │  (center)       │ [Tabbed Panel]    │
///   └────────────┴─────────────────┴───────────────────┘
class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage>
    with SingleTickerProviderStateMixin {
  String? _selectedAgentId;
  String? _activeThreadId;
  late TabController _tabController;

  static const _tabIcons = [
    Icons.bolt, // GOD
    Icons.blur_on, // Bifrost
    Icons.build_circle, // Tools
    Icons.forum, // Comms
  ];

  static const _tabLabels = ['GOD', 'BIFROST', 'TOOLS', 'COMMS'];

  static const _tabColors = [
    ThroneTheme.accent,
    ThroneTheme.bifrostBridge,
    ThroneTheme.tether,
    ThroneTheme.accent,
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    // auto-connect on load
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<WebSocketService>().connect();
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _onAgentSelected(String agentId) {
    setState(() {
      _selectedAgentId = agentId;
      _activeThreadId = null; // reset thread when switching agent
    });
  }

  void _onThreadSelected(String threadId) {
    setState(() => _activeThreadId = threadId);
    // Subscribe to thread events
    context.read<WebSocketService>().joinThread(threadId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: ThroneTheme.void0,
      body: Column(
        children: [
          // ── Status Bar ──
          const StatusBar(),
          const Divider(height: 1, color: ThroneTheme.void3),

          // ── Main Content ──
          Expanded(
            child: Row(
              children: [
                // ── Left: Agent Grid ──
                SizedBox(
                  width: 300,
                  child: AgentGrid(
                    selectedAgentId: _selectedAgentId,
                    onAgentSelected: _onAgentSelected,
                  ),
                ),
                const VerticalDivider(width: 1, color: ThroneTheme.void3),

                // ── Center: Thread Panel ──
                Expanded(
                  child: ThreadPanel(
                    agentId: _selectedAgentId,
                    activeThreadId: _activeThreadId,
                    onThreadSelected: _onThreadSelected,
                  ),
                ),
                const VerticalDivider(width: 1, color: ThroneTheme.void3),

                // ── Right: Tabbed Control Panel ──
                SizedBox(width: 320, child: _controlPanel()),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// Tabbed right sidebar: GOD | Bifrost | Tools | Comms
  Widget _controlPanel() {
    return Column(
      children: [
        // ── Tab Bar ──
        Container(
          color: ThroneTheme.void1,
          child: AnimatedBuilder(
            animation: _tabController,
            builder: (context, _) {
              return Row(
                children: List.generate(4, (i) {
                  final isActive = _tabController.index == i;
                  return Expanded(
                    child: InkWell(
                      onTap: () => setState(() => _tabController.animateTo(i)),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        padding: const EdgeInsets.symmetric(vertical: 10),
                        decoration: BoxDecoration(
                          border: Border(
                            bottom: BorderSide(
                              color: isActive
                                  ? _tabColors[i]
                                  : Colors.transparent,
                              width: 2,
                            ),
                          ),
                        ),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              _tabIcons[i],
                              size: 14,
                              color: isActive
                                  ? _tabColors[i]
                                  : ThroneTheme.textMuted,
                            ),
                            const SizedBox(height: 3),
                            Text(
                              _tabLabels[i],
                              style: TextStyle(
                                color: isActive
                                    ? _tabColors[i]
                                    : ThroneTheme.textMuted,
                                fontSize: 8,
                                fontWeight: FontWeight.w700,
                                letterSpacing: 1,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  );
                }),
              );
            },
          ),
        ),
        const Divider(height: 1, color: ThroneTheme.void3),

        // ── Tab Content ──
        Expanded(
          child: TabBarView(
            controller: _tabController,
            physics: const NeverScrollableScrollPhysics(),
            children: [
              GodPanel(selectedAgentId: _selectedAgentId),
              const BifrostPanel(),
              const ToolsPanel(),
              const InteragentPanel(),
            ],
          ),
        ),
      ],
    );
  }
}
