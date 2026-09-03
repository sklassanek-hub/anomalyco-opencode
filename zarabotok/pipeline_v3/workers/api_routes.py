# Transfer route registration (P1 [ ] /transfer endpoint)
# Wires api/transfer_handler.py into the API worker.
# Usage: from workers.api_routes import register_transfer_routes; register_transfer_routes(app)
import os
from api import transfer_handler

def register_transfer_routes(app):
    @app.post('/transfer')
    def _transfer():
        data = app.request.json or {}
        url = data.get('url')
        target_agent = data.get('target_agent')
        reason = data.get('reason', '')
        token = app.request.headers.get('Authorization', '').replace('Bearer ', '')
        result, code = transfer_handler.handle_transfer(url, target_agent, reason, token)
        return app.jsonify(result), code

    @app.get('/transfer/<path:url>')
    def _transfer_status(url):
        from modules import conversation
        links = conversation.list_links(url)
        return app.jsonify({'url': url, 'links': links})
