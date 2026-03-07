import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../core/config.dart';
import '../models/models.dart';
import 'api_service.dart';

/// WebSocket service for real-time dashboard communication.
///
/// Handles:
///   - Auto-reconnect with backoff
///   - STATE_UPDATE broadcasts (agent state)
///   - TETHER_MESSAGE events (new messages in subscribed threads)
///   - MSG_STATUS_UPDATE events (read/delivered transitions)
///   - CMD_ACK responses
///   - GOD_MODE commands (sync, mood, stimuli)
///   - Tether commands (join, send, read)
class WebSocketService extends ChangeNotifier {
  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _subscription;
  Timer? _reconnectTimer;

  ApiService? apiService;

  bool _connected = false;
  int _reconnectAttempts = 0;

  // ── Observable State ──
  bool get isConnected => _connected;
  List<AgentState> agents = [];
  final List<TetherMessage> _liveMessages = [];
  List<TetherMessage> get liveMessages => List.unmodifiable(_liveMessages);

  // ── Event Streams ──
  final StreamController<TetherMessage> _messageStream =
      StreamController<TetherMessage>.broadcast();
  Stream<TetherMessage> get onMessage => _messageStream.stream;

  final StreamController<Map<String, dynamic>> _statusUpdateStream =
      StreamController<Map<String, dynamic>>.broadcast();
  Stream<Map<String, dynamic>> get onStatusUpdate => _statusUpdateStream.stream;

  final StreamController<Map<String, dynamic>> _cmdAckStream =
      StreamController<Map<String, dynamic>>.broadcast();
  Stream<Map<String, dynamic>> get onCmdAck => _cmdAckStream.stream;

    final StreamController<ToolUseEvent> _toolUseStream =
      StreamController<ToolUseEvent>.broadcast();
    Stream<ToolUseEvent> get onToolUse => _toolUseStream.stream;

    final StreamController<ToolApprovalRequest> _toolApprovalStream =
      StreamController<ToolApprovalRequest>.broadcast();
    Stream<ToolApprovalRequest> get onToolApprovalRequired =>
      _toolApprovalStream.stream;

    final StreamController<ReplyChainEvent> _replyChainStream =
      StreamController<ReplyChainEvent>.broadcast();
    Stream<ReplyChainEvent> get onReplyChain => _replyChainStream.stream;

  // ════════════════════════════════════════════════════════════════════
  // Connection Lifecycle
  // ════════════════════════════════════════════════════════════════════

  void connect() {
    if (_connected) return;
    _doConnect();
  }

  void _doConnect() {
    try {
      final wsUrl = ThroneConfig.wsUrl;
      _channel = WebSocketChannel.connect(Uri.parse(wsUrl));
      _connected = true;
      _reconnectAttempts = 0;
      notifyListeners();

      _subscription = _channel!.stream.listen(
        _onData,
        onError: _onError,
        onDone: _onDone,
      );
    } catch (e) {
      debugPrint('[WS] Connection failed: $e');
      _scheduleReconnect();
    }
  }

  void disconnect() {
    _reconnectTimer?.cancel();
    _subscription?.cancel();
    _channel?.sink.close();
    _connected = false;
    notifyListeners();
  }

  void _scheduleReconnect() {
    if (_reconnectAttempts >= ThroneConfig.wsMaxReconnectAttempts) {
      debugPrint('[WS] Max reconnect attempts reached');
      return;
    }
    _connected = false;
    notifyListeners();

    final delay = ThroneConfig.wsReconnectDelay * (_reconnectAttempts + 1);
    _reconnectTimer = Timer(Duration(milliseconds: delay), () {
      _reconnectAttempts++;
      debugPrint('[WS] Reconnect attempt $_reconnectAttempts');
      _doConnect();
    });
  }

  // ════════════════════════════════════════════════════════════════════
  // Inbound Message Handling
  // ════════════════════════════════════════════════════════════════════

  void _onData(dynamic raw) {
    try {
      final data = jsonDecode(raw as String) as Map<String, dynamic>;
      final type = data['type'] as String?;

      switch (type) {
        case 'STATE_UPDATE':
          _handleStateUpdate(data['payload'] as Map<String, dynamic>?);
          break;

        case 'TETHER_MESSAGE':
          _handleTetherMessage(data['data'] as Map<String, dynamic>? ?? data);
          break;

        case 'MSG_STATUS_UPDATE':
          _handleStatusUpdate(data['data'] as Map<String, dynamic>? ?? data);
          break;

        case 'CMD_ACK':
          _cmdAckStream.add(data);
          break;

        case 'TOOL_USE_EVENT':
          _toolUseStream.add(ToolUseEvent.fromJson(_extractPayload(data)));
          break;

        case 'TOOL_USE_APPROVAL_REQUIRED':
          _toolApprovalStream.add(
            ToolApprovalRequest.fromJson(_extractPayload(data)),
          );
          break;

        case 'REPLY_CHAIN_EVENT':
          _replyChainStream.add(ReplyChainEvent.fromJson(_extractPayload(data)));
          break;

        default:
          debugPrint('[WS] Unknown event type: $type');
      }
    } catch (e) {
      debugPrint('[WS] Parse error: $e');
    }
  }

