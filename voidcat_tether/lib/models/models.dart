// Data models for the Tether protocol and agent state.
//
// These mirror the backend Pydantic models and PostgreSQL schema
// defined in `src/api/tether.py` and `config/init-scripts/02_tether_schema.sql`.

class AgentState {
  final String id;
  final String name;
  final String designation;
  final String mood;
  final double uptime;
  final DateTime? lastPulse;

  const AgentState({
    required this.id,
    required this.name,
    this.designation = '',
    this.mood = 'Neutral',
    this.uptime = 0,
    this.lastPulse,
  });

  factory AgentState.fromJson(Map<String, dynamic> json) {
    return AgentState(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      designation: json['designation'] as String? ?? '',
      mood: json['mood'] as String? ?? 'Neutral',
      uptime: (json['uptime'] as num?)?.toDouble() ?? 0,
      lastPulse: json['last_pulse'] != null
          ? DateTime.tryParse(json['last_pulse'] as String)
          : null,
    );
  }
}

// ── Tether Thread ──

enum ThreadType {
  userAgent('user_agent'),
  agentAgent('agent_agent'),
  broadcast('broadcast'),
  godMode('god_mode');

  final String value;
  const ThreadType(this.value);

  static ThreadType fromString(String s) {
    return ThreadType.values.firstWhere(
      (t) => t.value == s,
      orElse: () => ThreadType.userAgent,
    );
  }
}

class TetherThread {
  final String id;
  final ThreadType threadType;
  final String? subject;
  final String createdBy;
  final DateTime? createdAt;
  final DateTime? lastActivityAt;
  final int messageCount;
  final List<Map<String, dynamic>> participants;

  const TetherThread({
    required this.id,
    required this.threadType,
    this.subject,
    required this.createdBy,
    this.createdAt,
    this.lastActivityAt,
    this.messageCount = 0,
    this.participants = const [],
  });

  factory TetherThread.fromJson(Map<String, dynamic> json) {
    return TetherThread(
      id: json['id'] as String,
      threadType: ThreadType.fromString(
        json['thread_type'] as String? ?? 'user_agent',
      ),
      subject: json['subject'] as String?,
      createdBy: json['created_by'] as String? ?? '',
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'] as String)
          : null,
      lastActivityAt: json['last_activity_at'] != null
          ? DateTime.tryParse(json['last_activity_at'] as String)
          : null,
      messageCount: json['message_count'] as int? ?? 0,
      participants:
          (json['participants'] as List<dynamic>?)
              ?.map((p) => p as Map<String, dynamic>)
              .toList() ??
          [],
    );
  }

  /// Display-friendly title for the thread.
  String get displayTitle {
    if (subject != null && subject!.isNotEmpty) return subject!;
    if (participants.isNotEmpty) {
      final names = participants
          .map(
            (p) =>
                p['name'] as String? ?? p['agent_id'] as String? ?? 'Unknown',
          )
          .toList();
      return names.join(', ');
    }
    return 'Thread ${id.substring(0, 8)}';
  }
}

// ── Tether Message ──

enum MessageStatus {
  pending('pending'),
  delivered('delivered'),
  read('read'),
  expired('expired');

  final String value;
  const MessageStatus(this.value);

  static MessageStatus fromString(String s) {
    return MessageStatus.values.firstWhere(
      (m) => m.value == s,
      orElse: () => MessageStatus.pending,
    );
  }
}

enum SenderType {
  user('user'),
  agent('agent'),
  system('system');

  final String value;
  const SenderType(this.value);

  static SenderType fromString(String s) {
    return SenderType.values.firstWhere(
      (t) => t.value == s,
      orElse: () => SenderType.system,
    );
  }
}

class TetherMessage {
  final String id;
  final String threadId;
  final String senderName;
  final SenderType senderType;
  final String content;
  final String messageType;
  MessageStatus status;
  final String? replyTo;
  final DateTime? createdAt;

  TetherMessage({
    required this.id,
    required this.threadId,
    required this.senderName,
    required this.senderType,
    required this.content,
    this.messageType = 'chat',
    this.status = MessageStatus.pending,
    this.replyTo,
    this.createdAt,
  });

  factory TetherMessage.fromJson(Map<String, dynamic> json) {
    return TetherMessage(
      id: json['id'] as String,
      threadId: json['thread_id'] as String,
      senderName: json['sender_name'] as String? ?? 'Unknown',
      senderType: SenderType.fromString(
        json['sender_type'] as String? ?? 'system',
      ),
      content: json['content'] as String? ?? '',
      messageType: json['message_type'] as String? ?? 'chat',
      status: MessageStatus.fromString(json['status'] as String? ?? 'pending'),
      replyTo: json['reply_to'] as String?,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'] as String)
          : null,
    );
  }

