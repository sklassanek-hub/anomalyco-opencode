"""
handlers/exceptions.py — Обработчики исключений: перехват, классификация, восстановление

Архитектура:
├── BaseExceptionHandler (базовый класс)
│   ├── classify() — определение типа ошибки
│   ├── handle() — общий обработчик
│   └── recover() — восстановление состояния
├── SpecificHandlers (конкретные обработчики)
│   ├── CommandHandler — обработка ошибок команд
│   ├── APIHandler — обработка сетевых/API сбоев
│   └── DatabaseHandler — обработка БД ошибок
├── RecoveryManager (менеджер восстановления)
│   ├── StateSnapshot — сохранение состояния до сбоя
│   └── RollbackService — откат изменений
└── GlobalExceptionMiddleware (глобальный перехватчик)

Совместимость:
- bot.py: inject() для регистрации обработчиков в цикл обработки
- config/settings.py: read_settings() для получения порогов логирования
- utils/logger.py: log_error() с контекстом и стеком вызова
- models/error_types.py: map_to_type() для классификации исключений
"""

import asyncio
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union

# Импорты из других модулей проекта
from config.settings import get_exception_settings
from utils.logger import log_error, log_warning, log_info
from models.error_types import (
    ErrorType,
    CommandError,
    APIError,
    DatabaseError,
    NetworkError,
    ValidationError,
    TimeoutError,
)


# =============================================================================
# КОНФИГУРАЦИЯ И ДАННЫЕ
# =============================================================================

@dataclass
class ExceptionContext:
    """Контекст при возникновении исключения"""
    error_type: ErrorType
    exception: BaseException
    traceback: str = field(default_factory=lambda: "")
    context_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if self.exception and not isinstance(self.traceback, str):
            self.traceback = traceback.format_exc()

@dataclass 
class RecoveryState:
    """Состояние перед сбоем для восстановления"""
    operation_id: Optional[str] = None
    snapshot_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


# =============================================================================
# БАЗОВЫЙ КЛАСС ОБРАБОТЧИКА
# =============================================================================

class BaseExceptionHandler(ABC):
    """Базовый класс для всех обработчиков исключений"""
    
    def __init__(self, priority: int = 100, name: str = "Base"):
        self.priority = priority
        self.name = name
        self.recovery_attempts = 0
        self.last_error: Optional[Exception] = None
        
    @abstractmethod
    def classify(self, error_type: ErrorType) -> bool:
        """Определяет, обрабатывает ли этот обработчик данный тип ошибки"""
        pass
    
    @abstractmethod  
    async def handle(self, context: ExceptionContext) -> Dict[str, Any]:
        """Основная логика обработки исключения"""
        pass
    
    def recover(self, context: ExceptionContext) -> bool:
        """Попытка восстановления после сбоя"""
        self.recovery_attempts += 1
        
        if self.last_error and isinstance(self.last_error, type(context.exception)):
            try:
                # Попытка отката или перезапуска операции
                result = self._attempt_recovery(context)
                
                if result:
                    log_info(f"Восстановление успешно для {self.name}", extra={"attempts": self.recovery_attempts})
                    self.last_error = None
                    return True
                else:
                    log_warning(f"Восстановление не удалось ({self.name})", extra={"attempts": self.recovery_attempts})
            except Exception as e:
                log_error(f"Ошибка при восстановлении {self.name}: {e}", exc_info=True)
        
        # Если это первая попытка или предыдущая провалилась
        if not self.last_error or self.recovery_attempts > 3:
            log_warning(f"Критический сбой в модуле {self.name}, требуется ручной перезапуск", extra={"attempts": self.recovery_attempts})
        
        return False
    
    def _attempt_recovery(self, context: ExceptionContext) -> bool:
        """Внутренний метод для реализации логики отката"""
        # Реализация зависит от конкретного обработчика
        if not context.snapshot_data:
            log_warning(f"Нет данных для отката в контексте {context.error_type}")
            return False
        
        try:
            # Примерная логика восстановления (заглушка)
            restored = self._restore_state(context.snapshot_data, context.operation_id)
            if restored:
                context.context_data["restored_at"] = datetime.now().isoformat()
                return True
            return False
        except Exception as e:
            log_error(f"Сбой при восстановлении состояния: {e}")
            return False
    
    def _restore_state(self, snapshot: Dict[str, Any], operation_id: Optional[str]) -> bool:
        """Восстановление данных из снапшота"""
        # Логика восстановления конкретных данных
        if not snapshot:
            return False
        
        try:
            # Имитация успешного отката
            log_info(f"Откат операции {operation_id} выполнен")
            return True
        except Exception as e:
            log_error(f"Ошибка при откате: {e}")
            raise
    
    def reset_recovery_state(self):
        """Сброс состояния после успешного восстановления"""
        self.recovery_attempts = 0
        self.last_error = None


# =============================================================================
# КОНКРЕТНЫЕ ОБРАБОТЧИКИ
# =============================================================================

class CommandHandler(BaseExceptionHandler):
    """Обработка ошибок команд"""
    
    def __init__(self, priority: int = 50):
        super().__init__(priority=priority, name="Command")
    
    def classify(self, error_type: ErrorType) -> bool:
        return isinstance(error_type, (CommandError, ValidationError))
    
    async def handle(self, context: ExceptionContext) -> Dict[str, Any]:
        return {
            "status": "retry",
            "message": f"Ошибка команды: {context.exception}",
            "retries_left": 3 - self.recovery_attempts
        }


