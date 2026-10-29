import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'api.dart';

class Session extends ChangeNotifier {
  final storage = const FlutterSecureStorage();
  Api? api;
  Json? user;
  bool loading = true;
  String? bootError;
  bool get admin => user?['role'] == 'admin';
  Future<void> boot() async {
    loading = true;
    bootError = null;
    notifyListeners();
    try {
      const builtUrl = String.fromEnvironment(
        'API_BASE_URL',
        defaultValue: 'https://tranvanvu-2380602601-api.onrender.com',
      );
      final url = await storage.read(key: 'server') ?? builtUrl;
      if (url.isNotEmpty && validServer(url)) {
        api = Api(url)..onUnauthorized = expire;
        api!.token = await storage.read(key: 'token');
        if (api!.token != null) {
          try {
            user = Json.from(await api!.call('/me'));
          } on ApiError catch (e) {
            if (api!.token != null) bootError = e.message;
          }
        }
      } else {
        api = null;
      }
    } catch (_) {
      bootError = 'Không đọc được cấu hình kết nối. Hãy thử lại hoặc thiết lập máy chủ.';
    }
    loading = false;
    notifyListeners();
  }

  Future<void> connect(String url) async {
    if (!validServer(url)) {
      throw ApiError('Cần địa chỉ HTTPS công khai của API đã deploy.');
    }
    final candidate = Api(url);
    final health = await candidate.call('/health');
    if (health is! Map || health['project'] != 'TranVanVu_2380602601') {
      throw ApiError('Địa chỉ này chưa trỏ tới API chấm công của project.');
    }
    await storage.delete(key: 'token');
    await storage.write(key: 'server', value: url);
    api = candidate..onUnauthorized = expire;
    user = null;
    bootError = null;
    notifyListeners();
  }

  Future<void> authenticate(Json result) async {
    api!.token = result['access_token'];
    user = Json.from(result['user']);
    await storage.write(key: 'token', value: api!.token);
    notifyListeners();
  }

  void expire() {
    api?.token = null;
    user = null;
    storage.delete(key: 'token');
    notifyListeners();
  }

  Future<void> logout() async {
    await api!.call('/auth/logout', method: 'POST');
    expire();
  }

  Future<void> changeServer() async {
    if (api?.token != null) await logout();
    await storage.delete(key: 'server');
    api = null;
    user = null;
    bootError = null;
    notifyListeners();
  }

  Future<void> updateProfile(Json data) async {
    user = Json.from(await api!.call('/me', method: 'PUT', body: data));
    notifyListeners();
  }
}
