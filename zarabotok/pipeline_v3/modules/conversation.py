"""Conversation service для pipeline_v3 (§9 ТЗ fusion-response).

Фокус: threading сообщений, связывание входящих с заказом,
классификация ответов заказчика, очередь needs_linking.

Не изменяет listener.py, tg_common.py, modules/sender.py —
используется как независимый сервис (импорт по требованию).
"""
import difflib
import os
import re
from typing import List, Optional, Dict, Any, Tuple

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ------------------------------------------------------------------
# Классификация ответов (§9.2)
# ------------------------------------------------------------------
RESPONSE_TYPES = (
    "interested",
    "spec_sent",
    "terms_agreed",
    "rejected",
    "suspicious",
    "free_test_request",
)

INTERESTED_MARKERS = (
    "интерес", "заинтерес", "давайте", "делаем", "работаем",
    "готов", "приступ", "начнем", "начнём", "ок", "хорошо",
    "подходит", "согласен", "согласна", "давай",
)

SPEC_SENT_MARKERS = (
    "тз", "техническое задание", "специфика", "спец", "spec", "описание",
    "объём", "объем", "требования", "условия", "детали",
)

TERMS_AGREED_MARKERS = (
    "утверждаю", "одобрено", "подтверждаю", "принимаю условия",
    "договорились", "по рукам", "готов подписать",
)

REJECTED_MARKERS = (
    "отказ", "не подходит", "передумал", "не интересно", "не нужно",
    "уже нашли", "другой исполнитель", "отменяю",
)

SUSPICIOUS_MARKERS = (
    "казино", "крипто", "обменник", "anydesk", "rustdesk", "дроп",
    "вложен", "выигрыш", "бонус", "лотере", "быстрый заработок",
    "пассивный доход", "без опыта", "за грамм",
)

FREE_TEST_MARKERS = (
    "бесплатн", "тест", "пробн", "бесплатный тест",
    "без оплаты", "free test", "пробный период",
)