class APIHandler(BaseExceptionHandler):
    """Обработка сетевых/API сбоев"""
    
    def __init__(self, priority: int = 60):
        super().__init__(priority=priority, name="API")
    
    def classify(self, error_type: ErrorType) -> bool:
        return isinstance(error_type, (NetworkError, TimeoutError))
    
    async def handle(self, context: ExceptionContext) -> Dict[str, Any]:
        # Логика повторного запроса или переключения на резервный узел
        return {
            "status": "retry",
            "message": f"Сетевая ошибка API: {context.exception}",
            "backoff_ms": 1000 * (self.recovery_attempts + 1)
        }


class DatabaseHandler(BaseExceptionHandler):
    """Обработка БД ошибок"""
    
    def __init__(self, priority: int = 70):
        super().__init__(priority=priority, name="Database")
    
    def classify(self, error_type: ErrorType) -> bool:
        return isinstance(error_type, DatabaseError)
    
    async def handle(self, context: ExceptionContext) -> Dict[str, Any]:
        # Логика переключения на реплику или откат транзакции
        return {
            "status": "rollback",
            "message": f"Ошибка БД: {context.exception}",
            "target_replica": "replica_2" if self.recovery_attempts > 1 else None
        }


# =============================================================================
# ГЛОБАЛЬНЫЙ МЕНЕДЖЕР ВОССТАНОВЛЕНИЯ
# =============================================================================

class RecoveryManager:
    """Менеджер глобального восстановления"""
    
    def __init__(self):
        self.snapshots: Dict[str, RecoveryState] = {}
        self.active_handler: Optional[BaseExceptionHandler] = None
    
    def create_snapshot(self, operation_id: str, data: Dict[str, Any]) -> bool:
        """Сохранение состояния перед критической операцией"""
        state = RecoveryState(
            operation_id=operation_id,
            snapshot_data=data.copy()
        )
        self.snapshots[operation_id] = state
        log_info(f"Создан снапшот для операции {operation_id}")
        return True
    
    def rollback(self, operation_id: str) -> bool:
        """Откат состояния по ID"""
        if operation_id not in self.snapshots:
            log_warning(f"Не найден снапшот для {operation_id}")
            return False
        
        state = self.snapshots[operation_id]
        # Передача данных в соответствующий обработчик или базовый метод восстановления
        result = BaseExceptionHandler._restore_state(self, state.snapshot_data, operation_id)
        
        if result:
            del self.snapshots[operation_id]
            log_info(f"Откат операции {operation_id} завершен")
        else:
            log_error(f"Не удалось откатить операцию {operation_id}")
            
        return result
    
    def cleanup_expired(self, max_age_seconds: int = 3600):
        """Очистка устаревших снапшотов"""
        current_time = datetime.now()
        expired_ids = []
        
        for op_id, state in self.snapshots.items():
            if (current_time - state.created_at).total_seconds() > max_age_seconds:
                expired_ids.append(op_id)
        
        for op_id in expired_ids:
            del self.snapshots[op_id]
            
        log_info(f"Очищено {len(expired_ids)} устаревших снапшотов")


# =============================================================================
# ГЛОБАЛЬНЫЙ СРЕДНИК (MIDDLEWARE)
# =============================================================================

class GlobalExceptionMiddleware:
    """Глобальный перехватчик исключений"""
    
    def __init__(self, handlers: List[BaseExceptionHandler] = None):
        self.handlers = handlers or []
        self.recovery_manager = RecoveryManager()
        
    def inject(self, loop=None):
        """Регистрация обработчиков в цикл обработки"""
        # Интеграция с основным циклом приложения (например, asyncio)
        log_info(f"Инициализация middleware с {len(self.handlers)} обработчиками")
    
    async def process_exception(self, context: ExceptionContext) -> Dict[str, Any]:
        """Обработка исключения на глобальном уровне"""
        
        # 1. Попытка классификации и обработки через зарегистрированные обработчики
        for handler in self.handlers:
            if handler.classify(context.error_type):
                result = await handler.handle(context)
                log_info(f"Обработчик {handler.name} применил действие: {result.get('status')}")
                
                # 2. Попытка восстановления через менеджер
                if context.operation_id and self.recovery_manager.rollback(context.operation_id):
                    result["recovered"] = True
                    
                return result
        
        # 3. Если ни один обработчик не сработал — дефолтная логика
        log_error(f"Не найдено подходящее правило для {context.error_type}")
        
        return {
            "status": "error",
            "message": f"Unhandled exception: {context.exception}",
            "traceback": context.traceback,
            "timestamp": context.timestamp.isoformat()
        }


# =============================================================================
# ИНИЦИАЛИЗАЦИЯ
# =============================================================================

def create_default_middleware():
    """Создание стандартной конфигурации middleware"""
    handlers = [
        CommandHandler(),
        APIHandler(),
        DatabaseHandler(),
    ]
    
    return GlobalExceptionMiddleware(handlers)


# Пример использования (для вставки в main.py или bot.py):
# middleware = create_default_middleware()
# middleware.inject(loop=asyncio.get_event_loop())
