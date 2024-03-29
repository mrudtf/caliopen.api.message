from datetime import datetime
import logging

from cornice.resource import resource, view

from caliopen.base.message.core import (
    RawMessage,
    Message as CoreMessage,
    ReturnIndexMessage)
from caliopen.base.message.parameters import NewMessage
from caliopen.api.base import Api

log = logging.getLogger(__name__)


@resource(collection_path='/threads/{thread_id}/messages',
          path='/threads/{thread_id}/messages/{message_id}')
class Message(Api):

    def __init__(self, request):
        self.request = request
        self.user = request.authenticated_userid

    def extract_recipients(self):
        """Get recipients from request"""
        recipients = {}
        for rec_type in ['to_recipients', 'cc_recipients', 'bcc_recipients']:
            addrs = []
            for rec in self.request.json.get(rec_type, []):
                addrs.append((rec['contact'], rec['address']))
            recipients[rec_type] = addrs
        recipients['from'] = [(self.user.user_id, self.user.user_id)]
        return recipients

    @view(renderer='json', permission='authenticated')
    def collection_get(self):
        thread_id = self.request.matchdict.get('thread_id')
        messages = CoreMessage.by_thread_id(self.user, thread_id,
                                            limit=self.get_limit(),
                                            offset=self.get_offset())
        results = []
        for msg in messages.get('data', []):
            results.append(ReturnIndexMessage.build(msg).serialize())
        return {'messages': results, 'total': messages['total']}

    @view(renderer='json', permission='authenticated')
    def collection_post(self):
        thread_id = self.request.matchdict.get('thread_id')
        reply_to = self.request.json.get('reply_to')
        if reply_to:
            parent = CoreMessage.get(self.user, reply_to)
            parent_message_id = parent.external_id
            thread_id = parent.thread_id
            sec_level = parent.security_level
        else:
            parent_message_id = None
            thread_id = None
            # XXX : how to compute ?
            sec_level = 0
        recipients = self.extract_recipients()
        # XXX : make recipient for UserMessage using Recipient class
        subject = self.request.json.get('subject')
        text = self.request.json.get('text')
        tags = self.request.json.get('tags', [])
        new_msg = NewMessage(recipients,
                             subject=subject,
                             text=text, tags=tags,
                             date=datetime.utcnow(),
                             security_level=sec_level,
                             thread_id=thread_id,
                             parent_message_id=parent_message_id)
        msg = CoreMessage.create(self.user, new_msg)
        idx_msg = CoreMessage.get(self.user, msg.message_id)
        log.info('Post new message %r' % msg.message_id)
        # XXX return redirect to newly created message ?
        return idx_msg


@resource(path='/raws/{raw_id}')
class Raw(Api):

    def __init__(self, request):
        self.request = request
        self.user = request.authenticated_userid

    @view(renderer='text_plain', permission='authenticated')
    def get(self):
        raw_id = self.request.matchdict.get('raw_id')
        raw = RawMessage.get(self.user, raw_id)
        return raw.data