class Conversation:
    """Единый объект диалога с threading по Message-ID / In-Reply-To / References."""

    def __init__(self, msg_id: Optional[str] = None):
        self.msg_id: Optional[str] = msg_id or self._generate_msg_id()
        self.in_reply_to: Optional[str] = None
        self.references: List[str] = []
        self.messages: List[Dict[str, Any]] = []
        self.needs_linking: List[Dict[str, Any]] = []
        self.linked_order: Optional[str] = None
        self.link_method: Optional[str] = None  # chat_id | email_thread | proposal_id | contact | semantic

    # ------------------------------------------------------------------
    # Threading
    # ------------------------------------------------------------------
    @staticmethod
    def _generate_msg_id() -> str:
        import uuid
        return str(uuid.uuid4())[:16]

    def add_reference(self, msg_id: str) -> None:
        if msg_id and msg_id not in self.references:
            self.references.append(msg_id)

    def set_in_reply_to(self, msg_id: str) -> None:
        self.in_reply_to = msg_id
        self.add_reference(msg_id)

    def extract_thread_ids(self, raw_msg: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], List[str]]:
        """Извлекает Message-ID, In-Reply-To, References из сырого сообщения."""
        msg_id = raw_msg.get("message_id") or raw_msg.get("msg_id") or raw_msg.get("id")
        in_reply = raw_msg.get("in_reply_to") or raw_msg.get("in_reply_to")
        refs_raw = raw_msg.get("references") or raw_msg.get("references", [])
        refs = refs_raw if isinstance(refs_raw, list) else ([refs_raw] if refs_raw else [])
        # Если References — строка с пробелами
        if isinstance(refs_raw, str) and refs_raw:
            refs = refs_raw.split()
        return (msg_id, in_reply, refs)

    def build_thread_key(self, msg_id: Optional[str] = None, in_reply_to: Optional[str] = None) -> str:
        """Строит ключ треда из Message-ID и In-Reply-To."""
        base = msg_id or self.msg_id or ""
        reply = in_reply_to or self.in_reply_to or ""
        refs = ",".join(self.references)
        return f"{base}|{reply}|{refs}"

    # ------------------------------------------------------------------
    # Связь входящих с заказом
    # ------------------------------------------------------------------
    def link_by_chat_id(self, msg: Dict[str, Any], order_url: Optional[str] = None) -> Optional[str]:
        chat_id = msg.get("chat_id") or msg.get("peer", "") or msg.get("sender", "")
        if chat_id and isinstance(chat_id, str):
            chat_id = chat_id.lower()
        # Простая нормализация: если chat_id содержит url или известен из store
        if order_url:
            self.linked_order = order_url
            self.link_method = "chat_id"
            return order_url
        # Попытка найти заказ через импорт chat (без изменения интерфейсов)
        try:
            from modules import chat as chat_mod
            if chat_id:
                found = chat_mod.find_order_for_peer(chat_id)
                if found:
                    self.linked_order = found
                    self.link_method = "chat_id"
                    return found
        except Exception:
            pass
        # Фолбэк: если chat_id содержит ссылку на заказ
        import re
        url_match = re.search(r"https?://[^\s]+", str(chat_id))
        if url_match:
            url = url_match.group(0)
            self.linked_order = url
            self.link_method = "chat_id"
            return url
        return None

    def link_by_email_thread(self, msg: Dict[str, Any], order_url: Optional[str] = None) -> Optional[str]:
        """Привязка по email-thread (In-Reply-To / References)."""
        _, in_reply, refs = self.extract_thread_ids(msg)
        # Пробуем найти заказ по ссылкам в тексте или контактам
        if order_url:
            self.linked_order = order_url
            self.link_method = "email_thread"
            return order_url
        # Фолбэк на контакт из текста
        text = msg.get("text", "")
        contact = self._extract_contact(text)
        if contact:
            try:
                from modules import chat as chat_mod
                found = chat_mod.find_order_for_peer(contact)
                if found:
                    self.linked_order = found
                    self.link_method = "email_thread"
                    return found
            except Exception:
                pass
        # По references / in_reply_to — если содержит url
        combined = f"{in_reply or ''} {' '.join(str(r) for r in refs)}"
        url_match = re.search(r"https?://[^\s]+", combined)
        if url_match:
            url = url_match.group(0)
            self.linked_order = url
            self.link_method = "email_thread"
            return url
        return None

    def link_by_proposal_id(self, msg: Dict[str, Any], proposal_id: Optional[str] = None, order_url: Optional[str] = None) -> Optional[str]:
        prop_id = proposal_id or msg.get("proposal_id") or msg.get("proposal", "")
        if prop_id:
            # Пробуем связать с заказом по url из proposal (если хранится в jobs/outbox)
            try:
                from modules import store
                jobs = store.load("jobs", {"items": []}).get("items", [])
                for j in jobs:
                    if prop_id in (j.get("url", "") or j.get("id", "")):
                        self.linked_order = j.get("url")
                        self.link_method = "proposal_id"
                        return j.get("url")
                outbox = store.load("outbox", {"items": []}).get("items", [])
                for o in outbox:
                    if prop_id in (o.get("url", "") or o.get("id", "")):
                        self.linked_order = o.get("url")
                        self.link_method = "proposal_id"
                        return o.get("url")
            except Exception:
                pass
        if order_url:
            self.linked_order = order_url
            self.link_method = "proposal_id"
            return order_url
        return None

    def link_by_contact(self, msg: Dict[str, Any], order_url: Optional[str] = None) -> Optional[str]:
        contact = msg.get("contact") or msg.get("sender", "") or msg.get("peer", "")
        if order_url:
            self.linked_order = order_url
            self.link_method = "contact"
            return order_url
        if contact:
            try:
                from modules import chat as chat_mod
                found = chat_mod.find_order_for_peer(str(contact))
                if found:
                    self.linked_order = found
                    self.link_method = "contact"
                    return found
            except Exception:
                pass
        return None

    def link_by_semantic_similarity(self, msg: Dict[str, Any], order_url: Optional[str] = None, threshold: float = 0.65) -> Optional[str]:
        text = msg.get("text", "")
        if order_url:
            self.linked_order = order_url
            self.link_method = "semantic"
            return order_url
        if text:
            try:
                from modules import store
                jobs = store.load("jobs", {"items": []}).get("items", [])
                best_url = None
                best_score = 0.0
                for j in jobs:
                    jtext = (j.get("title", "") + " " + j.get("description", "")).lower()
                    score = self._similarity(text.lower(), jtext)
                    if score > best_score:
                        best_score = score
                        best_url = j.get("url")
                if best_url and best_score >= threshold:
                    self.linked_order = best_url
                    self.link_method = "semantic"
                    return best_url
            except Exception:
                pass
        return None

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        return difflib.SequenceMatcher(None, a, b).ratio()

    @staticmethod
    def _extract_contact(text: str) -> Optional[str]:
        import re
        m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
        if m:
            return m.group(0)
        tg_match = re.search(r"(?:@|t\.me/)([a-zA-Z0-9_]{4,32})", text)
        if tg_match:
            return "@" + tg_match.group(1).lower()
        return None

    # ------------------------------------------------------------------
    # Классификация ответов (§9.2)
    # ------------------------------------------------------------------
    def classify_response(self, text: str) -> str:
        low = (text or "").lower()
        # Сначала исключаем скам / подозрительное
        if any(m in low for m in SUSPICIOUS_MARKERS):
            return "suspicious"
        # Бесплатный тест
        if any(m in low for m in FREE_TEST_MARKERS):
            return "free_test_request"
        # Отказ
        if any(m in low for m in REJECTED_MARKERS):
            return "rejected"
        # Условия согласованы
        if any(m in low for m in TERMS_AGREED_MARKERS):
            return "terms_agreed"
        # Спецификация отправлена
        if any(m in low for m in SPEC_SENT_MARKERS):
            return "spec_sent"
        # Заинтересован (остальное позитивное)
        if any(m in low for m in INTERESTED_MARKERS):
            return "interested"
        # Если текст очень короткий или пустой — не классифицируем как интерес
        if len((text or "").strip()) < 3:
            return "rejected"  # или можно вернуть None; оставим rejected для безопасности
        return "interested"

    # ------------------------------------------------------------------
    # Связывание (единый метод)
    # ------------------------------------------------------------------
    def link_message(self, msg: Dict[str, Any], order_url: Optional[str] = None) -> Optional[str]:
        """Пытается связать входящее сообщение с заказом всеми доступными способами."""
        methods = [
            lambda: self.link_by_chat_id(msg, order_url),
            lambda: self.link_by_email_thread(msg, order_url),
            lambda: self.link_by_proposal_id(msg),
            lambda: self.link_by_contact(msg, order_url),
            lambda: self.link_by_semantic_similarity(msg, order_url),
        ]
        for method in methods:
            result = method()
            if result:
                # Если результат отличается от order_url — обновляем
                if not order_url or result == order_url:
                    return result
        # Если ничего не найдено — добавляем в needs_linking
        if msg not in self.needs_linking:
            self.needs_linking.append(msg)
        return None

    # ------------------------------------------------------------------
    # Очередь needs_linking
    # ------------------------------------------------------------------
    def pop_needs_linking(self, index: int = 0) -> Optional[Dict[str, Any]]:
        if 0 <= index < len(self.needs_linking):
            return self.needs_linking.pop(index)
        return None

    def clear_needs_linking(self) -> None:
        self.needs_linking.clear()

    # ------------------------------------------------------------------
    # Утилиты для проверки целостности
    # ------------------------------------------------------------------
    def is_linked(self) -> bool:
        return bool(self.linked_order)

    def thread_summary(self) -> Dict[str, Any]:
        return {
            "msg_id": self.msg_id,
            "in_reply_to": self.in_reply_to,
            "references": self.references,
            "linked_order": self.linked_order,
            "link_method": self.link_method,
            "messages_count": len(self.messages),
            "needs_linking_count": len(self.needs_linking),
        }

    def accept_inbox(self, messages: List[Dict[str, Any]]) -> List[str]:
        """P0 W3 — Accept inbox messages with threading (listener integration).
        Processes Message-ID / In-Reply-To / References and links to thread."""
        keys = []
        for msg in messages:
            msg_id, in_reply, refs = self.extract_thread_ids(msg)
            if msg_id:
                self.msg_id = msg_id
            if in_reply:
                self.set_in_reply_to(in_reply)
            for r in refs:
                self.add_reference(r)
            # Link to order if present
            if msg.get("order_url") or msg.get("url"):
                self.link_message(msg, order_url=msg.get("order_url") or msg.get("url"))
            else:
                # General link attempt
                self.link_message(msg)
            keys.append(self.build_thread_key())
            self.messages.append(msg)
        return keys


