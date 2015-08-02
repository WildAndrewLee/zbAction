import json
import traceback

from tornado import websocket

from shared import *

from helpers import get_unread
from logger import log
from models.action import Action
from models.forum import Forum
from models.mod import Mod
from models.user import User

class SocketHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        # Do nothing. The handler will
        # be added to the list if it receives
        # a proper handshake.
        #
        # Eventually though, we want to be able
        # to verify sending domains.
        pass

    def handshake(self, user, key, mod_key):
        # Check for disabled boards.
        board = Forum.from_key(user['board_key'])

        if board is None or board is not None and board.enabled == False:
            return

        # Only one handshake per connection.
        if hasattr(self, 'user'):
            return

        name = user['name']
        user = User.create_from(user)

        user.name = name
        user.save()

        # if the above passes this is a handshake
        setattr(self, 'user', user)
        
        conn_mutex.acquire()
        connections.append((self.user.toKey(), self))
        conn_mutex.release()

        # Send API key.

        handshake = Action(
            event='handshake',
            details=self.user.access_key,
            source=self.user.access_key,
            receiver=self.user.access_key
        )

        self.push_action(handshake, self.user.access_key, 0)

    def push_action(self, action, key, mod_key):
        if not self.user or not self.user.validate_key(key):
            return

        if not Mod.key_exists(mod_key):
            log('Attempted to use invalid modification key:', mod_key)
            return

        action = Action.create_from(action)
        receiver = User.from_access_key(action.receiver)

        # Check for cross-board requests
        if self.user.board_key != receiver.board_key:
            log('Attempted to send cross-board request:', self.user.board_key, receiver.board_key)
            return

        action_mutex.acquire()
        action_queue.append(action)
        action_mutex.release()

    def get_unread(self, user, key, mod_key):
        # fetch all missed notifications and send
        # them to the user. this may take a while
        # so maybe we should store any missed
        # notifications inside a separate dict
        # and fetch from that instead. of course we
        # should probably prune any notifications
        # more than a week old so we don't just use
        # up all our RAM.

        for action in get_unread(self.user):
            self.push_action(action, self.user.access_key, 0)

    def on_message(self, message):
        try:
            log('Received:', message)

            message = json.loads(message)

            # A dict of message handlers.
            handlers = {
                'handshake': self.handshake,
                'get_unread': self.get_unread,
                'action': self.push_action
            }

            handler = handlers[message['type']]
            mod_key = message['mod_key'] if 'mod_key' in message else None

            handler(message['data'], message['key'], mod_key)
        except:
            # any of the above causing an error
            # means something wrong happened
            # and we should ignore. log the error
            # anyway in case.
            traceback.print_exc()

    def on_close(self):
        if 'user' in self.__dict__:
            conn_mutex.acquire()
            connections.remove((self.toKey(), self))
            conn_mutex.release()

            log('Disconnected from user:', self.toKey())

    def toKey(self):
        return self.user.toKey()    