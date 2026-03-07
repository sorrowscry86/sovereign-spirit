import 'dart:async';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../../core/theme.dart';
import '../../../models/models.dart';
import '../../../services/api_service.dart';
import '../../../services/websocket_service.dart';

/// Center panel: thread list + thread timeline + compose bar.
///
/// This is the primary Tether UI surface (WS3 from the revamp plan).
class ThreadPanel extends StatefulWidget {
  final String? agentId;
  final String? activeThreadId;
  final ValueChanged<String> onThreadSelected;

  const ThreadPanel({
    super.key,
    this.agentId,
    this.activeThreadId,
    required this.onThreadSelected,
  });

  @override
  State<ThreadPanel> createState() => _ThreadPanelState();
}

class _ThreadPanelState extends State<ThreadPanel> {
  List<TetherThread> _threads = [];
  List<TetherMessage> _messages = [];
  bool _loadingThreads = false;
  bool _loadingMessages = false;
  final TextEditingController _composeCtrl = TextEditingController();
  final ScrollController _scrollCtrl = ScrollController();
  StreamSubscription<TetherMessage>? _msgSub;
  StreamSubscription<ReplyChainEvent>? _chainSub;
  final List<ReplyChainEvent> _chainEvents = [];

  @override
  void initState() {
    super.initState();
    final ws = context.read<WebSocketService>();
    _msgSub = ws.onMessage.listen(_onLiveMessage);
    _chainSub = ws.onReplyChain.listen(_onReplyChainEvent);
  }

  @override
  void didUpdateWidget(ThreadPanel old) {
    super.didUpdateWidget(old);
    if (widget.agentId != old.agentId) {
      _loadThreads();
    }
    if (widget.activeThreadId != old.activeThreadId &&
        widget.activeThreadId != null) {
      _loadMessages(widget.activeThreadId!);
    }
  }