# ------------------------------------------------------------------
# Глобальный хелпер для быстрого доступа из listener / tg_scrape
# ------------------------------------------------------------------
_conversation_cache: Dict[str, Conversation] = {}


def get_conversation(key: Optional[str] = None) -> Conversation:
    """Возвращает Conversation по ключу (msg_id / chat_id / email thread)."""
    k = key or "default"
    if k not in _conversation_cache:
        _conversation_cache[k] = Conversation()
    return _conversation_cache[k]


def reset_cache() -> None:
    _conversation_cache.clear()


# ------------------------------------------------------------------
# Проверка синтаксиса при импорте
# ------------------------------------------------------------------
if __name__ == "__main__":
    # Базовая самопроверка
    c = Conversation()
    msg = {
        "message_id": "msg_123",
        "in_reply_to": "msg_122",
        "references": ["msg_122"],
        "chat_id": "tg:user1",
        "text": "Интересно, давайте обсудим спецификацию",
    }
    c.extract_thread_ids(msg)
    c.set_in_reply_to("msg_122")
    c.add_reference("msg_122")
    print("Thread key:", c.build_thread_key())
    cls = c.classify_response("Спецификацию отправил, когда можно начать?")
    print("Classified:", cls)
    assert cls == "spec_sent"
    # Связывание
    result = c.link_message({"text": "Привет, интересное предложение", "sender": "@user"}, order_url="https://example.com/order")
    assert c.is_linked()
    print("Link result:", result)
    print("Summary:", c.thread_summary())