  bool get isFromUser => senderType == SenderType.user;
  bool get isFromAgent => senderType == SenderType.agent;
  bool get isFromSystem => senderType == SenderType.system;
}

// ── Tool + Reply Chain Events ──

class ToolUseEvent {
  final String eventId;
  final String agentId;
  final String threadId;
  final String chainId;
  final int chainStep;
  final String chainStatus;
  final String phase;
  final String tool;
  final String server;
  final String argsPreview;
  final String resultPreview;
  final int? durationMs;
  final DateTime? timestamp;

  const ToolUseEvent({
    required this.eventId,
    required this.agentId,
    required this.threadId,
    required this.chainId,
    required this.chainStep,
    required this.chainStatus,
    required this.phase,
    required this.tool,
    required this.server,
    required this.argsPreview,
    required this.resultPreview,
    this.durationMs,
    this.timestamp,
  });

  factory ToolUseEvent.fromJson(Map<String, dynamic> json) {
    return ToolUseEvent(
      eventId: json['event_id'] as String? ?? '',
      agentId: json['agent_id'] as String? ?? '',
      threadId: json['thread_id'] as String? ?? '',
      chainId: json['chain_id'] as String? ?? '',
      chainStep: (json['chain_step'] as num?)?.toInt() ?? 0,
      chainStatus: json['chain_status'] as String? ?? '',
      phase: json['phase'] as String? ?? '',
      tool: json['tool'] as String? ?? '',
      server: json['server'] as String? ?? '',
      argsPreview: json['args_preview'] as String? ?? '',
      resultPreview: json['result_preview'] as String? ?? '',
      durationMs: (json['duration_ms'] as num?)?.toInt(),
      timestamp: json['timestamp'] != null
          ? DateTime.tryParse(json['timestamp'] as String)
          : null,
    );
  }
}

class ToolApprovalRequest {
  final String chainId;
  final int chainStep;
  final String agentId;
  final String threadId;
  final String tool;
  final String server;
  final String argsPreview;
  final int ttlSeconds;
  final DateTime? timestamp;

  const ToolApprovalRequest({
    required this.chainId,
    required this.chainStep,
    required this.agentId,
    required this.threadId,
    required this.tool,
    required this.server,
    required this.argsPreview,
    required this.ttlSeconds,
    this.timestamp,
  });

  factory ToolApprovalRequest.fromJson(Map<String, dynamic> json) {
    return ToolApprovalRequest(
      chainId: json['chain_id'] as String? ?? '',
      chainStep: (json['chain_step'] as num?)?.toInt() ?? 0,
      agentId: json['agent_id'] as String? ?? '',
      threadId: json['thread_id'] as String? ?? '',
      tool: json['tool'] as String? ?? '',
      server: json['server'] as String? ?? '',
      argsPreview: json['args_preview'] as String? ?? '',
      ttlSeconds: (json['ttl_seconds'] as num?)?.toInt() ?? 300,
      timestamp: json['timestamp'] != null
          ? DateTime.tryParse(json['timestamp'] as String)
          : null,
    );
  }
}

class ReplyChainEvent {
  final String eventId;
  final String agentId;
  final String threadId;
  final String chainId;
  final int chainStep;
  final String chainStatus;
  final String? parentMessageId;
  final String details;
  final DateTime? timestamp;

  const ReplyChainEvent({
    required this.eventId,
    required this.agentId,
    required this.threadId,
    required this.chainId,
    required this.chainStep,
    required this.chainStatus,
    this.parentMessageId,
    required this.details,
    this.timestamp,
  });

  factory ReplyChainEvent.fromJson(Map<String, dynamic> json) {
    return ReplyChainEvent(
      eventId: json['event_id'] as String? ?? '',
      agentId: json['agent_id'] as String? ?? '',
      threadId: json['thread_id'] as String? ?? '',
      chainId: json['chain_id'] as String? ?? '',
      chainStep: (json['chain_step'] as num?)?.toInt() ?? 0,
      chainStatus: json['chain_status'] as String? ?? '',
      parentMessageId: json['parent_message_id'] as String?,
      details: json['details'] as String? ?? '',
      timestamp: json['timestamp'] != null
          ? DateTime.tryParse(json['timestamp'] as String)
          : null,
    );
  }
}