  @override
  void dispose() {
    _msgSub?.cancel();
    _chainSub?.cancel();
    _composeCtrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadThreads() async {
    if (widget.agentId == null) return;
    setState(() => _loadingThreads = true);
    try {
      final threads = await context.read<ApiService>().listThreads(
        agentId: widget.agentId,
      );
      setState(() {
        _threads = threads;
        _loadingThreads = false;
      });
    } catch (e) {
      setState(() => _loadingThreads = false);
      debugPrint('[ThreadPanel] Load threads error: $e');
    }
  }

  Future<void> _loadMessages(String threadId) async {
    setState(() => _loadingMessages = true);
    try {
      final messages = await context.read<ApiService>().getThreadMessages(
        threadId,
      );
      setState(() {
        _messages = messages;
        _chainEvents.removeWhere((e) => e.threadId != threadId);
        _loadingMessages = false;
      });
      _scrollToBottom();
    } catch (e) {
      setState(() => _loadingMessages = false);
      debugPrint('[ThreadPanel] Load messages error: $e');
    }
  }

  void _onLiveMessage(TetherMessage msg) {
    if (msg.threadId == widget.activeThreadId) {
      setState(() {
        if (msg.isFromUser) {
          // Find matching optimistic message and replace it
          final existingIdx = _messages.indexWhere(
            (m) => m.id.startsWith('local-') && m.content == msg.content,
          );
          if (existingIdx != -1) {
            _messages[existingIdx] = msg;
            return;
          }
        }
        _messages.add(msg);
      });
      _scrollToBottom();

      // Auto mark-read for incoming messages in the active thread
      if (!msg.isFromUser) {
        context.read<WebSocketService>().markRead([msg.id]);
      }
    }
    // Refresh thread list for updated last_activity_at
    _loadThreads();
  }

  void _onReplyChainEvent(ReplyChainEvent event) {
    if (event.threadId != widget.activeThreadId) return;
    if (!mounted) return;
    setState(() {
      final exists = _chainEvents.any((e) => e.eventId == event.eventId);
      if (!exists) {
        _chainEvents.add(event);
      }
      if (_chainEvents.length > 60) {
        _chainEvents.removeRange(0, _chainEvents.length - 60);
      }
    });
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _sendMessage() {
    final text = _composeCtrl.text.trim();
    if (text.isEmpty ||
        widget.activeThreadId == null ||
        widget.agentId == null) {
      return;
    }

    // Send via WebSocket for real-time delivery
    context.read<WebSocketService>().sendTetherMessage(
      threadId: widget.activeThreadId!,
      agentId: widget.agentId!,
      content: text,
    );

    // Optimistic append
    setState(() {
      _messages.add(
        TetherMessage(
          id: 'local-${DateTime.now().millisecondsSinceEpoch}',
          threadId: widget.activeThreadId!,
          senderName: 'User',
          senderType: SenderType.user,
          content: text,
          status: MessageStatus.pending,
          createdAt: DateTime.now(),
        ),
      );
    });

    _composeCtrl.clear();
    _scrollToBottom();
  }

  Future<void> _startNewThread() async {
    if (widget.agentId == null) return;
    try {
      final thread = await context.read<ApiService>().createThread(
        threadType: 'user_agent',
        subject: 'Conversation with ${widget.agentId}',
        agentIds: [widget.agentId!],
      );
      widget.onThreadSelected(thread.id);
      _loadThreads();
    } catch (e) {
      debugPrint('[ThreadPanel] Create thread error: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.agentId == null) {
      return _emptyState('Select a spirit to view threads');
    }

    return Column(
      children: [
        // ── Thread Tabs / Header ──
        _threadHeader(),
        const Divider(height: 1, color: ThroneTheme.void3),

        // ── Content Area ──
        Expanded(
          child: widget.activeThreadId == null
              ? _threadList()
              : _threadTimeline(),
        ),

        // ── Compose Bar ──
        if (widget.activeThreadId != null) _composeBar(),
      ],
    );
  }

  // ── Thread Header ──
  Widget _threadHeader() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      color: ThroneTheme.void1,
      child: Row(
        children: [
          if (widget.activeThreadId != null)
            IconButton(
              icon: const Icon(Icons.arrow_back_ios, size: 16),
              onPressed: () {
                widget.onThreadSelected('');
                setState(() => _messages.clear());
              },
              tooltip: 'Back to threads',
              color: ThroneTheme.textSecondary,
            ),
          const Icon(Icons.forum_outlined, size: 16, color: ThroneTheme.tether),
          const SizedBox(width: 8),
          Text(
            widget.activeThreadId != null
                ? 'Thread ${widget.activeThreadId!.substring(0, 8)}'
                : 'THREADS — ${widget.agentId?.toUpperCase() ?? ""}',
            style: const TextStyle(
              color: ThroneTheme.textSecondary,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.2,
            ),
          ),
          const Spacer(),
          if (widget.activeThreadId == null)
            IconButton(
              icon: const Icon(Icons.add_circle_outline, size: 20),
              onPressed: _startNewThread,
              tooltip: 'New thread',
              color: ThroneTheme.tether,
            ),
        ],
      ),
    );
  }

  // ── Thread List ──
  Widget _threadList() {
    if (_loadingThreads) {
      return const Center(
        child: CircularProgressIndicator(color: ThroneTheme.accent),
      );
    }
    if (_threads.isEmpty) {
      return _emptyState('No threads yet. Start a conversation.');
    }

    return ListView.builder(
      padding: const EdgeInsets.all(8),
      itemCount: _threads.length,
      itemBuilder: (context, i) {
        final thread = _threads[i];
        return _threadCard(thread);
      },
    );
  }

  Widget _threadCard(TetherThread thread) {
    final timeStr = thread.lastActivityAt != null
        ? DateFormat.jm().format(thread.lastActivityAt!.toLocal())
        : '';
    return InkWell(
      onTap: () => widget.onThreadSelected(thread.id),
      borderRadius: BorderRadius.circular(8),
      child: Container(
        margin: const EdgeInsets.only(bottom: 4),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: ThroneTheme.void2,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: ThroneTheme.void3, width: 0.5),
        ),
        child: Row(
          children: [
            Icon(
              _threadIcon(thread.threadType),
              size: 18,
              color: ThroneTheme.tether,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    thread.displayTitle,
                    style: const TextStyle(
                      color: ThroneTheme.textPrimary,
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '${thread.messageCount} messages • ${thread.threadType.value}',
                    style: const TextStyle(
                      color: ThroneTheme.textMuted,
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),
            Text(
              timeStr,
              style: const TextStyle(
                color: ThroneTheme.textMuted,
                fontSize: 11,
              ),
            ),
          ],
        ),
      ),
    );
  }

  IconData _threadIcon(ThreadType type) {
    switch (type) {
      case ThreadType.userAgent:
        return Icons.person_outline;
      case ThreadType.agentAgent:
        return Icons.smart_toy_outlined;
      case ThreadType.broadcast:
        return Icons.campaign_outlined;
      case ThreadType.godMode:
        return Icons.bolt;
    }
  }

  // ── Thread Timeline ──
  Widget _threadTimeline() {
    if (_loadingMessages) {
      return const Center(
        child: CircularProgressIndicator(color: ThroneTheme.accent),
      );
    }
    if (_messages.isEmpty) {
      return _emptyState('No messages yet. Send the first one.');
    }

    return Column(
      children: [
        if (_chainEvents.isNotEmpty) _chainBadgeRail(),
        Expanded(
          child: ListView.builder(
            controller: _scrollCtrl,
            padding: const EdgeInsets.all(16),
            itemCount: _messages.length,
            itemBuilder: (context, i) => _messageBubble(_messages[i]),
          ),
        ),
      ],
    );
  }

  Widget _chainBadgeRail() {
    final items = _chainEvents.reversed.take(8).toList();
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: const BoxDecoration(
        color: ThroneTheme.void1,
        border: Border(bottom: BorderSide(color: ThroneTheme.void3)),
      ),
      child: Wrap(
        spacing: 6,
        runSpacing: 6,
        children: items.map((event) {
          final chainLabel = event.chainId.isNotEmpty
              ? event.chainId.substring(0, event.chainId.length < 6 ? event.chainId.length : 6)
              : 'chain';
          return Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: _chainStatusColor(event.chainStatus).withValues(alpha: 0.18),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: _chainStatusColor(event.chainStatus).withValues(alpha: 0.4)),
            ),
            child: Text(
              '$chainLabel • s${event.chainStep} • ${event.chainStatus}',
              style: TextStyle(
                color: _chainStatusColor(event.chainStatus),
                fontSize: 10,
                fontWeight: FontWeight.w600,
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _messageBubble(TetherMessage msg) {
    final isUser = msg.isFromUser;
    final alignment = isUser
        ? CrossAxisAlignment.end
        : CrossAxisAlignment.start;
    final bgColor = isUser
        ? ThroneTheme.accent.withValues(alpha: 0.15)
        : ThroneTheme.void2;
    final borderColor = isUser
        ? ThroneTheme.accent.withValues(alpha: 0.3)
        : ThroneTheme.void3;
    final nameColor = isUser ? ThroneTheme.accent : ThroneTheme.tether;

    final timeStr = msg.createdAt != null
        ? DateFormat.jm().format(msg.createdAt!.toLocal())
        : '';

    final messageChainEvents = _chainEvents
        .where((e) => e.parentMessageId != null && e.parentMessageId == msg.id)
        .toList();

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: alignment,
        children: [
          // Sender + time
          Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: Row(
              mainAxisAlignment: isUser
                  ? MainAxisAlignment.end
                  : MainAxisAlignment.start,
              children: [
                Text(
                  msg.senderName,
                  style: TextStyle(
                    color: nameColor,
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  timeStr,
                  style: const TextStyle(
                    color: ThroneTheme.textMuted,
                    fontSize: 10,
                  ),
                ),
                const SizedBox(width: 8),
                _statusIcon(msg.status),
              ],
            ),
          ),
          if (messageChainEvents.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Wrap(
                spacing: 6,
                children: messageChainEvents.map((event) {
                  return Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: _chainStatusColor(event.chainStatus).withValues(alpha: 0.18),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      'step ${event.chainStep} • ${event.chainStatus}',
                      style: TextStyle(
                        color: _chainStatusColor(event.chainStatus),
                        fontSize: 9,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  );
                }).toList(),
              ),
            ),
          // Message body
          Container(
            constraints: BoxConstraints(
              maxWidth: MediaQuery.of(context).size.width * 0.5,
            ),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: bgColor,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: borderColor, width: 0.5),
            ),
            child: SelectableText(
              msg.content,
              style: const TextStyle(
                color: ThroneTheme.textPrimary,
                fontSize: 13,
                height: 1.5,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Color _chainStatusColor(String status) {
    switch (status) {
      case 'completed':
        return ThroneTheme.statusOnline;
      case 'failed':
      case 'cancelled':
        return ThroneTheme.danger;
      case 'waiting_approval':
        return ThroneTheme.accent;
      case 'running':
      case 'waiting_tool':
        return ThroneTheme.tether;
      default:
        return ThroneTheme.textMuted;
    }
  }

  Widget _statusIcon(MessageStatus status) {
    switch (status) {
      case MessageStatus.pending:
        return const Icon(
          Icons.schedule,
          size: 12,
          color: ThroneTheme.textMuted,
        );
      case MessageStatus.delivered:
        return const Icon(
          Icons.done,
          size: 12,
          color: ThroneTheme.statusDelivered,
        );
      case MessageStatus.read:
        return const Icon(
          Icons.done_all,
          size: 12,
          color: ThroneTheme.statusRead,
        );
      case MessageStatus.expired:
        return const Icon(Icons.timer_off, size: 12, color: ThroneTheme.danger);
    }
  }

  // ── Compose Bar ──
  Widget _composeBar() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: const BoxDecoration(
        color: ThroneTheme.void1,
        border: Border(top: BorderSide(color: ThroneTheme.void3)),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _composeCtrl,
              style: const TextStyle(
                color: ThroneTheme.textPrimary,
                fontSize: 14,
              ),
              decoration: const InputDecoration(
                hintText: 'Send a message...',
                isDense: true,
                contentPadding: EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 10,
                ),
              ),
              onSubmitted: (_) => _sendMessage(),
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            icon: const Icon(Icons.send, size: 20),
            onPressed: _sendMessage,
            color: ThroneTheme.tether,
            tooltip: 'Send',
          ),
        ],
      ),
    );
  }

  // ── Empty State ──
  Widget _emptyState(String text) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.chat_bubble_outline,
            size: 40,
            color: ThroneTheme.textMuted.withValues(alpha: 0.4),
          ),
          const SizedBox(height: 12),
          Text(
            text,
            style: const TextStyle(color: ThroneTheme.textMuted, fontSize: 13),
          ),
        ],
      ),
    );
  }
}
