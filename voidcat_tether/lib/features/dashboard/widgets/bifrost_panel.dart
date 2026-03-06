import 'package:flutter/material.dart';
import 'dart:async';

import '../../../core/theme.dart';
import '../../../services/api_service.dart';

/// Bifrost Panel — LLM provider configuration and inference routing.
///
/// Full-featured control surface showing:
///   - Cloud failure banner (dismissible)
///   - Inference mode switcher (AUTO/LOCAL/CLOUD)
///   - Active route visualization with pulse animation
///   - Reorderable fallback chain
///   - Expandable provider cards with config editing and test tools
class BifrostPanel extends StatefulWidget {
  const BifrostPanel({super.key});

  @override
  State<BifrostPanel> createState() => _BifrostPanelState();
}

class _BifrostPanelState extends State<BifrostPanel>
    with TickerProviderStateMixin {
  // ── State ──
  String _mode = 'AUTO';
  String _currentRoute = 'LOCAL';
  bool _cloudHealthy = true;
  String? _lastCloudFailure;
  String? _lastCloudFailureAt;
  bool _bannerDismissed = false;

  Map<String, dynamic> _healthProviders = {};
  Map<String, dynamic> _configProviders = {};
  List<String> _fallbackChain = [];
  String _activeProvider = '';
  String _selectedLocalProvider = '';
  String _selectedCloudProvider = '';
  final TextEditingController _localModelController = TextEditingController();
  final TextEditingController _cloudModelController = TextEditingController();

  bool _loading = true;

  // Per-provider expanded state
  final Set<String> _expandedProviders = {};

  // Per-provider edit state (keyed by provider name)
  final Map<String, _ProviderEditState> _editStates = {};

  // ── Animation ──
  late AnimationController _pulseController;
  late AnimationController _bridgeController;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);
    _bridgeController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat();
    _loadData();
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 30),
      (_) => _loadData(),
    );
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _bridgeController.dispose();
    _refreshTimer?.cancel();
    _localModelController.dispose();
    _cloudModelController.dispose();
    for (final es in _editStates.values) {
      es.dispose();
    }
    super.dispose();
  }

  String _providerTypeFor(String name) {
    final cfg = _configProviders[name] as Map<String, dynamic>?;
    if (cfg != null && cfg['type'] is String) {
      return cfg['type'] as String;
    }
    final health = _healthProviders[name] as Map<String, dynamic>?;
    return (health?['type'] as String?) ?? '';
  }

  List<String> _providersByType(Set<String> types) {
    final names = <String>{
      ..._configProviders.keys,
      ..._healthProviders.keys,
      ..._fallbackChain,
    };
    return names.where((n) => types.contains(_providerTypeFor(n))).toList()
      ..sort();
  }

  String _providerModel(String name) {
    final es = _editStates[name];
    if (es != null && es.modelController.text.isNotEmpty) {
      return es.modelController.text;
    }
    final cfg = _configProviders[name] as Map<String, dynamic>?;
    return (cfg?['model'] as String?) ?? '';
  }

  void _syncRouteSelections() {
    final localCandidates = _providersByType({'ollama', 'lm_studio'});
    final cloudCandidates = _providersByType({'openrouter', 'openai'});

    if (_selectedLocalProvider.isEmpty ||
        !localCandidates.contains(_selectedLocalProvider)) {
      _selectedLocalProvider = localCandidates.isNotEmpty
          ? localCandidates.first
          : '';
    }
    if (_selectedCloudProvider.isEmpty ||
        !cloudCandidates.contains(_selectedCloudProvider)) {
      _selectedCloudProvider = cloudCandidates.isNotEmpty
          ? cloudCandidates.first
          : '';
    }

    if (_selectedLocalProvider.isNotEmpty) {
      _localModelController.text = _providerModel(_selectedLocalProvider);
    }
    if (_selectedCloudProvider.isNotEmpty) {
      _cloudModelController.text = _providerModel(_selectedCloudProvider);
    }
  }

  // ════════════════════════════════════════════════════════════════════
  // Data Loading
  // ════════════════════════════════════════════════════════════════════

  Future<void> _loadData() async {
    try {
      final api = ApiService();
      final results = await Future.wait([
        api.getInferenceConfig(),
        api.getLLMHealth(),
        api.getLLMProviders(),
      ]);

      final inference = results[0];
      final health = results[1];
      final providers = results[2];

      if (mounted) {
        setState(() {
          _mode = (inference['mode'] as String?) ?? 'AUTO';
          _currentRoute = (inference['current_route'] as String?) ?? 'LOCAL';
          _cloudHealthy = (inference['cloud_healthy'] as bool?) ?? true;
          _lastCloudFailure = inference['last_cloud_failure'] as String?;
          _lastCloudFailureAt = inference['last_cloud_failure_at'] as String?;

          _healthProviders =
              (health['providers'] as Map<String, dynamic>?) ?? {};
          _activeProvider = (providers['active_provider'] as String?) ?? '';

          final chain = providers['fallback_chain'];
          if (chain is List) {
            _fallbackChain = chain.map((e) => e.toString()).toList();
          }

          final cfgMap = providers['providers'];
          if (cfgMap is Map<String, dynamic>) {
            _configProviders = cfgMap;
            // Initialize edit states for any new providers
            for (final entry in cfgMap.entries) {
              if (!_editStates.containsKey(entry.key)) {
                _editStates[entry.key] = _ProviderEditState.fromConfig(
                  entry.value as Map<String, dynamic>,
                );
              }
            }
          }

          _syncRouteSelections();

          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _setMode(String mode) async {
    setState(() => _mode = mode);
    try {
      final api = ApiService();
      await api.updateInferenceMode(mode);
      await _loadData();
    } catch (_) {}
  }

  // ════════════════════════════════════════════════════════════════════
  // Build
  // ════════════════════════════════════════════════════════════════════

  @override
  Widget build(BuildContext context) {
    return Container(
      color: ThroneTheme.void1,
      child: Column(
        children: [
          _header(),
          const Divider(height: 1, color: ThroneTheme.void3),
          Expanded(
            child: _loading
                ? const Center(
                    child: CircularProgressIndicator(
                      color: ThroneTheme.bifrostAuto,
                    ),
                  )
                : ListView(
                    padding: const EdgeInsets.all(14),
                    children: [
                      if (!_cloudHealthy && !_bannerDismissed) _failureBanner(),
                      _routeVisualization(),
                      const SizedBox(height: 16),
                      _modeSwitcher(),
                      const SizedBox(height: 14),
                      _routeProviderSection(),
                      const SizedBox(height: 20),
                      _fallbackChainSection(),
                      const SizedBox(height: 20),
                      _providerCardsSection(),
                    ],
                  ),
          ),
        ],
      ),
    );
  }

  // ════════════════════════════════════════════════════════════════════
  // Header
  // ════════════════════════════════════════════════════════════════════

  Widget _header() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Row(
        children: [
          Icon(Icons.blur_on, size: 16, color: ThroneTheme.bifrostBridge),
          const SizedBox(width: 8),
          Text(
            'BIFROST',
            style: TextStyle(
              color: ThroneTheme.bifrostBridge,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.5,
            ),
          ),
          const Spacer(),
          _warmButton(),
          const SizedBox(width: 12),
          InkWell(
            onTap: _loadData,
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

  Widget _warmButton() {
    return InkWell(
      onTap: () async {
        try {
          await ApiService().warmLocalProvider();
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: const Text('Local provider warm-up triggered'),
                backgroundColor: ThroneTheme.void3,
                duration: const Duration(seconds: 2),
              ),
            );
          }
        } catch (_) {}
      },
      borderRadius: BorderRadius.circular(4),
      child: Tooltip(
        message: 'Warm local provider',
        child: Icon(
          Icons.whatshot,
          size: 14,
          color: ThroneTheme.warning.withValues(alpha: 0.7),
        ),
      ),
    );
  }

  // ════════════════════════════════════════════════════════════════════
  // Failure Banner
  // ════════════════════════════════════════════════════════════════════

  Widget _failureBanner() {
    final timestamp = _lastCloudFailureAt ?? '';
    final reason = _lastCloudFailure ?? 'Unknown error';
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: ThroneTheme.warning.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: ThroneTheme.warning.withValues(alpha: 0.4),
          ),
        ),
        child: Row(
          children: [
            Icon(
              Icons.warning_amber_rounded,
              size: 16,
              color: ThroneTheme.warning,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Cloud unavailable \u2014 routed to local',
                    style: TextStyle(
                      color: ThroneTheme.warning,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  if (timestamp.isNotEmpty || reason.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Text(
                        '${reason.isNotEmpty ? reason : ''}'
                        '${timestamp.isNotEmpty ? ' \u2014 $timestamp' : ''}',
                        style: TextStyle(
                          color: ThroneTheme.warning.withValues(alpha: 0.7),
                          fontSize: 9,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(width: 4),
            InkWell(
              onTap: () => setState(() => _bannerDismissed = true),
              borderRadius: BorderRadius.circular(4),
              child: Icon(
                Icons.close,
                size: 14,
                color: ThroneTheme.warning.withValues(alpha: 0.6),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ════════════════════════════════════════════════════════════════════
  // Route Visualization
  // ════════════════════════════════════════════════════════════════════

  Widget _routeVisualization() {
    final isLocal = _currentRoute == 'LOCAL';
    final routeColor =
        isLocal ? ThroneTheme.bifrostLocal : ThroneTheme.bifrostCloud;
    final routeLabel = isLocal ? '\u2B22 LOCAL' : '\u2601 CLOUD';
    final routeIcon = isLocal ? Icons.computer : Icons.cloud;

    return AnimatedBuilder(
      animation: _pulseController,
      builder: (context, child) {
        final glow = _pulseController.value * 0.4 + 0.6;
        return Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                routeColor.withValues(alpha: 0.15 * glow),
                ThroneTheme.void2,
              ],
            ),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: routeColor.withValues(alpha: 0.4 * glow),
              width: 1.5,
            ),
            boxShadow: [
              BoxShadow(
                color: routeColor.withValues(alpha: 0.1 * glow),
                blurRadius: 20,
                spreadRadius: 2,
              ),
            ],
          ),
          child: Column(
            children: [
              Text(
                'ACTIVE ROUTE',
                style: TextStyle(
                  color: ThroneTheme.textMuted,
                  fontSize: 9,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 2,
                ),
              ),
              const SizedBox(height: 10),
              Icon(routeIcon, size: 32, color: routeColor),
              const SizedBox(height: 6),
              Text(
                routeLabel,
                style: TextStyle(
                  color: routeColor,
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1,
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  // ════════════════════════════════════════════════════════════════════
  // Mode Switcher
  // ════════════════════════════════════════════════════════════════════

  Widget _modeSwitcher() {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: ThroneTheme.void2,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: ThroneTheme.void3),
      ),
      child: Row(
        children: [
          _modeButton('LOCAL', ThroneTheme.bifrostLocal, Icons.computer),
          _modeButton('AUTO', ThroneTheme.bifrostAuto, Icons.auto_awesome),
          _modeButton('CLOUD', ThroneTheme.bifrostCloud, Icons.cloud),
        ],
      ),
    );
  }

  Widget _routeProviderSection() {
    final localProviders = _providersByType({'ollama', 'lm_studio'});
    final cloudProviders = _providersByType({'openrouter', 'openai'});

    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: ThroneTheme.void2,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: ThroneTheme.void3),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _fieldLabel('Route Provider and Model'),
          const SizedBox(height: 8),
          _providerModelPicker(
            label: 'Local',
            providers: localProviders,
            selected: _selectedLocalProvider,
            onProviderChanged: (v) {
              setState(() {
                _selectedLocalProvider = v;
                _localModelController.text = _providerModel(v);
              });
            },
            modelController: _localModelController,
            emptyText: 'No local providers configured',
          ),
          const SizedBox(height: 10),
          _providerModelPicker(
            label: 'Remote',
            providers: cloudProviders,
            selected: _selectedCloudProvider,
            onProviderChanged: (v) {
              setState(() {
                _selectedCloudProvider = v;
                _cloudModelController.text = _providerModel(v);
              });
            },
            modelController: _cloudModelController,
            emptyText: 'No remote providers configured',
          ),
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            child: _actionButton(
              label: 'Apply Route Preferences',
              icon: Icons.route,
              color: ThroneTheme.accent,
              loading: false,
              onTap: _saveRoutePreferences,
            ),
          ),
        ],
      ),
    );
  }

  Widget _providerModelPicker({
    required String label,
    required List<String> providers,
    required String selected,
    required ValueChanged<String> onProviderChanged,
    required TextEditingController modelController,
    required String emptyText,
  }) {
    final hasItems = providers.isNotEmpty;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _fieldLabel(label),
        const SizedBox(height: 4),
        if (!hasItems)
          Text(
            emptyText,
            style: const TextStyle(
              color: ThroneTheme.textMuted,
              fontSize: 11,
            ),
          )
        else
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10),
            decoration: BoxDecoration(
              color: ThroneTheme.void1,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: ThroneTheme.void3),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: selected.isNotEmpty ? selected : providers.first,
                isExpanded: true,
                dropdownColor: ThroneTheme.void2,
                style: const TextStyle(
                  color: ThroneTheme.textPrimary,
                  fontSize: 12,
                ),
                iconEnabledColor: ThroneTheme.textMuted,
                items: providers
                    .map(
                      (p) => DropdownMenuItem(
                        value: p,
                        child: Text(p),
                      ),
                    )
                    .toList(),
                onChanged: (v) {
                  if (v != null) onProviderChanged(v);
                },
              ),
            ),
          ),
        const SizedBox(height: 6),
        _configTextField(modelController, 'model-name'),
      ],
    );
  }

  Future<void> _saveRoutePreferences() async {
    if (_selectedLocalProvider.isEmpty && _selectedCloudProvider.isEmpty) return;

    if (_selectedLocalProvider.isNotEmpty) {
      final es = _editStates[_selectedLocalProvider] ??
          _ProviderEditState.fromConfig(
            (_configProviders[_selectedLocalProvider] as Map<String, dynamic>?) ?? {},
          );
      _editStates[_selectedLocalProvider] = es;
      es.modelController.text = _localModelController.text.trim();
    }

    if (_selectedCloudProvider.isNotEmpty) {
      final es = _editStates[_selectedCloudProvider] ??
          _ProviderEditState.fromConfig(
            (_configProviders[_selectedCloudProvider] as Map<String, dynamic>?) ?? {},
          );
      _editStates[_selectedCloudProvider] = es;
      es.modelController.text = _cloudModelController.text.trim();
    }

    final ordered = <String>[];
    if (_selectedCloudProvider.isNotEmpty) ordered.add(_selectedCloudProvider);
    if (_selectedLocalProvider.isNotEmpty) ordered.add(_selectedLocalProvider);
    ordered.addAll(_fallbackChain);
    ordered.addAll(_configProviders.keys);

    final seen = <String>{};
    _fallbackChain = ordered.where((n) => seen.add(n)).toList();

    if (_mode == 'LOCAL' && _selectedLocalProvider.isNotEmpty) {
      _activeProvider = _selectedLocalProvider;
    } else if (_mode == 'CLOUD' && _selectedCloudProvider.isNotEmpty) {
      _activeProvider = _selectedCloudProvider;
    } else if (_selectedCloudProvider.isNotEmpty) {
      _activeProvider = _selectedCloudProvider;
    }

    await _saveCurrentConfig();
  }

  Widget _modeButton(String mode, Color color, IconData icon) {
    final isActive = _mode == mode;
    return Expanded(
      child: GestureDetector(
        onTap: () => _setMode(mode),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeInOut,
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            gradient: isActive
                ? LinearGradient(
                    colors: [
                      color.withValues(alpha: 0.3),
                      color.withValues(alpha: 0.1),
                    ],
                  )
                : null,
            borderRadius: BorderRadius.circular(8),
            border: isActive
                ? Border.all(color: color.withValues(alpha: 0.5))
                : null,
          ),
          child: Column(
            children: [
              Icon(
                icon,
                size: 16,
                color: isActive ? color : ThroneTheme.textMuted,
              ),
              const SizedBox(height: 4),
              Text(
                mode,
                style: TextStyle(
                  color: isActive ? color : ThroneTheme.textMuted,
                  fontSize: 9,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ════════════════════════════════════════════════════════════════════
  // Fallback Chain
  // ════════════════════════════════════════════════════════════════════

  Widget _fallbackChainSection() {
    if (_fallbackChain.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 2, bottom: 8),
          child: Row(
            children: [
              Icon(
                Icons.swap_vert,
                size: 12,
                color: ThroneTheme.textMuted,
              ),
              const SizedBox(width: 6),
              Text(
                'FALLBACK CHAIN',
                style: TextStyle(
                  color: ThroneTheme.textMuted,
                  fontSize: 9,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.5,
                ),
              ),
              const Spacer(),
              Text(
                'Drag to reorder, bin to remove',
                style: TextStyle(
                  color: ThroneTheme.textMuted.withValues(alpha: 0.75),
                  fontSize: 9,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
        Container(
          decoration: BoxDecoration(
            color: ThroneTheme.void2,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: ThroneTheme.void3),
          ),
          clipBehavior: Clip.antiAlias,
          child: ReorderableListView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            buildDefaultDragHandles: false,
            itemCount: _fallbackChain.length,
            onReorder: _onReorderChain,
            proxyDecorator: (child, index, animation) {
              return AnimatedBuilder(
                animation: animation,
                builder: (context, child) {
                  final elevate = Tween<double>(begin: 0, end: 4)
                      .animate(animation)
                      .value;
                  return Material(
                    color: ThroneTheme.void2,
                    elevation: elevate,
                    shadowColor: ThroneTheme.accent.withValues(alpha: 0.3),
                    borderRadius: BorderRadius.circular(0),
                    child: child,
                  );
                },
                child: child,
              );
            },
            itemBuilder: (context, index) {
              final name = _fallbackChain[index];
              final isPrimary = index == 0;
              final health = _healthProviders[name] as Map<String, dynamic>?;
              final online = (health?['online'] as bool?) ?? false;

              return Container(
                key: ValueKey(name),
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                decoration: BoxDecoration(
                  border: index < _fallbackChain.length - 1
                      ? Border(
                          bottom: BorderSide(
                            color: ThroneTheme.void3.withValues(alpha: 0.5),
                          ),
                        )
                      : null,
                ),
                child: Row(
                  children: [
                    ReorderableDragStartListener(
                      index: index,
                      child: Icon(
                        Icons.drag_handle,
                        size: 16,
                        color: ThroneTheme.textMuted.withValues(alpha: 0.5),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Container(
                      width: 18,
                      height: 18,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: isPrimary
                            ? ThroneTheme.accent.withValues(alpha: 0.2)
                            : ThroneTheme.void3.withValues(alpha: 0.5),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        '${index + 1}',
                        style: TextStyle(
                          color: isPrimary
                              ? ThroneTheme.accent
                              : ThroneTheme.textMuted,
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Text(
                      _providerIcon(
                        (health?['type'] as String?) ?? '',
                      ),
                      style: const TextStyle(fontSize: 14),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        name,
                        style: TextStyle(
                          color: isPrimary
                              ? ThroneTheme.textPrimary
                              : ThroneTheme.textSecondary,
                          fontSize: 11,
                          fontWeight:
                              isPrimary ? FontWeight.w600 : FontWeight.w400,
                        ),
                      ),
                    ),
                    if (isPrimary)
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 6,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: ThroneTheme.accent.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          'PRIMARY',
                          style: TextStyle(
                            color: ThroneTheme.accent,
                            fontSize: 8,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ),
                    const SizedBox(width: 8),
                    _healthDot(online),
                    const SizedBox(width: 8),
                    InkWell(
                      onTap: () => _removeFromFallbackChain(name),
                      borderRadius: BorderRadius.circular(4),
                      child: Icon(
                        Icons.delete_outline,
                        size: 16,
                        color: ThroneTheme.danger.withValues(alpha: 0.85),
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  void _onReorderChain(int oldIndex, int newIndex) {
    setState(() {
      if (newIndex > oldIndex) newIndex--;
      final item = _fallbackChain.removeAt(oldIndex);
      _fallbackChain.insert(newIndex, item);
    });
    // Persist reordered chain via config save
    _saveCurrentConfig();
  }

  Future<void> _removeFromFallbackChain(String providerName) async {
    if (!_fallbackChain.contains(providerName)) return;

    final previousChain = List<String>.from(_fallbackChain);
    final previousActive = _activeProvider;

    setState(() {
      _fallbackChain.remove(providerName);
      if (_activeProvider == providerName) {
        _activeProvider = _fallbackChain.isNotEmpty ? _fallbackChain.first : '';
      }
    });

    try {
      await _saveCurrentConfig();

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Removed $providerName from fallback chain'),
          backgroundColor: ThroneTheme.void3,
          action: SnackBarAction(
            label: 'UNDO',
            textColor: ThroneTheme.accentGlow,
            onPressed: () async {
              setState(() {
                _fallbackChain = previousChain;
                _activeProvider = previousActive;
              });
              await _saveCurrentConfig();
            },
          ),
          duration: const Duration(seconds: 4),
        ),
      );
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _fallbackChain = previousChain;
        _activeProvider = previousActive;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Failed to remove provider from chain')),
      );
    }
  }

  Future<void> _saveCurrentConfig() async {
    try {
      final config = <String, dynamic>{
        'active_provider': _activeProvider.isNotEmpty
            ? _activeProvider
            : (_fallbackChain.isNotEmpty ? _fallbackChain.first : ''),
        'fallback_chain': _fallbackChain,
        'providers': <String, dynamic>{},
      };

      for (final entry in _configProviders.entries) {
        final es = _editStates[entry.key];
        if (es != null) {
          config['providers'][entry.key] = es.toConfigMap();
        } else {
          config['providers'][entry.key] = entry.value;
        }
      }

      await ApiService().saveLLMConfig(config);
      await _loadData();
    } catch (_) {}
  }

  // ════════════════════════════════════════════════════════════════════
  // Provider Cards
  // ════════════════════════════════════════════════════════════════════

  Widget _providerCardsSection() {
    // Build cards in fallback chain order, then append any not in chain
    final ordered = <String>[..._fallbackChain];
    for (final key in _healthProviders.keys) {
      if (!ordered.contains(key)) ordered.add(key);
    }
    for (final key in _configProviders.keys) {
      if (!ordered.contains(key)) ordered.add(key);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 2, bottom: 8),
          child: Row(
            children: [
              Icon(Icons.dns, size: 12, color: ThroneTheme.textMuted),
              const SizedBox(width: 6),
              Text(
                'PROVIDERS',
                style: TextStyle(
                  color: ThroneTheme.textMuted,
                  fontSize: 9,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.5,
                ),
              ),
            ],
          ),
        ),
        ...ordered.map(_providerCard),
      ],
    );
  }

  Widget _providerCard(String name) {
    final health =
        (_healthProviders[name] as Map<String, dynamic>?) ?? <String, dynamic>{};
    final online = (health['online'] as bool?) ?? false;
    final type = (health['type'] as String?) ?? '';
    final model = (health['model'] as String?) ?? '';
    final isExpanded = _expandedProviders.contains(name);

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeInOut,
        decoration: BoxDecoration(
          color: ThroneTheme.void2,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isExpanded
                ? ThroneTheme.accent.withValues(alpha: 0.4)
                : online
                    ? ThroneTheme.statusOnline.withValues(alpha: 0.3)
                    : ThroneTheme.void3,
          ),
        ),
        child: Column(
          children: [
            // Collapsed header — always visible
            InkWell(
              onTap: () {
                setState(() {
                  if (isExpanded) {
                    _expandedProviders.remove(name);
                  } else {
                    _expandedProviders.add(name);
                  }
                });
              },
              borderRadius: BorderRadius.circular(8),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Row(
                  children: [
                    Text(
                      _providerIcon(type),
                      style: const TextStyle(fontSize: 20),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            name,
                            style: const TextStyle(
                              color: ThroneTheme.textPrimary,
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          if (model.isNotEmpty)
                            Padding(
                              padding: const EdgeInsets.only(top: 2),
                              child: Text(
                                model,
                                style: const TextStyle(
                                  color: ThroneTheme.textMuted,
                                  fontSize: 10,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                        ],
                      ),
                    ),
                    AnimatedBuilder(
                      animation: _pulseController,
                      builder: (context, _) {
                        final pulse =
                            online ? _pulseController.value * 0.5 + 0.5 : 1.0;
                        return _healthDotWithGlow(online, pulse);
                      },
                    ),
                    const SizedBox(width: 8),
                    AnimatedRotation(
                      turns: isExpanded ? 0.5 : 0,
                      duration: const Duration(milliseconds: 250),
                      child: Icon(
                        Icons.expand_more,
                        size: 18,
                        color: ThroneTheme.textMuted,
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // Expanded config panel
            if (isExpanded) _providerConfigPanel(name),
          ],
        ),
      ),
    );
  }

  Widget _providerConfigPanel(String name) {
    final editState = _editStates[name] ??
        _ProviderEditState.fromConfig(
          (_configProviders[name] as Map<String, dynamic>?) ?? {},
        );
    // Ensure it is stored
    _editStates[name] = editState;

    return Container(
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Divider(height: 1, color: ThroneTheme.void3),
          const SizedBox(height: 12),

          // Provider type dropdown
          _fieldLabel('Type'),
          const SizedBox(height: 4),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10),
            decoration: BoxDecoration(
              color: ThroneTheme.void1,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: ThroneTheme.void3),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: editState.type,
                isExpanded: true,
                dropdownColor: ThroneTheme.void2,
                style: const TextStyle(
                  color: ThroneTheme.textPrimary,
                  fontSize: 12,
                ),
                iconEnabledColor: ThroneTheme.textMuted,
                items: const [
                  DropdownMenuItem(value: 'ollama', child: Text('Ollama')),
                  DropdownMenuItem(value: 'lm_studio', child: Text('LM Studio')),
                  DropdownMenuItem(
                    value: 'openrouter',
                    child: Text('OpenRouter'),
                  ),
                  DropdownMenuItem(value: 'openai', child: Text('OpenAI')),
                ],
                onChanged: (v) {
                  if (v != null) setState(() => editState.type = v);
                },
              ),
            ),
          ),

          const SizedBox(height: 10),

          // Endpoint
          _fieldLabel('Endpoint'),
          const SizedBox(height: 4),
          _configTextField(editState.endpointController, 'http://...'),

          const SizedBox(height: 10),

          // Model
          _fieldLabel('Model'),
          const SizedBox(height: 4),
          _configTextField(editState.modelController, 'model-name'),

          const SizedBox(height: 10),

          // API Key (obscured with reveal)
          _fieldLabel('API Key'),
          const SizedBox(height: 4),
          _apiKeyField(editState),

          const SizedBox(height: 10),

          // Max tokens, temperature, timeout in a row
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _fieldLabel('Max Tokens'),
                    const SizedBox(height: 4),
                    _configTextField(
                      editState.maxTokensController,
                      '2048',
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _fieldLabel('Temperature'),
                    const SizedBox(height: 4),
                    _configTextField(
                      editState.temperatureController,
                      '0.7',
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _fieldLabel('Timeout'),
                    const SizedBox(height: 4),
                    _configTextField(
                      editState.timeoutController,
                      '30',
                    ),
                  ],
                ),
              ),
            ],
          ),

          const SizedBox(height: 14),

          // Test buttons row
          Row(
            children: [
              Expanded(
                child: _actionButton(
                  label: 'Test Connection',
                  icon: Icons.lan,
                  color: ThroneTheme.bifrostLocal,
                  loading: editState.testingConnection,
                  onTap: () => _testConnection(name, editState),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _actionButton(
                  label: 'Test Reply',
                  icon: Icons.chat_bubble_outline,
                  color: ThroneTheme.bifrostCloud,
                  loading: editState.testingReply,
                  onTap: () => _testReply(name, editState),
                ),
              ),
            ],
          ),

          // Test result area
          if (editState.testResult != null)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: _testResultWidget(editState.testResult!),
            ),

          const SizedBox(height: 12),

          // Save button
          SizedBox(
            width: double.infinity,
            child: _actionButton(
              label: 'Save Provider Config',
              icon: Icons.save,
              color: ThroneTheme.accent,
              loading: editState.saving,
              onTap: () => _saveProvider(name, editState),
            ),
          ),
        ],
      ),
    );
  }

  // ════════════════════════════════════════════════════════════════════
  // Provider Actions
  // ════════════════════════════════════════════════════════════════════

  Future<void> _testConnection(
    String name,
    _ProviderEditState editState,
  ) async {
    setState(() {
      editState.testingConnection = true;
      editState.testResult = null;
    });
    try {
      final result = await ApiService().testProviderHealth(name);
      if (mounted) {
        setState(() {
          editState.testingConnection = false;
          final online = result['online'] as bool? ?? false;
          editState.testResult = _TestResult(
            success: online,
            message: online
                ? 'Connection OK \u2014 ${result['model'] ?? name}'
                : 'Connection failed',
          );
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          editState.testingConnection = false;
          editState.testResult = _TestResult(
            success: false,
            message: 'Error: $e',
          );
        });
      }
    }
  }

  Future<void> _testReply(
    String name,
    _ProviderEditState editState,
  ) async {
    setState(() {
      editState.testingReply = true;
      editState.testResult = null;
    });
    try {
      final result = await ApiService().testProviderReply(name);
      if (mounted) {
        setState(() {
          editState.testingReply = false;
          final success = result['success'] as bool? ?? false;
          if (success) {
            final response = result['response'] as String? ?? '';
            final model = result['model'] as String? ?? '';
            final tokens = result['tokens_used'];
            editState.testResult = _TestResult(
              success: true,
              message: 'Model: $model'
                  '${tokens != null ? ' | Tokens: $tokens' : ''}'
                  '\n$response',
            );
          } else {
            editState.testResult = _TestResult(
              success: false,
              message: result['error'] as String? ?? 'Unknown error',
            );
          }
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          editState.testingReply = false;
          editState.testResult = _TestResult(
            success: false,
            message: 'Error: $e',
          );
        });
      }
    }
  }

  Future<void> _saveProvider(
    String name,
    _ProviderEditState editState,
  ) async {
    setState(() => editState.saving = true);
    try {
      await _saveCurrentConfig();
      if (mounted) {
        setState(() {
          editState.saving = false;
          editState.testResult = _TestResult(
            success: true,
            message: 'Configuration saved',
          );
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          editState.saving = false;
          editState.testResult = _TestResult(
            success: false,
            message: 'Save failed: $e',
          );
        });
      }
    }
  }

  // ════════════════════════════════════════════════════════════════════
  // Shared Widgets
  // ════════════════════════════════════════════════════════════════════

  Widget _fieldLabel(String label) {
    return Text(
      label.toUpperCase(),
      style: TextStyle(
        color: ThroneTheme.textMuted,
        fontSize: 9,
        fontWeight: FontWeight.w600,
        letterSpacing: 1,
      ),
    );
  }

  Widget _configTextField(TextEditingController controller, String hint) {
    return SizedBox(
      height: 36,
      child: TextField(
        controller: controller,
        style: const TextStyle(
          color: ThroneTheme.textPrimary,
          fontSize: 12,
        ),
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: TextStyle(
            color: ThroneTheme.textMuted.withValues(alpha: 0.5),
            fontSize: 12,
          ),
          filled: true,
          fillColor: ThroneTheme.void1,
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 10,
            vertical: 8,
          ),
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
            borderSide: BorderSide(
              color: ThroneTheme.accent.withValues(alpha: 0.6),
            ),
          ),
        ),
      ),
    );
  }

  Widget _apiKeyField(_ProviderEditState editState) {
    return SizedBox(
      height: 36,
      child: TextField(
        controller: editState.apiKeyController,
        obscureText: !editState.apiKeyVisible,
        style: const TextStyle(
          color: ThroneTheme.textPrimary,
          fontSize: 12,
        ),
        decoration: InputDecoration(
          hintText: 'sk-...',
          hintStyle: TextStyle(
            color: ThroneTheme.textMuted.withValues(alpha: 0.5),
            fontSize: 12,
          ),
          filled: true,
          fillColor: ThroneTheme.void1,
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 10,
            vertical: 8,
          ),
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
            borderSide: BorderSide(
              color: ThroneTheme.accent.withValues(alpha: 0.6),
            ),
          ),
          suffixIcon: InkWell(
            onTap: () {
              setState(() => editState.apiKeyVisible = !editState.apiKeyVisible);
            },
            child: Icon(
              editState.apiKeyVisible
                  ? Icons.visibility_off
                  : Icons.visibility,
              size: 16,
              color: ThroneTheme.textMuted,
            ),
          ),
        ),
      ),
    );
  }

  Widget _actionButton({
    required String label,
    required IconData icon,
    required Color color,
    required bool loading,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: loading ? null : onTap,
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 8),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: color.withValues(alpha: 0.3)),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (loading)
              SizedBox(
                width: 12,
                height: 12,
                child: CircularProgressIndicator(
                  strokeWidth: 1.5,
                  color: color,
                ),
              )
            else
              Icon(icon, size: 13, color: color),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                color: color,
                fontSize: 10,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _testResultWidget(_TestResult result) {
    final color =
        result.success ? ThroneTheme.statusOnline : ThroneTheme.danger;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.25)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            result.success ? Icons.check_circle : Icons.error,
            size: 14,
            color: color,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              result.message,
              style: TextStyle(
                color: color.withValues(alpha: 0.9),
                fontSize: 10,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _healthDot(bool online) {
    return Container(
      width: 8,
      height: 8,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: online
            ? ThroneTheme.statusOnline
            : ThroneTheme.danger.withValues(alpha: 0.6),
      ),
    );
  }

  Widget _healthDotWithGlow(bool online, double pulse) {
    return Container(
      width: 10,
      height: 10,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: online
            ? ThroneTheme.statusOnline.withValues(alpha: pulse)
            : ThroneTheme.danger.withValues(alpha: 0.6),
        boxShadow: online
            ? [
                BoxShadow(
                  color: ThroneTheme.statusOnline.withValues(
                    alpha: 0.3 * pulse,
                  ),
                  blurRadius: 6,
                  spreadRadius: 1,
                ),
              ]
            : [],
      ),
    );
  }

  String _providerIcon(String type) {
    return switch (type) {
      'ollama' => '\uD83E\uDD99',
      'lm_studio' => '\uD83E\uDDE0',
      'openrouter' => '\u2601\uFE0F',
      'openai' => '\uD83E\uDD16',
      _ => '\u2753',
    };
  }
}

// ════════════════════════════════════════════════════════════════════
// Supporting Data Classes
// ════════════════════════════════════════════════════════════════════

/// Mutable edit state for a single provider's config panel.
class _ProviderEditState {
  String type;
  final TextEditingController endpointController;
  final TextEditingController modelController;
  final TextEditingController apiKeyController;
  final TextEditingController maxTokensController;
  final TextEditingController temperatureController;
  final TextEditingController timeoutController;

  bool apiKeyVisible = false;
  bool testingConnection = false;
  bool testingReply = false;
  bool saving = false;
  _TestResult? testResult;

  _ProviderEditState({
    required this.type,
    required this.endpointController,
    required this.modelController,
    required this.apiKeyController,
    required this.maxTokensController,
    required this.temperatureController,
    required this.timeoutController,
  });

  factory _ProviderEditState.fromConfig(Map<String, dynamic> config) {
    return _ProviderEditState(
      type: (config['type'] as String?) ?? 'lm_studio',
      endpointController: TextEditingController(
        text: (config['endpoint'] as String?) ?? '',
      ),
      modelController: TextEditingController(
        text: (config['model'] as String?) ?? '',
      ),
      apiKeyController: TextEditingController(
        text: (config['api_key'] as String?) ?? '',
      ),
      maxTokensController: TextEditingController(
        text: '${config['max_tokens'] ?? ''}',
      ),
      temperatureController: TextEditingController(
        text: '${config['temperature'] ?? ''}',
      ),
      timeoutController: TextEditingController(
        text: '${config['timeout'] ?? ''}',
      ),
    );
  }

  Map<String, dynamic> toConfigMap() {
    final map = <String, dynamic>{
      'type': type,
      'endpoint': endpointController.text,
      'model': modelController.text,
    };
    if (apiKeyController.text.isNotEmpty) {
      map['api_key'] = apiKeyController.text;
    }
    final maxTokens = int.tryParse(maxTokensController.text);
    if (maxTokens != null) map['max_tokens'] = maxTokens;
    final temp = double.tryParse(temperatureController.text);
    if (temp != null) map['temperature'] = temp;
    final timeout = int.tryParse(timeoutController.text);
    if (timeout != null) map['timeout'] = timeout;
    return map;
  }

  void dispose() {
    endpointController.dispose();
    modelController.dispose();
    apiKeyController.dispose();
    maxTokensController.dispose();
    temperatureController.dispose();
    timeoutController.dispose();
  }
}

/// Result from a test connection or test reply action.
class _TestResult {
  final bool success;
  final String message;
  const _TestResult({required this.success, required this.message});
}
