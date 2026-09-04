import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../services/api_client.dart';
import '../services/secure_storage_service.dart';

enum AuthStatus { unknown, authenticated, unauthenticated }

// State management class bridging authentication logic with the Flutter widget tree.
class AuthProvider extends ChangeNotifier {
  AuthProvider({
    ApiClient? apiClient,
    SecureStorageService? storageService,
  })  : _apiClient = apiClient ?? ApiClient.instance,
        _storage = storageService ?? SecureStorageService.instance {
    
    // Binds the API layer's session expiration event directly to the logout logic.
    _apiClient.onSessionExpired = logout;
  }

  final ApiClient _apiClient;
  final SecureStorageService _storage;

  AuthStatus _status = AuthStatus.unknown;
  String? _errorMessage;
  bool _isLoading = false;

  AuthStatus get status => _status;
  String? get errorMessage => _errorMessage;
  bool get isLoading => _isLoading;
  bool get isAuthenticated => _status == AuthStatus.authenticated;

  // Evaluates existing tokens on application startup to skip the login screen if valid.
  Future<void> restoreSession() async {
    final hasSession = await _storage.hasValidSession();
    _status = hasSession ? AuthStatus.authenticated : AuthStatus.unauthenticated;
    notifyListeners();
  }

  // Authenticates the user against the backend and persists JWT tokens on success.
  Future<bool> login(String username, String password) async {
    _setLoading(true);
    _errorMessage = null;

    try {
      final response = await _apiClient.post(
        '/auth/login/',
        body: {'username': username, 'password': password},
        authenticated: false,
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        await _storage.saveTokens(
          accessToken: data['access'] as String,
          refreshToken: data['refresh'] as String,
        );
        _status = AuthStatus.authenticated;
        _setLoading(false);
        return true;
      }

      _errorMessage = _extractErrorMessage(response);
      _status = AuthStatus.unauthenticated;
      _setLoading(false);
      return false;
    } catch (e) {
      _errorMessage = 'Network error. Please check your connection and try again.';
      _status = AuthStatus.unauthenticated;
      _setLoading(false);
      return false;
    }
  }

  // Clears on-device credentials and forcefully updates the UI state to unauthenticated.
  Future<void> logout() async {
    await _storage.clearTokens();
    _status = AuthStatus.unauthenticated;
    notifyListeners();
  }

  // Parses varied error payload structures returned by Django REST Framework and SimpleJWT.
  String _extractErrorMessage(http.Response response) {
    try {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      if (data['detail'] != null) return data['detail'].toString();
      
      final firstKey = data.keys.first;
      final firstValue = data[firstKey];
      if (firstValue is List && firstValue.isNotEmpty) {
        return firstValue.first.toString();
      }
      return firstValue.toString();
    } catch (_) {
      return 'Invalid username or password.';
    }
  }

  void _setLoading(bool value) {
    _isLoading = value;
    notifyListeners();
  }

  Future<bool> register({
    required String username,
    required String email,
    required String password,
    required String passwordConfirm,
  }) async {
    _setLoading(true);
    _errorMessage = null;

    try {
      final response = await _apiClient.post(
        '/auth/register/',
        body: {
          'username': username,
          'email': email,
          'password': password,
          'password_confirm': passwordConfirm,
        },
        authenticated: false,
      );

      if (response.statusCode == 201) {
        // Await the future to ensure local try-catch boundary is respected
        return await login(username, password);
      }

      _errorMessage = _extractErrorMessage(response);
      _setLoading(false);
      return false;
    } catch (e) {
      // Secure logging for ADB wireless debugging, ignored in release builds
      debugPrint('[Auth Error - Register]: $e');
      _errorMessage = 'Network error. Please check your connection and try again.';
      _setLoading(false);
      return false;
    }
  }
}