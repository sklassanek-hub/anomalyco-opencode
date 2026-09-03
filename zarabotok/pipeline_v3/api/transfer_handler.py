
# Agent Transfer Endpoint — orders handoff
# File: zarabotok/pipeline_v3/api/transfer_handler.py
from flask import request, jsonify
import json, os
from modules import conversation, listener_bridge, kill_switch, auth_middleware

def handle_transfer(url, target_agent, reason='', auth_token=None):
    # Auth check
    auth_middleware.init_auth_guard()
    if not auth_token or auth_token != os.environ.get('PIPELINE_AUTH_TOKEN'):
        return {'status':'error','message':'auth_required'}, 401
    # Audit
    kill_switch.write_event({'event':'transfer_request','url':url,'agent':target_agent,'reason':reason})
    # Link to conversation
    link_id = conversation.link_message(url, target_agent, reason)
    return {'status':'ok','url':url,'target_agent':target_agent,'link_id':link_id}
