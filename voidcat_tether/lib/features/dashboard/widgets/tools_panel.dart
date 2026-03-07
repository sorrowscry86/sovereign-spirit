import 'dart:convert';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/theme.dart';
import '../../../models/models.dart';
import '../../../services/api_service.dart';
import '../../../services/websocket_service.dart';

/// Known MCP server presets with pre-filled command/args.
class _ServerPreset {
  final String name;
  final String command;
  final List<String> args;
  final int securityTier;

  const _ServerPreset({
    required this.name,
    required this.command,
    required this.args,
    required this.securityTier,
  });
}

const Map<String, _ServerPreset> _knownPresets = {
  'filesystem': _ServerPreset(
    name: 'filesystem',
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/server-filesystem', '/app'],
    securityTier: 3,
  ),
  'git': _ServerPreset(
    name: 'git',
    command: 'python',
    args: ['src/mcp/servers/git.py'],
    securityTier: 2,
  ),
  'chronos': _ServerPreset(
    name: 'chronos',
    command: 'python',
    args: ['src/mcp/servers/chronos.py'],
    securityTier: 1,
  ),
  'search': _ServerPreset(
    name: 'search',
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/server-brave-search'],
    securityTier: 1,
  ),
  'perplexity': _ServerPreset(
    name: 'perplexity',
    command: 'npx',
    args: ['-y', '@perplexity-ai/mcp-server'],
    securityTier: 1,
  ),
};

/// Tools Panel -- MCP tool registry viewer with server management
/// and per-tool testing.
class ToolsPanel extends StatefulWidget {
  const ToolsPanel({super.key});

  @override
  State<ToolsPanel> createState() => _ToolsPanelState();
}

class _ToolsPanelState extends State<ToolsPanel> {
  final ApiService _api = ApiService();

  Map<String, List<Map<String, dynamic>>> _servers = {};
  Map<String, bool> _registeredServers = {};
  List<String> _connectedServers = [];
  int _totalTools = 0;
  bool _loading = true;

  // Add-server form state
  bool _showAddForm = false;
  String _selectedPreset = 'filesystem';
  final TextEditingController _customNameCtrl = TextEditingController();
  final TextEditingController _customCommandCtrl = TextEditingController();
  final TextEditingController _customArgsCtrl = TextEditingController();
  final TextEditingController _customTierCtrl = TextEditingController(text: '1');
  bool _addingServer = false;

  // Per-server loading state (for reconnect)
  final Set<String> _serverLoading = {};

  // Per-tool test expansion + state
  final Map<String, bool> _toolTestExpanded = {};
  final Map<String, TextEditingController> _toolArgControllers = {};
  final Map<String, String?> _toolTestResults = {};
  final Map<String, bool> _toolTestRunning = {};

  StreamSubscription<ToolUseEvent>? _toolSub;
  StreamSubscription<ToolApprovalRequest>? _approvalSub;
  final List<ToolUseEvent> _recentEvents = [];
  final Map<String, ToolApprovalRequest> _pendingApprovals = {};

  @override
  void initState() {
    super.initState();
    final ws = context.read<WebSocketService>();
    _toolSub = ws.onToolUse.listen(_onToolEvent);
    _approvalSub = ws.onToolApprovalRequired.listen(_onApprovalRequired);
    _loadTools();
  }

  @override
  void dispose() {
    _toolSub?.cancel();
    _approvalSub?.cancel();
    _customNameCtrl.dispose();
    _customCommandCtrl.dispose();
    _customArgsCtrl.dispose();
    _customTierCtrl.dispose();
    for (final ctrl in _toolArgControllers.values) {
      ctrl.dispose();
    }
    super.dispose();
  }

  void _onToolEvent(ToolUseEvent event) {
    if (!mounted) return;
    setState(() {
      _recentEvents.insert(0, event);
      if (_recentEvents.length > 40) {
        _recentEvents.removeRange(40, _recentEvents.length);
      }
      if (event.phase == 'completed' || event.phase == 'failed') {
        _pendingApprovals.remove(event.chainId);
      }
    });
  }

  void _onApprovalRequired(ToolApprovalRequest request) {
    if (!mounted) return;
    setState(() {
      _pendingApprovals[request.chainId] = request;
    });
  }

