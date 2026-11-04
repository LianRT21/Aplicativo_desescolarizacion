import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiConfig {
  static const String baseUrl = 'http://localhost:8000';
  static const String login = '/api/v1/auth/login';
  static const String dashboard = '/api/v1/dashboard';
  static const String risk = '/api/v1/risk/evaluate';
}

class AuthResponse {
  final String accessToken;
  final String tokenType;
  final User user;

  AuthResponse({
    required this.accessToken,
    required this.tokenType,
    required this.user,
  });

  factory AuthResponse.fromJson(Map<String, dynamic> json) {
    return AuthResponse(
      accessToken: json['access_token'],
      tokenType: json['token_type'],
      user: User.fromJson(json['user']),
    );
  }
}

class User {
  final String id;
  final String email;
  final String fullName;
  final String role;

  User({
    required this.id,
    required this.email,
    required this.fullName,
    required this.role,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      email: json['email'],
      fullName: json['full_name'],
      role: json['role'],
    );
  }
}

class CampusApi {
  static Future<AuthResponse> login(String username, String password) async {
    final response = await http.post(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.login}'),
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: {'username': username, 'password': password},
    );

    if (response.statusCode != 200) {
      throw Exception('Login falló: ${response.body}');
    }

    return AuthResponse.fromJson(jsonDecode(response.body));
  }

  static Future<Map<String, dynamic>> getDashboard(String token) async {
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.dashboard}'),
      headers: {'Authorization': 'Bearer $token'},
    );

    if (response.statusCode != 200) {
      throw Exception('Dashboard falló: ${response.body}');
    }

    return jsonDecode(response.body);
  }

  static Future<Map<String, dynamic>> evaluateRisk(Map<String, dynamic> payload, String token) async {
    final response = await http.post(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.risk}'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode(payload),
    );

    if (response.statusCode != 200) {
      throw Exception('Evaluación de riesgo falló: ${response.body}');
    }

    return jsonDecode(response.body);
  }
}

void main() async {
  try {
    final auth = await CampusApi.login('teacher@campus.com', 'teacher123');
    print('Token: ${auth.accessToken}');

    final dashboard = await CampusApi.getDashboard(auth.accessToken);
    print('Dashboard: $dashboard');

    final payload = {
      'id': 'stu-001',
      'full_name': 'Ana Gómez',
      'document_number': '1012345678',
      'grade': '11A',
      'status': 'ACTIVE',
      'attendance_records': [
        {'student_id': 'stu-001', 'date': '2026-09-01', 'present': false},
        {'student_id': 'stu-001', 'date': '2026-09-02', 'present': false},
      ],
      'grades': [
        {'student_id': 'stu-001', 'subject': 'Matemáticas', 'period': 'Corte 1', 'value': 2.8},
      ],
      'observer_records': [
        {'student_id': 'stu-001', 'category': 'Familiar/Entorno', 'description': 'Sin apoyo familiar', 'severity': 'MEDIUM'},
      ],
      'absent_parent_meetings': 1,
      'warnings_this_month': 2,
    };

    final risk = await CampusApi.evaluateRisk(payload, auth.accessToken);
    print('Riesgo: $risk');
  } catch (e) {
    print('Error: $e');
  }
}