  void _handleStateUpdate(Map<String, dynamic>? payload) {
    if (payload == null) return;
    final agentList = payload['agents'] as List<dynamic>?;
    if (agentList != null) {
      agents = agentList
          .map((j) => AgentState.fromJson(j as Map<String, dynamic>))
          .toList();
      notifyListeners();
    }
  }

  void _handleTetherMessage(Map<String, dynamic> data) {
    final msg = TetherMessage.fromJson(data);
    _liveMessages.add(msg);
    _messageStream.add(msg);
    notifyListeners();
  }

  void _handleStatusUpdate(Map<String, dynamic> data) {
    final ids =
        (data['message_ids'] as List<dynamic>?)
            ?.map((id) => id as String)
            .toSet() ??
        {};
    final newStatus = MessageStatus.fromString(
      data['status'] as String? ?? 'read',
    );
    for (final msg in _liveMessages) {
      if (ids.contains(msg.id)) {
        msg.status = newStatus;
      }
    }
    _statusUpdateStream.add(data);
    notifyListeners();
  }

  void _onError(Object error) {
    debugPrint('[WS] Error: $error');
    _scheduleReconnect();
  }

  void _onDone() {
    debugPrint('[WS] Connection closed');
    _scheduleReconnect();
  }

  Map<String, dynamic> _extractPayload(Map<String, dynamic> data) {
    final payload = data['data'] ?? data['payload'];
    if (payload is Map<String, dynamic>) {
      return payload;
    }
    return data;
  }

  // ════════════════════════════════════════════════════════════════════
  // Outbound — Tether Commands
  // ════════════════════════════════════════════════════════════════════

  /// Subscribe to a thread's real-time events.
  void joinThread(String threadId) {
    _send({
      'type': 'TETHER_JOIN',
      'payload': {'thread_id': threadId},
    });
  }

  /// Send a message via WebSocket (alternative to REST POST).
  void sendTetherMessage({
    required String threadId,
    required String agentId,
    required String content,
  }) {
    _send({
      'type': 'TETHER_SEND',
      'payload': {
        'thread_id': threadId,
        'agent_id': agentId,
        'content': content,
      },
    });
  }

  /// Mark messages as read via WebSocket.
  void markRead(List<String> messageIds) {
    _send({
      'type': 'TETHER_READ',
      'payload': {'message_ids': messageIds},
    });
  }

  void approveToolUse(String chainId) {
    _send({
      'type': 'TOOL_USE_APPROVE',
      'payload': {'chain_id': chainId},
    });
  }

  void denyToolUse(String chainId) {
    _send({
      'type': 'TOOL_USE_DENY',
      'payload': {'chain_id': chainId},
    });
  }

  void resumeReplyChain(String chainId) {
    _send({
      'type': 'REPLY_CHAIN_RESUME',
      'payload': {'chain_id': chainId},
    });
  }

  void cancelReplyChain(String chainId) {
    _send({
      'type': 'REPLY_CHAIN_CANCEL',
      'payload': {'chain_id': chainId},
    });
  }

  // ════════════════════════════════════════════════════════════════════
  // Outbound — GOD MODE Commands
  // ════════════════════════════════════════════════════════════════════

  /// Force-sync an agent's identity to a specific spirit.
  void godSync({required String agentId, required String spirit}) {
    _send({
      'type': 'GOD_SYNC',
      'payload': {'agent_id': agentId, 'spirit': spirit},
    });
  }

  /// Override an agent's mood.
  void godMood({required String agentId, required String mood}) {
    _send({
      'type': 'GOD_MOOD',
      'payload': {'agent_id': agentId, 'mood': mood},
    });
  }

  /// Inject stimuli into an agent's inbox.
  void godStimuli({required String agentId, required String content}) {
    _send({
      'type': 'GOD_STIMULI',
      'payload': {'agent_id': agentId, 'content': content},
    });
  }

  // ════════════════════════════════════════════════════════════════════
  // Send Helper
  // ════════════════════════════════════════════════════════════════════

  void _send(Map<String, dynamic> data) {
    if (!_connected || _channel == null) {
      debugPrint('[WS] Cannot send — not connected');
      return;
    }
    _channel!.sink.add(jsonEncode(data));
  }

  /// Clear cached live messages (e.g. on thread switch).
  void clearLiveMessages() {
    _liveMessages.clear();
    notifyListeners();
  }

  @override
  void dispose() {
    disconnect();
    _messageStream.close();
    _statusUpdateStream.close();
    _cmdAckStream.close();
    _toolUseStream.close();
    _toolApprovalStream.close();
    _replyChainStream.close();
    super.dispose();
  }
}
