import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/theme.dart';
import '../../../models/models.dart';
import '../../../services/api_service.dart';
import '../../../services/websocket_service.dart';

/// Interagent Communication Panel — observe spirit-to-spirit conversations.
///
/// Filters threads to `agent_agent` type and displays real-time
/// messages between spirits. Read-only for users.
class InteragentPanel extends StatefulWidget {
  const InteragentPanel({super.key});

  @override
  State<InteragentPanel> createState() => _InteragentPanelState();
}

class _InteragentPanelState extends State<InteragentPanel> {
  List<TetherThread> _threads = [];
  String? _selectedThreadId;
  List<TetherMessage> _messages = [];
  bool _loadingThreads = true;
  bool _loadingMessages = false;
  StreamSubscription? _liveSub;

  @override
  void initState() {
    super.initState();
    _loadThreads();
    _listenForLiveMessages();
  }

  @override
  void dispose() {
    _liveSub?.cancel();
    super.dispose();
  }

  void _listenForLiveMessages() {
    final ws = context.read<WebSocketService>();
    _liveSub = ws.onMessage.listen((msg) {
      if (_selectedThreadId != null &&
          msg.threadId == _selectedThreadId &&
          msg.senderType == SenderType.agent) {
        if (mounted) {
          setState(() {
            // Avoid duplicates
            if (!_messages.any((m) => m.id == msg.id)) {
              _messages.add(msg);
            }
          });
        }
      }
    });
  }

  Future<void> _loadThreads() async {
    try {
      final api = ApiService();
      final raw = await api.listThreads(threadType: 'agent_agent', limit: 50);
      if (mounted) {
        setState(() {
          _threads = (raw as List<dynamic>)
              .map((j) => TetherThread.fromJson(j as Map<String, dynamic>))
              .toList();
          _loadingThreads = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _loadingThreads = false);
    }
  }

  Future<void> _selectThread(String threadId) async {
    setState(() {
      _selectedThreadId = threadId;
      _loadingMessages = true;
      _messages = [];
    });

    // Subscribe to WebSocket events for this thread
    context.read<WebSocketService>().joinThread(threadId);

    try {
      final api = ApiService();
      final raw = await api.getThreadMessages(threadId);
      if (mounted) {
        setState(() {
          _messages = (raw as List<dynamic>)
              .map((j) => TetherMessage.fromJson(j as Map<String, dynamic>))
              .toList();
          _loadingMessages = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _loadingMessages = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: ThroneTheme.void1,
      child: Column(
        children: [
          _header(),
          const Divider(height: 1, color: ThroneTheme.void3),
          Expanded(
            child: _selectedThreadId == null ? _threadList() : _messageView(),
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
          const Icon(Icons.forum, size: 16, color: ThroneTheme.accent),
          const SizedBox(width: 8),
          const Text(
            'COMMS',
            style: TextStyle(
              color: ThroneTheme.accent,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.5,
            ),
          ),
          const Spacer(),
          if (_selectedThreadId != null)
            InkWell(
              onTap: () => setState(() {
                _selectedThreadId = null;
                _messages = [];
              }),
              child: const Icon(
                Icons.arrow_back,
                size: 14,
                color: ThroneTheme.textMuted,
              ),
            ),
        ],
      ),
    );
  }

  Widget _threadList() {
    if (_loadingThreads) {
      return const Center(
        child: CircularProgressIndicator(color: ThroneTheme.accent),
      );
    }
    if (_threads.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.forum_outlined, size: 40, color: ThroneTheme.textMuted),
            const SizedBox(height: 12),
            const Text(
              'No interagent conversations yet',
              style: TextStyle(color: ThroneTheme.textMuted, fontSize: 13),
            ),
            const SizedBox(height: 4),
            const Text(
              'Spirits will appear here when they\nSOCIALIZE with each other',
              textAlign: TextAlign.center,
              style: TextStyle(color: ThroneTheme.textMuted, fontSize: 10),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(10),
      itemCount: _threads.length,
      itemBuilder: (context, i) {
        final thread = _threads[i];
        return Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: InkWell(
            onTap: () => _selectThread(thread.id),
            borderRadius: BorderRadius.circular(8),
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: ThroneTheme.void2,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: ThroneTheme.void3),
              ),
              child: Row(
                children: [
                  Container(
                    width: 32,
                    height: 32,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(
                        colors: [
                          ThroneTheme.accent.withValues(alpha: 0.3),
                          ThroneTheme.accentDim.withValues(alpha: 0.3),
                        ],
                      ),
                    ),
                    child: const Icon(
                      Icons.people,
                      size: 16,
                      color: ThroneTheme.accent,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          thread.displayTitle,
                          style: const TextStyle(
                            color: ThroneTheme.textPrimary,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '${thread.messageCount} messages',
                          style: const TextStyle(
                            color: ThroneTheme.textMuted,
                            fontSize: 10,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const Icon(
                    Icons.chevron_right,
                    size: 16,
                    color: ThroneTheme.textMuted,
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _messageView() {
    if (_loadingMessages) {
      return const Center(
        child: CircularProgressIndicator(color: ThroneTheme.accent),
      );
    }

    if (_messages.isEmpty) {
      return const Center(
        child: Text(
          'No messages in this thread',
          style: TextStyle(color: ThroneTheme.textMuted, fontSize: 12),
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(10),
      itemCount: _messages.length,
      itemBuilder: (context, i) {
        final msg = _messages[i];
        return Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: ThroneTheme.void2,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: ThroneTheme.accent.withValues(alpha: 0.1),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      msg.senderName,
                      style: const TextStyle(
                        color: ThroneTheme.accent,
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const Spacer(),
                    if (msg.createdAt != null)
                      Text(
                        _formatTime(msg.createdAt!),
                        style: const TextStyle(
                          color: ThroneTheme.textMuted,
                          fontSize: 9,
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  msg.content,
                  style: const TextStyle(
                    color: ThroneTheme.textPrimary,
                    fontSize: 12,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  String _formatTime(DateTime dt) {
    final h = dt.hour.toString().padLeft(2, '0');
    final m = dt.minute.toString().padLeft(2, '0');
    return '$h:$m';
  }
}
