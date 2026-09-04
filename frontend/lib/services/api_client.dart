import 'dart:convert';
import 'package:http/http.dart' as http;
import 'secure_storage_service.dart';

// Exception thrown when the refresh token is invalid or expired.
class SessionExpiredException implements Exception {
  final String message;
  SessionExpiredException([this.message = 'Session expired. Please log in again.']);

  @override
  String toString() => message;
}

// HTTP client wrapper enforcing JWT injection and silent token rotation.
class ApiClient {
  ApiClient._internal();
  static final ApiClient instance = ApiClient._internal();

  // Targets the host machine's physical LAN IP for wireless debugging via ADB.
  static const String baseUrl = 'http://10.8.195.99:8000/api/v1';

  final http.Client _httpClient = http.Client();
  final SecureStorageService _storage = SecureStorageService.instance;

  // Callback triggered upon terminal session failure to notify the state management layer.
  void Function()? onSessionExpired;

  // Tracks ongoing refresh operations to prevent duplicate network calls.
  Future<bool>? _refreshInFlight;

  Uri _buildUri(String path, [Map<String, dynamic>? queryParams]) {
    return Uri.parse('$baseUrl$path').replace(
      queryParameters: queryParams?.map((k, v) => MapEntry(k, v.toString())),
    );
  }

  Future<Map<String, String>> _buildHeaders({bool authenticated = true}) async {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    
    if (authenticated) {
      final accessToken = await _storage.getAccessToken();
      if (accessToken != null) {
        headers['Authorization'] = 'Bearer $accessToken';
      }
    }
    return headers;
  }

  // Interceptor core: executes requests, catches 401s, attempts refresh, and retries once.
  Future<http.Response> _sendWithAuthRetry(
    Future<http.Response> Function(Map<String, String> headers) requestFn, {
    bool authenticated = true,
  }) async {
    final headers = await _buildHeaders(authenticated: authenticated);
    final response = await requestFn(headers);

    if (response.statusCode != 401 || !authenticated) {
      return response;
    }

    final refreshed = await _refreshAccessToken();
    if (!refreshed) {
      await _storage.clearTokens();
      onSessionExpired?.call(); // Dispatch global logout event.
      throw SessionExpiredException();
    }

    final retryHeaders = await _buildHeaders(authenticated: authenticated);
    return requestFn(retryHeaders);
  }

  // Deduplicates concurrent refresh requests using the _refreshInFlight lock.
  Future<bool> _refreshAccessToken() {
    _refreshInFlight ??= _performRefresh().whenComplete(() {
      _refreshInFlight = null;
    });
    return _refreshInFlight!;
  }

  // Executes the physical network call to exchange the refresh token for a new access token.
  Future<bool> _performRefresh() async {
    final refreshToken = await _storage.getRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) {
      return false;
    }

    try {
      final response = await _httpClient.post(
        _buildUri('/auth/refresh/'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'refresh': refreshToken}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        final newAccessToken = data['access'] as String;
        await _storage.saveAccessToken(newAccessToken);

        if (data['refresh'] != null) {
          await _storage.saveTokens(
            accessToken: newAccessToken,
            refreshToken: data['refresh'] as String,
          );
        }
        return true;
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  // Standard HTTP methods mapped to the authentication interceptor.
  Future<http.Response> get(String path, {Map<String, dynamic>? queryParams, bool authenticated = true}) {
    return _sendWithAuthRetry((headers) => _httpClient.get(_buildUri(path, queryParams), headers: headers), authenticated: authenticated);
  }

  Future<http.Response> post(String path, {Object? body, bool authenticated = true}) {
    return _sendWithAuthRetry((headers) => _httpClient.post(_buildUri(path), headers: headers, body: jsonEncode(body)), authenticated: authenticated);
  }

  Future<http.Response> put(String path, {Object? body, bool authenticated = true}) {
    return _sendWithAuthRetry((headers) => _httpClient.put(_buildUri(path), headers: headers, body: jsonEncode(body)), authenticated: authenticated);
  }

  Future<http.Response> patch(String path, {Object? body, bool authenticated = true}) {
    return _sendWithAuthRetry((headers) => _httpClient.patch(_buildUri(path), headers: headers, body: jsonEncode(body)), authenticated: authenticated);
  }

  Future<http.Response> delete(String path, {bool authenticated = true}) {
    return _sendWithAuthRetry((headers) => _httpClient.delete(_buildUri(path), headers: headers), authenticated: authenticated);
  }
}