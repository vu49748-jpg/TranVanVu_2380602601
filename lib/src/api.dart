import 'package:dio/dio.dart';

typedef Json = Map<String, dynamic>;

class ApiError implements Exception {
  final String message;
  final Json? evidence;
  ApiError(this.message, {this.evidence});
  @override
  String toString() => message;
}

bool validServer(String text) {
  final uri = Uri.tryParse(text.trim());
  if (uri == null ||
      uri.scheme != 'https' ||
      uri.host.isEmpty ||
      uri.userInfo.isNotEmpty ||
      uri.hasQuery ||
      uri.hasFragment) {
    return false;
  }
  final host = uri.host.toLowerCase();
  if (host == 'localhost' ||
      host.endsWith('.localhost') ||
      host.endsWith('.local') ||
      host.contains(':') ||
      host.endsWith('.internal')) {
    return false;
  }
  final p = host.split('.').map(int.tryParse).toList();
  if (p.length == 4 && p.every((n) => n != null)) {
    if (p[0] == 0 ||
        p[0] == 10 ||
        p[0] == 127 ||
        p[0] == 169 && p[1] == 254 ||
        p[0] == 192 && p[1] == 168 ||
        p[0] == 172 && p[1]! >= 16 && p[1]! <= 31) {
      return false;
    }
  }
  return host.contains('.');
}

class Api {
  final Dio dio;
  String? token;
  void Function()? onUnauthorized;
  Api(String url)
    : dio = Dio(
        BaseOptions(
          baseUrl: url.replaceAll(RegExp(r'/+$'), ''),
          connectTimeout: const Duration(seconds: 30),
          receiveTimeout: const Duration(seconds: 60),
          sendTimeout: const Duration(seconds: 30),
          headers: {'Accept': 'application/json'},
        ),
      );
  Future<dynamic> call(
    String path, {
    String method = 'GET',
    dynamic body,
    ResponseType? type,
  }) async {
    try {
      return (await dio.request(
        path,
        data: body,
        options: Options(
          method: method,
          responseType: type,
          headers: {if (token != null) 'Authorization': 'Bearer $token'},
        ),
      )).data;
    } on DioException catch (error) {
      if (error.response?.statusCode == 401 && token != null) {
        onUnauthorized?.call();
      }
      final payload = error.response?.data;
      final detail = payload is Map ? payload['detail'] : null;
      if (detail is Map) {
        throw ApiError(
          '${detail['message'] ?? 'Không thực hiện được yêu cầu.'}',
          evidence: detail['evidence'] is Map
              ? Json.from(detail['evidence'])
              : null,
        );
      }
      if (detail is String) throw ApiError(detail);
      throw ApiError(
        error.response == null
            ? 'Không kết nối được máy chủ. Kiểm tra Internet và thử lại; máy chủ có thể đang khởi động.'
            : 'Máy chủ trả lỗi ${error.response?.statusCode}. Vui lòng thử lại sau.',
      );
    }
  }

  Future<List<Json>> list(String path) async =>
      (await call(path) as List).map((x) => Json.from(x)).toList();
}
