import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../core/config.dart';
import '../models/models.dart';

/// REST client for the Sovereign Spirit middleware API.
///
/// Covers:
///   - Tether protocol routes (`/api/tether/*`)
///   - Agent management (`/api/agents`)
///   - System logs (`/api/logs/thoughts`)
///   - Pulse control (`/api/pulse/trigger`)
///   - Health check (`/health`)
class ApiService extends ChangeNotifier {
  final http.Client _client = http.Client();

  String get _base => ThroneConfig.baseUrl;

  Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  // ════════════════════════════════════════════════════════════════════
  // Health
  // ════════════════════════════════════════════════════════════════════

  Future<Map<String, dynamic>> healthCheck() async {
    final res = await _client.get(
      Uri.parse('$_base/health'),
      headers: _headers,
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  // ════════════════════════════════════════════════════════════════════
  // Tether — Threads
  // ════════════════════════════════════════════════════════════════════

  /// List threads, optionally filtered by agent and/or type.
  Future<List<TetherThread>> listThreads({
    String? agentId,
    String? threadType,
    int limit = 20,
  }) async {
    final params = <String, String>{'limit': limit.toString()};
    if (agentId != null) params['agent_id'] = agentId;
    if (threadType != null) params['thread_type'] = threadType;

    final uri = Uri.parse(
      '$_base/api/tether/threads',
    ).replace(queryParameters: params);
    final res = await _client.get(uri, headers: _headers);

    if (res.statusCode != 200) {
      throw ApiException('Failed to list threads: ${res.statusCode}');
    }
    final List<dynamic> data = jsonDecode(res.body) as List<dynamic>;
    return data
        .map((j) => TetherThread.fromJson(j as Map<String, dynamic>))
        .toList();
  }

  /// Get a single thread with participants.
  Future<TetherThread> getThread(String threadId) async {
    final res = await _client.get(
      Uri.parse('$_base/api/tether/threads/$threadId'),
      headers: _headers,
    );
    if (res.statusCode != 200) {
      throw ApiException('Thread not found: ${res.statusCode}');
    }
    return TetherThread.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  /// Create a new thread.
  Future<TetherThread> createThread({
    String threadType = 'user_agent',
    String? subject,
    List<String> agentIds = const [],
  }) async {
    final res = await _client.post(
      Uri.parse('$_base/api/tether/threads'),
      headers: _headers,
      body: jsonEncode({
        'thread_type': threadType,
        'subject': subject,
        'agent_ids': agentIds,
      }),
    );
    if (res.statusCode != 200 && res.statusCode != 201) {
      throw ApiException('Failed to create thread: ${res.statusCode}');
    }
    return TetherThread.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  // ════════════════════════════════════════════════════════════════════
  // Tether — Messages
  // ════════════════════════════════════════════════════════════════════

  /// Get messages in a thread (cursor-paginated).
  Future<List<TetherMessage>> getThreadMessages(
    String threadId, {
    String? before,
    int limit = 50,
  }) async {
    final params = <String, String>{'limit': limit.toString()};
    if (before != null) params['before'] = before;

    final uri = Uri.parse(
      '$_base/api/tether/threads/$threadId/messages',
    ).replace(queryParameters: params);
    final res = await _client.get(uri, headers: _headers);

    if (res.statusCode != 200) {
      throw ApiException('Failed to load messages: ${res.statusCode}');
    }
    final Map<String, dynamic> data =
        jsonDecode(res.body) as Map<String, dynamic>;
    final List<dynamic> messages = data['messages'] as List<dynamic>? ?? [];
    return messages
        .map((j) => TetherMessage.fromJson(j as Map<String, dynamic>))
        .toList();
  }

  // ════════════════════════════════════════════════════════════════════
  // Tether — Direct Send
  // ════════════════════════════════════════════════════════════════════

  /// Send a message directly to an agent (creates/reuses thread).
  Future<Map<String, dynamic>> sendDirectMessage({
    required String agentId,
    required String content,
    String senderName = 'User',
  }) async {
    final res = await _client.post(
      Uri.parse('$_base/api/tether/send'),
      headers: _headers,
      body: jsonEncode({
        'agent_id': agentId,
        'content': content,
        'sender_name': senderName,
      }),
    );
    if (res.statusCode != 200) {
      throw ApiException('Send failed: ${res.statusCode}');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  // ════════════════════════════════════════════════════════════════════
  // Tether — Inbox
  // ════════════════════════════════════════════════════════════════════

  /// Get an agent's unread inbox.
  Future<Map<String, dynamic>> getAgentInbox(
    String agentId, {
    int limit = 10,
  }) async {
    final res = await _client.get(
      Uri.parse('$_base/api/tether/inbox/$agentId?limit=$limit'),
      headers: _headers,
    );
    if (res.statusCode != 200) {
      throw ApiException('Inbox fetch failed: ${res.statusCode}');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// Mark messages as read.
  Future<void> markMessagesRead(String agentId, List<String> messageIds) async {
    await _client.post(
      Uri.parse('$_base/api/tether/inbox/$agentId/read'),
      headers: _headers,
      body: jsonEncode({'message_ids': messageIds}),
    );
  }

  // ════════════════════════════════════════════════════════════════════
  // System — Logs & Pulse
  // ════════════════════════════════════════════════════════════════════

  /// Get system thought logs.
  Future<List<Map<String, dynamic>>> getSystemThoughts({int limit = 50}) async {
    final res = await _client.get(
      Uri.parse('$_base/api/logs/thoughts?limit=$limit'),
      headers: _headers,
    );
    if (res.statusCode != 200) return [];
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    return (data['logs'] as List<dynamic>?)
            ?.map((l) => l as Map<String, dynamic>)
            .toList() ??
        [];
  }

  /// Trigger a manual pulse.
  Future<Map<String, dynamic>> triggerPulse({
    String? agentId,
    String action = 'MUSE',
  }) async {
    final res = await _client.post(
      Uri.parse('$_base/api/pulse/trigger'),
      headers: _headers,
      body: jsonEncode({'agent_id': agentId, 'action': action}),
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  // ════════════════════════════════════════════════════════════════════
  // Config — Bifrost & LLM
  // ════════════════════════════════════════════════════════════════════

  /// Get current Bifrost inference configuration.
  Future<Map<String, dynamic>> getInferenceConfig() async {
    final res = await _client.get(
      Uri.parse('$_base/config/inference'),
      headers: _headers,
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// Update Bifrost inference mode (AUTO/LOCAL/CLOUD).
  Future<Map<String, dynamic>> updateInferenceMode(String mode) async {
    final res = await _client.post(
      Uri.parse('$_base/config/inference'),
      headers: _headers,
      body: jsonEncode({'mode': mode}),
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// Get all LLM provider configurations.
  Future<Map<String, dynamic>> getLLMProviders() async {
    final res = await _client.get(
      Uri.parse('$_base/config/llm'),
      headers: _headers,
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// Check health of all LLM providers.
  Future<Map<String, dynamic>> getLLMHealth() async {
    final res = await _client.get(
      Uri.parse('$_base/config/llm/health'),
      headers: _headers,
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// Get MCP tool registry (grouped by server).
  Future<Map<String, dynamic>> getToolRegistry() async {
    final res = await _client.get(
      Uri.parse('$_base/config/tools'),
      headers: _headers,
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  // ════════════════════════════════════════════════════════════════════
  // Config — Bifrost Extended
  // ════════════════════════════════════════════════════════════════════

  /// Test a single LLM provider's health.
  Future<Map<String, dynamic>> testProviderHealth(String name) async {
    final res = await _client.get(
      Uri.parse('$_base/config/llm/health/$name'),
      headers: _headers,
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// Send a test prompt to a provider and get response.
  Future<Map<String, dynamic>> testProviderReply(String name) async {
    final res = await _client.post(
      Uri.parse('$_base/config/llm/test/$name'),
      headers: _headers,
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// Save full LLM config.
  Future<Map<String, dynamic>> saveLLMConfig(
    Map<String, dynamic> config,
  ) async {
    final res = await _client.post(
      Uri.parse('$_base/config/llm'),
      headers: _headers,
      body: jsonEncode(config),
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// Warm up local provider.
  Future<Map<String, dynamic>> warmLocalProvider() async {
    final res = await _client.post(
      Uri.parse('$_base/config/llm/warm'),
      headers: _headers,
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  // ════════════════════════════════════════════════════════════════════
  // Config — MCP Tools Extended
  // ════════════════════════════════════════════════════════════════════

  /// Connect/reconnect an MCP server.
  Future<Map<String, dynamic>> connectMCPServer(String name) async {
    final res = await _client.post(
      Uri.parse('$_base/config/tools/connect/$name'),
      headers: _headers,
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// Disconnect an MCP server.
  Future<Map<String, dynamic>> disconnectMCPServer(String name) async {
    final res = await _client.post(
      Uri.parse('$_base/config/tools/disconnect/$name'),
      headers: _headers,
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// Test an MCP tool with arguments.
  Future<Map<String, dynamic>> testMCPTool(
    String server,
    String tool,
    Map<String, dynamic> args,
  ) async {
    final res = await _client.post(
      Uri.parse('$_base/config/tools/test/$server/$tool'),
      headers: _headers,
      body: jsonEncode(args),
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// Get MCP server registry.
  Future<Map<String, dynamic>> getMCPRegistry() async {
    final res = await _client.get(
      Uri.parse('$_base/config/tools/registry'),
      headers: _headers,
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// Add server to MCP registry.
  Future<Map<String, dynamic>> addMCPServer(
    String name,
    String command,
    List<String> args,
    {int securityTier = 1}
  ) async {
    final res = await _client.post(
      Uri.parse('$_base/config/tools/registry'),
      headers: _headers,
      body: jsonEncode({
        'name': name,
        'command': command,
        'args': args,
        'security_tier': securityTier,
      }),
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  // ════════════════════════════════════════════════════════════════════
  // Config — Agent Activity
  // ════════════════════════════════════════════════════════════════════

  /// Get recent activity (heartbeat decisions) for an agent.
  Future<Map<String, dynamic>> getAgentActivity(
    String agentId, {
    int limit = 10,
  }) async {
    final res = await _client.get(
      Uri.parse('$_base/config/agents/$agentId/activity?limit=$limit'),
      headers: _headers,
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  @override
  void dispose() {
    _client.close();
    super.dispose();
  }
}

class ApiException implements Exception {
  final String message;
  const ApiException(this.message);

  @override
  String toString() => 'ApiException: $message';
}
