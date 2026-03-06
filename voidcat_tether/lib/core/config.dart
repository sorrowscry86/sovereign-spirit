/// Configuration constants for the Throne dashboard.
class ThroneConfig {
  ThroneConfig._();

  /// Base URL for the Sovereign Spirit middleware API.
  /// In Docker, the middleware runs at port 8090.
  /// When served from the same origin, use relative paths.
  static String get baseUrl {
    // When served from the middleware itself, use same-origin
    return '';
  }

  /// WebSocket URL for the dashboard channel.
  static String get wsUrl {
    // Construct from window.location for same-origin
    final uri = Uri.base;
    final scheme = uri.scheme == 'https' ? 'wss' : 'ws';
    return '$scheme://${uri.host}:${uri.port}/ws/dashboard';
  }

  /// State update broadcast interval from server (seconds).
  static const int stateUpdateInterval = 2;

  /// WebSocket reconnect delay (milliseconds).
  static const int wsReconnectDelay = 3000;

  /// Maximum reconnect attempts before giving up.
  static const int wsMaxReconnectAttempts = 10;

  /// Default message page size.
  static const int defaultMessageLimit = 50;

  /// Default thread list page size.
  static const int defaultThreadLimit = 20;
}
