"""P0 W3 — Conversation / Listener / Threading bridge.
Integrates modules/conversation.py with modules/listener.py (poll_telegram, poll_email_tz)
and threading (Message-ID / In-Reply-To / References).
Files: conversation.py (updated), listener.py (poll sources), listener_bridge.py (this)
References: WORKFLOW.md §20, modules/conversation.py lines 61-352.
"""
import time
from typing import Dict, Any, List, Optional

logger = __import__("logging").getLogger(__name__)

try:
    from modules import conversation as conv_mod
    from modules import listener as ls
    from modules import store
except Exception as e:
    logger.warning("listener_bridge: import error %s", e)
    conv_mod = None
    ls = None
    store = None

class ListenerBridge:
    """Bridge listener inbox/thread results into Conversation threading."""

    def __init__(self, source: str = "tg"):
        self.source = source  # "tg" | "email"
        self.conversations: Dict[str, Any] = {}

    def poll_and_link(self, limit: int = 60) -> int:
        """Poll listener source, feed messages into conversation threading, return count linked."""
        linked = 0
        if self.source == "tg" and ls:
            try:
                count = ls.poll_telegram(mark_seen=True, limit=limit)
            except Exception as e:
                logger.warning("listener_bridge: poll_telegram error %s", e)
                count = 0
            # After poll, read threads from store to link via conversation
            if store and conv_mod:
                threads = store.load("threads", {"items": []}).get("items", [])
                for msg in threads[-limit:]:
                    key = self._link_message(msg)
                    if key:
                        linked += 1
            return linked
        elif self.source == "email" and ls:
            try:
                count = ls.poll_email_tz(limit=limit)
            except Exception as e:
                logger.warning("listener_bridge: poll_email_tz error %s", e)
                count = 0
            # Email threading via conversation link_by_email_thread
            if conv_mod:
                # Placeholder: in production, load email messages from store/email index
                pass
            return linked
        return linked

    def _link_message(self, msg: Dict[str, Any]) -> Optional[str]:
        if not conv_mod:
            return None
        # Use Conversation threading: build_thread_key + link_message
        conv = conv_mod.get_conversation()
        # Accept raw message with threading headers
        msg_id = msg.get("msg_id") or msg.get("message_id")
        if msg_id and msg.get("in_reply_to"):
            conv.set_in_reply_to(msg.get("in_reply_to"))
        key = conv.link_message(msg)
        if key:
            self.conversations[key] = conv
        return key

    def accept_inbox(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Explicit inbox ingestion (for integration with listener or chat pipeline).
        Updates conversation threading for each message."""
        keys = []
        if not conv_mod:
            return keys
        for msg in messages:
            key = self._link_message(msg)
            if key:
                keys.append(key)
        return keys

    def get_thread_summaries(self) -> List[Dict[str, Any]]:
        summaries = []
        for key, conv in self.conversations.items():
            if hasattr(conv, "thread_summary"):
                summaries.append(conv.thread_summary())
        return summaries

# ---------- Convenience functions ----------

def bridge_poll(source: str = "tg", limit: int = 60) -> int:
    return ListenerBridge(source=source).poll_and_link(limit=limit)

def bridge_inbox(messages: List[Dict[str, Any]], source: str = "tg") -> List[str]:
    return ListenerBridge(source=source).accept_inbox(messages)