  Future<void> _loadTools() async {
    try {
      final data = await _api.getToolRegistry();
      final registryData = await _api.getMCPRegistry();
      if (!mounted) return;
      final servers = data['servers'] as Map<String, dynamic>? ?? {};
      final registry = registryData['servers'] as Map<String, dynamic>? ?? {};
      setState(() {
        _totalTools = data['total_tools'] as int? ?? 0;
        _connectedServers =
            (data['connected_servers'] as List<dynamic>?)?.cast<String>() ?? [];
        _servers = servers.map(
          (k, v) => MapEntry(
            k,
            (v as List<dynamic>)
                .map((e) => e as Map<String, dynamic>)
                .toList(),
          ),
        );
        _registeredServers = registry.map(
          (k, v) => MapEntry(k, (v['connected'] as bool?) ?? false),
        );
        _loading = false;
      });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _reconnectServer(String name) async {
    setState(() => _serverLoading.add(name));
    try {
      await _api.connectMCPServer(name);
      await _loadTools();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to connect $name: $e'),
            backgroundColor: ThroneTheme.danger,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _serverLoading.remove(name));
    }
  }

  Future<void> _disconnectServer(String name) async {
    setState(() => _serverLoading.add(name));
    try {
      await _api.disconnectMCPServer(name);
      await _loadTools();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to disconnect $name: $e'),
            backgroundColor: ThroneTheme.danger,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _serverLoading.remove(name));
    }
  }

  Future<void> _addServer() async {
    setState(() => _addingServer = true);
    try {
      String name;
      String command;
      List<String> args;

      if (_selectedPreset == 'custom') {
        name = _customNameCtrl.text.trim();
        command = _customCommandCtrl.text.trim();
        args = _customArgsCtrl.text.trim().split(RegExp(r'\s+'));
        if (name.isEmpty || command.isEmpty) {
          setState(() => _addingServer = false);
          return;
        }
        final customTier = int.tryParse(_customTierCtrl.text.trim()) ?? 1;
        await _api.addMCPServer(
          name,
          command,
          args,
          securityTier: customTier,
        );
      } else {
        final preset = _knownPresets[_selectedPreset]!;
        name = preset.name;
        command = preset.command;
        args = preset.args;
        await _api.addMCPServer(
          name,
          command,
          args,
          securityTier: preset.securityTier,
        );
      }

      await _api.connectMCPServer(name);
      await _loadTools();

      if (mounted) {
        setState(() {
          _showAddForm = false;
          _addingServer = false;
          _customNameCtrl.clear();
          _customCommandCtrl.clear();
          _customArgsCtrl.clear();
        });
      }
    } catch (_) {
      if (mounted) setState(() => _addingServer = false);
    }
  }

  String _toolKey(String server, String tool) => '$server::$tool';

  Future<void> _runToolTest(String server, String tool) async {
    final key = _toolKey(server, tool);
    setState(() {
      _toolTestRunning[key] = true;
      _toolTestResults[key] = null;
    });

    try {
      final ctrl = _toolArgControllers[key];
      final argsText = ctrl?.text.trim() ?? '{}';
      Map<String, dynamic> args;
      try {
        args = jsonDecode(argsText) as Map<String, dynamic>;
      } catch (_) {
        setState(() {
          _toolTestResults[key] = 'Error: Invalid JSON';
          _toolTestRunning[key] = false;
        });
        return;
      }

      final result = await _api.testMCPTool(server, tool, args);
      if (mounted) {
        const encoder = JsonEncoder.withIndent('  ');
        setState(() {
          _toolTestResults[key] = encoder.convert(result);
          _toolTestRunning[key] = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _toolTestResults[key] = 'Error: $e';
          _toolTestRunning[key] = false;
        });
      }
    }
  }

  // ── Build ──

