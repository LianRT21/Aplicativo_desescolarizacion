# Integración Flutter con la API Campus Connect

## 1) Estructura recomendada

```text
lib/
  app/
    config/
      api_config.dart
    models/
      auth_model.dart
      student_model.dart
      risk_report_model.dart
    services/
      auth_service.dart
      student_service.dart
      risk_service.dart
    providers/
      auth_provider.dart
  screens/
    login_screen.dart
    dashboard_screen.dart
    risk_screen.dart
```

## 2) Configuración base

```dart
class ApiConfig {
  static const String baseUrl = 'http://localhost:8000';
  static const String authLogin = '/api/v1/auth/login';
  static const String dashboard = '/api/v1/dashboard';
  static const String students = '/api/v1/students';
  static const String risk = '/api/v1/risk/evaluate';
}
```

## 3) Auth service

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

class AuthService {
  static Future<Map<String, dynamic>> login(String username, String password) async {
    final response = await http.post(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.authLogin}'),
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: {'username': username, 'password': password},
    );

    if (response.statusCode != 200) {
      throw Exception('Error al iniciar sesión');
    }

    return jsonDecode(response.body);
  }
}
```

## 4) Modelo de login

```dart
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
```

## 5) Risk service

```dart
class RiskService {
  static Future<Map<String, dynamic>> evaluateRisk(Map<String, dynamic> payload) async {
    final response = await http.post(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.risk}'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(payload),
    );

    if (response.statusCode != 200) {
      throw Exception('No se pudo evaluar el riesgo');
    }

    return jsonDecode(response.body);
  }
}
```

## 6) Ejemplo de flujo

```dart
Future<void> iniciarSesion() async {
  final auth = await AuthService.login('teacher@campus.com', 'teacher123');
  final token = auth['access_token'];

  final dashboard = await http.get(
    Uri.parse('${ApiConfig.baseUrl}${ApiConfig.dashboard}'),
    headers: {'Authorization': 'Bearer $token'},
  );

  print(dashboard.body);
}
```

## 7) Recomendación visual

Para imitar la referencia de tus fotos, usa:
- azul primario para header
- fondo gris claro
- cards con bordes redondeados
- chips de estado: VERDE / AMARILLO / ROJO
- iconos de calendario, tareas, usuario y alertas
- menú inferior con navegación por roles

## 8) Roles del cliente

- Docente: toma de asistencia, notas, observador
- Acudiente: dashboard del hijo, promedio, riesgo, justificación
- Directivo: panel de riesgo por urgencia

## 9) Mejor estrategia para la app móvil

- guardar token en secure storage
- usar `Provider`, `Riverpod` o `Bloc`
- crear un interceptor para inyectar el token en cada request
- separar cada flujo por rol
- consumir la API a través de repositorios por entidad
