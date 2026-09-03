import json
import time
from typing import Any, Dict, Optional
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs


class DeliveryAPIHandler(BaseHTTPRequestHandler):
    """Обработчик HTTP-запросов для сервиса автодоставки."""

    # Конфигурация лимитов (в секундах)
    RATE_LIMIT_WINDOW = 60
    MAX_REQUESTS_PER_WINDOW = 10
    
    # Хранилище состояния для rate-limiting в памяти процесса
    _rate_limit_store: Dict[str, tuple] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._request_body: Optional[Dict[str, Any]] = None

    @property
    def client_ip(self) -> str:
        """Получение IP-адреса клиента."""
        return self.client_address[0]

    def _log_message(self, format_string: str, *args):
        """Унифицированное логирование."""
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {format_string}", *args)

    def _validate_request_body(self, data: Dict[str, Any]) -> bool:
        """Валидация входящих данных JSON."""
        required_fields = ['pickup_address', 'delivery_address']
        
        if not isinstance(data, dict):
            self._log_message("Validation Error", "Root element must be an object")
            return False

        for field in required_fields:
            if field not in data:
                self._log_message("Validation Error", f"Missing required field: {field}")
                return False
        
        # Проверка типов (упрощенная)
        if not isinstance(data.get('pickup_address'), str):
             self._log_message("Validation Error", "pickup_address must be a string")
             return False

        return True

    def _check_rate_limit(self, client_ip: str) -> bool:
        """Проверка лимита частоты запросов."""
        current_time = time.time()
        
        # Если IP не в кэше или прошло время окна — сбрасываем счетчик
        if client_ip not in self._rate_limit_store or \
           (current_time - self._rate_limit_store[client_ip][0]) > self.RATE_LIMIT_WINDOW:
            self._rate_limit_store[client_ip] = (current_time, 1)
            return True

        last_request_time, count = self._rate_limit_store[client_ip]
        
        if count >= self.MAX_REQUESTS_PER_WINDOW:
            # Лимит превышен
            remaining_window = int(self.RATE_LIMIT_WINDOW - (current_time - last_request_time))
            self._log_message("Rate Limit", f"Client {client_ip} exceeded limit. Wait {remaining_window}s")
            return False

        # Увеличиваем счетчик
        new_count = count + 1
        self._rate_limit_store[client_ip] = (last_request_time, new_count)
        
        return True

    def _call_delivery_service(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Вызов сервиса доставки."""
        # Имитация вызова внешнего сервиса
        try:
            # В реальном проекте здесь будет импорт и вызов services/delivery_service.py
            from services.delivery_service import DeliveryService
            
            service = DeliveryService()
            result = service.process_delivery(payload)
            
            if 'error' in result:
                self._log_message("Delivery Error", result['error'])
                return {
                    "status": "failed",
                    "message": result.get('error', 'Unknown error'),
                    "code": 500
                }

            return {
                "status": "success",
                "tracking_id": f"TRK-{int(time.time())}",
                "estimated_delivery": (time.time() + 7200),  # 2 часа в будущем
                "message": "Order accepted for processing"
            }

        except ImportError:
            self._log_message("Service Error", "Delivery service module not found")
            return {
                "status": "failed",
                "message": "External delivery service unavailable (check services/delivery_service.py)",
                "code": 503
            }

    def _parse_request_body(self) -> Optional[Dict[str, Any]]:
        """Парсинг тела POST-запроса."""
        content_length = int(self.headers.get('Content-Length', 0))
        
        if content_length > 1048576:  # 1MB лимит
            self._log_message("Request Error", "Body too large")
            return None

        try:
            body_bytes = self.rfile.read(content_length)
            data = json.loads(body_bytes.decode('utf-8'))
            
            if not isinstance(data, dict):
                self._log_message("Parse Error", "JSON root must be an object")
                return None
            
            return data

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self._log_message("Parse Error", str(e))
            return None

    def _send_json_response(self, status_code: int = 200, 
                           response_data: Optional[Dict[str, Any]] = None):
        """Удобная отправка JSON-ответа."""
        if response_data is not None:
            body = json.dumps(response_data)
        else:
            body = ''

        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        
        if body:
            self.wfile.write(body.encode('utf-8'))

    def _handle_create_order(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка создания нового заказа."""
        # Проверка rate-limit
        if not self._check_rate_limit(self.client_ip):
            return {
                "status": "rate_limited",
                "message": f"Too many requests. Retry in 60s.",
                "code": 429
            }

        # Валидация данных
        if not self._validate_request_body(data):
            return {
                "status": "validation_failed",
                "message": "Invalid order data format",
                "code": 400
            }

        # Вызов сервиса доставки
        result = self._call_delivery_service(data)
        
        if result['status'] == 'success':
            return {
                "status": "created",
                "tracking_id": result.get('tracking_id'),
                "message": "Order created successfully"
            }
        
        # Возвращаем ошибку от сервиса с кодом 400 для валидации данных
        if 'pickup_address' in data or 'delivery_address' in data:
            return {
                "status": "validation_failed",
                "message": result.get('message', 'Order processing error'),
                "code": 400
            }

        return result

    def _handle_get_status(self, tracking_id: str) -> Dict[str, Any]:
        """Обработка получения статуса заказа."""
        # Имитация проверки в базе данных
        mock_orders = {
            'TRK-1735689234': {'status': 'in_transit', 'eta': 3600},
            'TRK-1735689235': {'status': 'delivered', 'eta': 0},
        }

        if tracking_id in mock_orders:
            order = mock_orders[tracking_id]
            return {
                "status": "found",
                "tracking_id": tracking_id,
                "current_status": order['status'],
                "estimated_delivery_eta": order.get('eta', 0)
            }

        return {
            "status": "not_found",
            "tracking_id": tracking_id,
            "message": "Order not found"
        }

    def do_GET(self):
        """Обработка GET-запросов."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/api/v1/orders/status':
            # Получение статуса заказа по tracking_id из query params
            query_params = parse_qs(parsed_path.query)
            tracking_id = query_params.get('tracking_id', [''])[0]

            if not tracking_id:
                self._send_json_response(400, {
                    "status": "missing_param",
                    "message": "Query parameter 'tracking_id' is required"
                })
                return

            result = self._handle_get_status(tracking_id)
            self._send_json_response(200 if result['status'] == 'found' else 404, result)

        elif path == '/api/v1/orders/health':
            # Эндпоинт для проверки работоспособности сервиса
            self._send_json_response(200, {
                "status": "healthy",
                "service": "DeliveryAPI",
                "version": "1.0.0"
            })

        else:
            self._log_message("Route Not Found", path)
            self._send_json_response(404, {
                "status": "not_found",
                "path": path,
                "message": "API endpoint not found"
            })

    def do_POST(self):
        """Обработка POST-запросов."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/api/v1/orders':
            # Создание нового заказа
            data = self._parse_request_body()
            
            if data is None:
                return

            result = self._handle_create_order(data)
            status_code = 201 if result['status'] == 'created' else (400 if result['status'] in ['validation_failed', 'rate_limited'] else 500)
            
            self._send_json_response(status_code, result)

        elif path == '/api/v1/orders/refresh':
            # Принудительное обновление статуса заказа
            query_params = parse_qs(parsed_path.query)
            tracking_id = query_params.get('tracking_id', [''])[0]

            if not tracking_id:
                self._send_json_response(400, {
                    "status": "missing_param",
                    "message": "Query parameter 'tracking_id' is required"
                })
                return

            # Имитация обновления статуса
            mock_orders = {
                'TRK-1735689234': {'status': 'in_transit', 'eta': 3600},
                'TRK-1735689235': {'status': 'delivered', 'eta': 0},
            }

            if tracking_id in mock_orders:
                # Обновляем статус на "processing" для демонстрации
                mock_orders[tracking_id]['status'] = 'processing'
                
                self._send_json_response(200, {
                    "status": "refreshed",
                    "tracking_id": tracking_id,
                    "previous_status": mock_orders.get('TRK-1735689234', {}).get('status'),
                    "current_status": 'processing'
                })
            else:
                self._send_json_response(404, {
                    "status": "not_found",
                    "tracking_id": tracking_id
                })

        elif path == '/api/v1/orders/reset':
            # Сброс rate-limit для тестирования
            self._rate_limit_store.clear()
            self._send_json_response(200, {
                "status": "reset",
                "message": "Rate limit counters cleared for all clients"
            })

        else:
            self._log_message("Route Not Found", path)
            self._send_json_response(404, {
                "status": "not_found",
                "path": path,
                "message": "API endpoint not found"
            })

    def log_message(self, format_string: str, *args):
        """Переопределение логирования для совместимости с BaseHTTPRequestHandler."""
        self._log_message(format_string, *args)


def create_server(host: str = '0.0.0.0', port: int = 8080):
    """Создание и запуск HTTP-сервера."""
    server_address = (host, port)
    httpd = HTTPServer(server_address, DeliveryAPIHandler)
    
    print(f"Delivery API Server running on http://{host}:{port}")
    print("Available endpoints:")
    print("  GET  /api/v1/orders/health      — Health check")
    print("  POST /api/v1/orders             — Create new order")
    print("  GET  /api/v1/orders/status?tracking_id=TRK-... — Get status")
    print("  POST /api/v1/orders/refresh?tracking_id=TRK-... — Refresh status")
    print("  POST /api/v1/orders/reset       — Reset rate limits (testing)")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")


if __name__ == '__main__':
    create_server()
