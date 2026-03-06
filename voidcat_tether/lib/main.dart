/// VoidCat Sovereign Spirit — The Throne Dashboard
///
/// A Flutter web application for monitoring and commanding
/// the Sovereign Spirit agent ecosystem via the Tether protocol.
library;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/theme.dart';
import 'services/api_service.dart';
import 'services/websocket_service.dart';
import 'features/dashboard/dashboard_page.dart';

void main() {
  runApp(const ThroneApp());
}

class ThroneApp extends StatelessWidget {
  const ThroneApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ApiService()),
        ChangeNotifierProxyProvider<ApiService, WebSocketService>(
          create: (_) => WebSocketService(),
          update: (_, api, ws) => ws!..apiService = api,
        ),
      ],
      child: MaterialApp(
        title: 'VoidCat Throne',
        debugShowCheckedModeBanner: false,
        theme: ThroneTheme.dark,
        home: const DashboardPage(),
      ),
    );
  }
}