  @override
  Widget build(BuildContext context) {
    return Container(
      color: ThroneTheme.void1,
      child: Column(
        children: [
          _header(),
          const Divider(height: 1, color: ThroneTheme.void3),
          if (_showAddForm) _addServerForm(),
          Expanded(
            child: _loading
                ? const Center(
                    child:
                        CircularProgressIndicator(color: ThroneTheme.tether),
                  )
                : (_servers.isEmpty && _registeredServers.isEmpty)
                    ? _emptyState()
                    : Builder(
                        builder: (context) {
                          final allServerNames = {
                            ..._registeredServers.keys,
                            ..._servers.keys,
                          }.toList()
                            ..sort();

                          return ListView(
                            padding: const EdgeInsets.all(14),
                            children: [
                              if (_pendingApprovals.isNotEmpty)
                                _approvalQueueCard(),
                              if (_recentEvents.isNotEmpty) _toolFeedCard(),
                              ...allServerNames.map(
                                (name) => _serverGroup(
                                  name,
                                  _servers[name] ?? const [],
                                ),
                              ),
                            ],
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }

  // ── Header ──

  Widget _header() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Row(
        children: [
          const Icon(Icons.build_circle, size: 16, color: ThroneTheme.tether),
          const SizedBox(width: 8),
          const Text(
            'TOOLS',
            style: TextStyle(
              color: ThroneTheme.tether,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.5,
            ),
          ),
          const Spacer(),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: ThroneTheme.tether.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(
              '$_totalTools',
              style: const TextStyle(
                color: ThroneTheme.tether,
                fontSize: 11,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          const SizedBox(width: 8),
          InkWell(
            onTap: () {
              setState(() => _showAddForm = !_showAddForm);
            },
            borderRadius: BorderRadius.circular(4),
            child: Icon(
              _showAddForm ? Icons.close : Icons.add,
              size: 14,
              color: ThroneTheme.tether,
            ),
          ),
          const SizedBox(width: 8),
          InkWell(
            onTap: () {
              setState(() => _loading = true);
              _loadTools();
            },
            borderRadius: BorderRadius.circular(4),
            child: const Icon(
              Icons.refresh,
              size: 14,
              color: ThroneTheme.textMuted,
            ),
          ),
        ],
      ),
    );
  }

  // ── Add Server Form ──

  Widget _addServerForm() {
    final isCustom = _selectedPreset == 'custom';
    final preset = isCustom ? null : _knownPresets[_selectedPreset];

    return Container(
      margin: const EdgeInsets.fromLTRB(14, 0, 14, 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: ThroneTheme.void2,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: ThroneTheme.tether.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'ADD SERVER',
            style: TextStyle(
              color: ThroneTheme.tether,
              fontSize: 10,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: 10),

          // Type dropdown
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10),
            decoration: BoxDecoration(
              color: ThroneTheme.void1,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: ThroneTheme.void3),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: _selectedPreset,
                isExpanded: true,
                dropdownColor: ThroneTheme.void2,
                style: const TextStyle(
                  color: ThroneTheme.textPrimary,
                  fontSize: 12,
                ),
                items: const [
                  DropdownMenuItem(
                      value: 'filesystem', child: Text('Filesystem')),
                  DropdownMenuItem(value: 'git', child: Text('Git')),
                  DropdownMenuItem(value: 'chronos', child: Text('Chronos')),
                  DropdownMenuItem(value: 'search', child: Text('Search')),
                  DropdownMenuItem(
                    value: 'perplexity',
                    child: Text('Perplexity'),
                  ),
                  DropdownMenuItem(value: 'custom', child: Text('Custom')),
                ],
                onChanged: (v) {
                  if (v != null) setState(() => _selectedPreset = v);
                },
              ),
            ),
          ),
          const SizedBox(height: 8),

          // Preset info or custom fields
          if (!isCustom && preset != null) ...[
            _readOnlyField('Command', preset.command),
            const SizedBox(height: 4),
            _readOnlyField('Args', preset.args.join(' ')),
          ],
          if (isCustom) ...[
            _inputField(_customNameCtrl, 'Server name'),
            const SizedBox(height: 6),
            _inputField(_customCommandCtrl, 'Command (e.g. npx, python)'),
            const SizedBox(height: 6),
            _inputField(_customArgsCtrl, 'Args (space-separated)'),
            const SizedBox(height: 6),
            _inputField(_customTierCtrl, 'Security tier (0-3)'),
          ],
          const SizedBox(height: 10),

          // Buttons
          Row(
            children: [
              Expanded(
                child: SizedBox(
                  height: 32,
                  child: ElevatedButton(
                    onPressed: _addingServer ? null : _addServer,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: ThroneTheme.tether,
                      foregroundColor: ThroneTheme.void0,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(6),
                      ),
                      padding: EdgeInsets.zero,
                    ),
                    child: _addingServer
                        ? const SizedBox(
                            width: 14,
                            height: 14,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: ThroneTheme.void0,
                            ),
                          )
                        : const Text(
                            'Connect',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              SizedBox(
                height: 32,
                child: TextButton(
                  onPressed: () => setState(() => _showAddForm = false),
                  style: TextButton.styleFrom(
                    foregroundColor: ThroneTheme.textMuted,
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                  ),
                  child: const Text(
                    'Cancel',
                    style: TextStyle(fontSize: 11),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _readOnlyField(String label, String value) {
    return Row(
      children: [
        SizedBox(
          width: 60,
          child: Text(
            label,
            style: const TextStyle(
              color: ThroneTheme.textMuted,
              fontSize: 10,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        Expanded(
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
            decoration: BoxDecoration(
              color: ThroneTheme.void1,
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              value,
              style: const TextStyle(
                color: ThroneTheme.textSecondary,
                fontSize: 10,
                fontFamily: 'monospace',
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ),
      ],
    );
  }

  Widget _inputField(TextEditingController controller, String hint) {
    return SizedBox(
      height: 32,
      child: TextField(
        controller: controller,
        style: const TextStyle(
          color: ThroneTheme.textPrimary,
          fontSize: 11,
        ),
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: const TextStyle(color: ThroneTheme.textMuted, fontSize: 11),
          filled: true,
          fillColor: ThroneTheme.void1,
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 10, vertical: 0),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(6),
            borderSide: const BorderSide(color: ThroneTheme.void3),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(6),
            borderSide: const BorderSide(color: ThroneTheme.void3),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(6),
            borderSide: const BorderSide(color: ThroneTheme.tether),
          ),
        ),
      ),
    );
  }

  // ── Empty State ──

  Widget _emptyState() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.extension_off, size: 40, color: ThroneTheme.textMuted),
          const SizedBox(height: 12),
          const Text(
            'No MCP tools connected',
            style: TextStyle(color: ThroneTheme.textMuted, fontSize: 13),
          ),
        ],
      ),
    );
  }

  // ── Server Group ──

  Widget _approvalQueueCard() {
    final ws = context.read<WebSocketService>();
    final approvals = _pendingApprovals.values.toList()
      ..sort((a, b) => (b.timestamp ?? DateTime.now()).compareTo(
            a.timestamp ?? DateTime.now(),
          ));

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: ThroneTheme.void2,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: ThroneTheme.accent.withValues(alpha: 0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'APPROVAL REQUIRED',
            style: TextStyle(
              color: ThroneTheme.accent,
              fontSize: 10,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: 8),
          ...approvals.map((req) {
            final chainLabel = req.chainId.isNotEmpty
                ? req.chainId.substring(0, req.chainId.length < 8 ? req.chainId.length : 8)
                : 'unknown';
            return Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: ThroneTheme.void1,
                borderRadius: BorderRadius.circular(6),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${req.server}.${req.tool}',
                    style: const TextStyle(
                      color: ThroneTheme.textPrimary,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      fontFamily: 'monospace',
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    'chain=$chainLabel step=${req.chainStep} ttl=${req.ttlSeconds}s',
                    style: const TextStyle(
                      color: ThroneTheme.textMuted,
                      fontSize: 10,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      Expanded(
                        child: SizedBox(
                          height: 28,
                          child: ElevatedButton(
                            onPressed: () => ws.approveToolUse(req.chainId),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: ThroneTheme.statusOnline,
                              foregroundColor: ThroneTheme.void0,
                            ),
                            child: const Text(
                              'Approve',
                              style: TextStyle(fontSize: 10),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: SizedBox(
                          height: 28,
                          child: ElevatedButton(
                            onPressed: () => ws.denyToolUse(req.chainId),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: ThroneTheme.danger,
                              foregroundColor: ThroneTheme.void0,
                            ),
                            child: const Text(
                              'Deny',
                              style: TextStyle(fontSize: 10),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }

  Widget _toolFeedCard() {
    final items = _recentEvents.take(8).toList();
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: ThroneTheme.void2,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: ThroneTheme.void3),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'TOOL FEED',
            style: TextStyle(
              color: ThroneTheme.tether,
              fontSize: 10,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: 8),
          ...items.map((event) {
            final color = _phaseColor(event.phase);
            return Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: color.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(
                      event.phase,
                      style: TextStyle(
                        color: color,
                        fontSize: 9,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      '${event.server}.${event.tool} (${event.durationMs ?? 0} ms)',
                      style: const TextStyle(
                        color: ThroneTheme.textSecondary,
                        fontSize: 10,
                        fontFamily: 'monospace',
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }

  Color _phaseColor(String phase) {
    switch (phase) {
      case 'completed':
        return ThroneTheme.statusOnline;
      case 'failed':
        return ThroneTheme.danger;
      case 'executing':
        return ThroneTheme.accent;
      default:
        return ThroneTheme.textMuted;
    }
  }

  Widget _serverGroup(String serverName, List<Map<String, dynamic>> tools) {
    final isConnected = _connectedServers.contains(serverName);
    final isLoading = _serverLoading.contains(serverName);
    final previewNames = tools
      .take(3)
      .map((t) => (t['name'] as String? ?? 'unknown'))
      .toList();
    final previewText = previewNames.isEmpty
      ? 'No tools loaded'
      : previewNames.join('  |  ');

    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Container(
        decoration: BoxDecoration(
          color: ThroneTheme.void2,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: isConnected
                ? ThroneTheme.tether.withValues(alpha: 0.2)
                : ThroneTheme.void3,
          ),
        ),
        child: Theme(
          data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
          child: ExpansionTile(
            initiallyExpanded: isConnected && tools.isNotEmpty,
            maintainState: true,
            tilePadding: const EdgeInsets.symmetric(horizontal: 12),
            childrenPadding: const EdgeInsets.only(
              left: 12,
              right: 12,
              bottom: 10,
            ),
            leading: isLoading
                ? const SizedBox(
                    width: 10,
                    height: 10,
                    child: CircularProgressIndicator(
                      strokeWidth: 1.5,
                      color: ThroneTheme.tether,
                    ),
                  )
                : Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: isConnected
                          ? ThroneTheme.statusOnline
                          : ThroneTheme.statusOffline,
                    ),
                  ),
            title: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        serverName.toUpperCase(),
                        style: const TextStyle(
                          color: ThroneTheme.textPrimary,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 1,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 2),
                      Text(
                        previewText,
                        style: const TextStyle(
                          color: ThroneTheme.textMuted,
                          fontSize: 9,
                          fontFamily: 'monospace',
                        ),
                        overflow: TextOverflow.ellipsis,
                        maxLines: 1,
                      ),
                    ],
                  ),
                ),
                Text(
                  '${tools.length}',
                  style: const TextStyle(
                    color: ThroneTheme.textMuted,
                    fontSize: 11,
                  ),
                ),
                const SizedBox(width: 8),
                _serverActionButton(
                  icon: Icons.sync,
                  tooltip: isConnected ? 'Reconnect' : 'Connect',
                  color: ThroneTheme.tether,
                  onTap: isLoading
                      ? null
                      : () => _reconnectServer(serverName),
                ),
                const SizedBox(width: 4),
                _serverActionButton(
                  icon: Icons.power_settings_new,
                  tooltip: 'Disconnect',
                  color: ThroneTheme.danger,
                  onTap: isLoading
                      ? null
                      : () => _disconnectServer(serverName),
                ),
              ],
            ),
            children: tools.isEmpty
                ? [
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 4),
                      child: Text(
                        'No tools loaded. Connect this server to load tools.',
                        style: TextStyle(
                          color: ThroneTheme.textMuted,
                          fontSize: 10,
                        ),
                      ),
                    ),
                  ]
                : tools.map((tool) => _toolTile(serverName, tool)).toList(),
          ),
        ),
      ),
    );
  }

  Widget _serverActionButton({
    required IconData icon,
    required String tooltip,
    required Color color,
    VoidCallback? onTap,
  }) {
    return Tooltip(
      message: tooltip,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(4),
        child: Padding(
          padding: const EdgeInsets.all(4),
          child: Icon(
            icon,
            size: 13,
            color: onTap != null
                ? color.withValues(alpha: 0.8)
                : ThroneTheme.textMuted.withValues(alpha: 0.4),
          ),
        ),
      ),
    );
  }

  // ── Tool Tile ──

  Widget _toolTile(String serverName, Map<String, dynamic> tool) {
    final name = tool['name'] as String? ?? 'unknown';
    final description = tool['description'] as String? ?? '';
    final key = _toolKey(serverName, name);
    final isExpanded = _toolTestExpanded[key] ?? false;
    final isRunning = _toolTestRunning[key] ?? false;
    final result = _toolTestResults[key];

    // Lazily create arg controller
    _toolArgControllers.putIfAbsent(key, () => TextEditingController(text: '{}'));

    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: ThroneTheme.void1,
          borderRadius: BorderRadius.circular(6),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Tool header row
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        name,
                        style: const TextStyle(
                          color: ThroneTheme.accent,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          fontFamily: 'monospace',
                        ),
                      ),
                      if (description.isNotEmpty) ...[
                        const SizedBox(height: 3),
                        Text(
                          description,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: ThroneTheme.textMuted,
                            fontSize: 10,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                InkWell(
                  onTap: () {
                    setState(() {
                      _toolTestExpanded[key] = !isExpanded;
                    });
                  },
                  borderRadius: BorderRadius.circular(4),
                  child: Container(
                    padding: const EdgeInsets.all(4),
                    decoration: BoxDecoration(
                      color: isExpanded
                          ? ThroneTheme.accent.withValues(alpha: 0.15)
                          : Colors.transparent,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Icon(
                      Icons.play_arrow,
                      size: 14,
                      color: isExpanded
                          ? ThroneTheme.accent
                          : ThroneTheme.textMuted,
                    ),
                  ),
                ),
              ],
            ),

            // Test form (expanded)
            if (isExpanded) ...[
              const SizedBox(height: 8),
              const Divider(height: 1, color: ThroneTheme.void3),
              const SizedBox(height: 8),
              const Text(
                'ARGUMENTS (JSON)',
                style: TextStyle(
                  color: ThroneTheme.textMuted,
                  fontSize: 9,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 1,
                ),
              ),
              const SizedBox(height: 4),
              SizedBox(
                height: 32,
                child: TextField(
                  controller: _toolArgControllers[key],
                  style: const TextStyle(
                    color: ThroneTheme.textPrimary,
                    fontSize: 11,
                    fontFamily: 'monospace',
                  ),
                  decoration: InputDecoration(
                    filled: true,
                    fillColor: ThroneTheme.void0,
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 0,
                    ),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(4),
                      borderSide: const BorderSide(color: ThroneTheme.void3),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(4),
                      borderSide: const BorderSide(color: ThroneTheme.void3),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(4),
                      borderSide:
                          const BorderSide(color: ThroneTheme.accent),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 6),
              SizedBox(
                height: 28,
                width: double.infinity,
                child: ElevatedButton(
                  onPressed:
                      isRunning ? null : () => _runToolTest(serverName, name),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: ThroneTheme.accent,
                    foregroundColor: ThroneTheme.void0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(4),
                    ),
                    padding: EdgeInsets.zero,
                  ),
                  child: isRunning
                      ? const SizedBox(
                          width: 12,
                          height: 12,
                          child: CircularProgressIndicator(
                            strokeWidth: 1.5,
                            color: ThroneTheme.void0,
                          ),
                        )
                      : const Text(
                          'Run',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                ),
              ),
              if (result != null) ...[
                const SizedBox(height: 6),
                Container(
                  width: double.infinity,
                  constraints: const BoxConstraints(maxHeight: 160),
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: ThroneTheme.void0,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(
                      color: ThroneTheme.void3.withValues(alpha: 0.5),
                    ),
                  ),
                  child: SingleChildScrollView(
                    child: Text(
                      result,
                      style: TextStyle(
                        color: result.startsWith('Error:')
                            ? ThroneTheme.danger
                            : ThroneTheme.textSecondary,
                        fontSize: 10,
                        fontFamily: 'monospace',
                        height: 1.4,
                      ),
                    ),
                  ),
                ),
              ],
            ],
          ],
        ),
      ),
    );
  }
}
