# coding: utf-8
import json
import io
import logging
import os
import time
from gettext import translation
from typing import IO, Any, Dict, Optional, List, Tuple
from collections import OrderedDict
from .db import DatabaseManager
import re

import yaml
from pyqrcode import QRCode

from ehforwarderbot import EFBChannel, EFBMiddleware, EFBMsg, MsgType, ChannelType, \
    ChatType, EFBStatus, EFBChat, coordinator
from ehforwarderbot import utils as efb_utils
from ehforwarderbot.exceptions import EFBMessageTypeNotSupported, EFBMessageError, EFBChatNotFound, \
    EFBOperationNotSupported
from ehforwarderbot.message import EFBMsgCommands, EFBMsgCommand
from ehforwarderbot.status import EFBMessageRemoval
from ehforwarderbot.utils import extra, get_config_path
from . import __version__ as version
from abc import ABC, abstractmethod

# class WeChatChannel(EFBChannel):
class Sticker2ImgMiddleware(EFBMiddleware):
    """
    EFB Middleware - MessageBlockerMiddleware
    Add and manage filters to block some messages.

    Author: Catbaron <https://github.com/catbaron>
    """
    # author_channel_id: the channel where the msg from
    # author_chat_uid: The user who send the msg. '__self__' if it is sent by you
    # chat_channel_id: the channel where the chat blongs to (wechat for instanfce)
    # chat_chat_uid: the chat where the msg blongs to (the wechat group for instance)

    middleware_id = "catbaron.msg_blocker"
    middleware_name = "Message Blocker Middleware"
    __version__ = version.__version__
    logger: logging.Logger = logging.getLogger("plugins.%s.MessageBlockerMiddleware" % middleware_id)


    def __init__(self, instance_id=None):
        super().__init__()
        self.types = {'image', 'audio', 'file', 'link', 'location', 'status', 'sticker', 'text', 'video', 'unsupported'}
        # self.config: Dict[str: Any] = self.load_config()
        # self.command = self.config.get("command", 'recog`')
        # self.default_lang = self.config.get('language', 'zh')
        self.db = DatabaseManager(self)
        self.filters = dict()
        self.commands = {
                'list': self.cmd_list_filter,
                'add': self.cmd_add_filter,
                'del': self.cmd_del_filter
                }

    def reply_msg(self, message: EFBMsg, text):
        msg: EFBMsg = EFBMsg()
        msg.chat = message.chat
        msg.author = message.author
        msg.author.chat_name = 'Message Blocker'
        msg.deliver_to = coordinator.master
        msg.type = MsgType.Text
        msg.uid = message.uid
        msg.text = text
        return msg

    def cmd_list_filter(self, message: EFBMsg, cmd: str) -> EFBMsg:
        '''list filter for current chat.'''
        filters_data = []
        target = message.target
        self.logger.info("List filters")
        filters = self.get_filters(message)
        if not target:
            for fi in filters:
                filters_data.append(str(fi.__data__))
        else:
            uid = target.author.chat_uid
            for fi in filters:
                if uid == eval(fi.filter_text).get('user', ''):
                    filters_data.append(str(fi.__data__))

        reply_text = '\n'.join(filters_data)
        if not reply_text:
            reply_text = 'No filter was found.'
        msg = self.reply_msg(message, reply_text)
        return msg

    def cmd_add_filter(self, message: EFBMsg, cmd: str) -> EFBMsg:
        cmd = cmd.lower()
        self.logger.info("Add filters")
        self.logger.info("filter_text:", cmd)
        filters = dict()
        if cmd:
            if cmd in self.types:
                filters['type'] = [cmd]
            else:
                self.logger.info("Filters of cmd: %s", cmd)
                filters = eval(cmd)
                if not isinstance(filters, dict):
                    reply_text = f"Failed to add filter. Invalid filter text. "
                    return self.reply_msg(message, reply_text)
            # try:
            #     self.logger.info("Filters of cmd: %s", cmd)
            #     filter_cmd: dict = eval(cmd)
            # except Exception as e:
            #     reply_text = 'Failed to load command text!'
            #     self.logger.info('Failed to load command text (%s): %s', cmd, str(e))
            #     return self.reply_msg(message, '\n'.join(reply_text))
        if message.target:
            self.logger.info("Filters to user: %s", message.target.author.chat_name)
            message.chat.chat_name = message.target.chat.chat_name
            filters['user'] = str(message.target.author.chat_uid)

        if filters:
            filter_text: str = json.dumps(filters)
            self.logger.info("Add filters: %s", filter_text)
            self.db.add_filter(message, filter_text)
            self.update_filters(message)
            # filter_text = self.select_filters(message).where(self.db.Filter.filter_text == filter_text)[0].__data__
            reply_text = f"Filter added: {filter_text}"
        else:
            reply_text = f"Failed to add filter. Filter is empty."
        self.logger.info(reply_text)
        filters.update(filters)
        return self.reply_msg(message, reply_text)

    def cmd_del_filter(self, message: EFBMsg, filter_id: str) -> EFBMsg:
        target = message.target
        author_channel_id: str = message.chat.channel_id
        chat_chat_uid: str = message.chat.chat_uid
        if not filter_id and target:
            filter_data = []
            for fi in self.select_filters(message):
                filter_dict = eval(fi.filter_text)
                if filter_dict.get('user', '') == target.author.chat_uid:
                    filter_data.append(str(fi.__data__))
                    fi.delete_instance()
            reply_text = 'Filter deleted: %s' % '\n'.join(filter_data)
        else:
            self.logger.info('Delete filter')
            filter_id = int(filter_id)
            reply_text = 'Filter deleted: %s' % self.db.Filter.get(id=filter_id).__data__
            self.db.delete_filter(filter_id = filter_id)
        # try:
        #     filter_id = int(filter_id)
        #     reply_text = 'Filter deleted: %s' % self.db.Filter.get(id=filter_id).__data__
        #     self.db.delete_filter(filter_id = filter_id)
        # except Exception as e:
        #     reply_text = 'Failed to delete filter: %s' % str(e)
        #     self.logger.info(reply_text)
        self.logger.info(reply_text)
        self.update_filters(message)
        return self.reply_msg(message, reply_text)

    def select_filters(self, message: EFBMsg):
        filters = None
        author_channel_id: str = message.chat.channel_id
        chat_chat_uid: str = message.chat.chat_uid
        filters = self.db.Filter.select().where(
            self.db.Filter.author_channel_id == author_channel_id,
            self.db.Filter.chat_chat_uid == chat_chat_uid
        )
        return filters

    def update_filters(self, message: EFBMsg):
        self.logger.info('Update filter')
        author_channel_id: str = message.chat.channel_id
        chat_chat_uid: str = message.chat.chat_uid
        filters = self.select_filters(message)
        self.filters[(author_channel_id, chat_chat_uid)] = filters
        # try:
        #     filters = self.db.Filter.select(
        #         self.db.Filter.author_channel_id == author_channel_id,
        #         self.db.Filter.chat_chat_uid == chat_chat_uid
        #         )
        #     self.filters[(author_channel_id, chat_chat_uid)] = filters
        # except Exception as e:
        #     self.logger.info('Update filters failed: %s', str(e))
        return filters

    def get_filters(self, message: EFBMsg):
        key = (message.chat.channel_id,  message.chat.chat_uid)
        return self.filters.get(key, self.update_filters(message))

    def load_config(self):
        config_path = get_config_path(self.middleware_id)
        if not os.path.exists(config_path):
            self.self.logger.info('The configure file does not exist!')
            return
        with open(config_path, 'r') as f:
            d = yaml.load(f)
            if not d:
                self.self.logger.info('Load configure file failed!')
                return
            return d

    def sent_by_me(self, message: EFBMsg) -> bool:
        author = message.author
        if author.channel_id == 'blueset.telegram' and author.chat_uid == '__self__':
            return True
        else:
            return False

    def match_msg(self, message: EFBMsg, filter_dict) -> bool:
        if 'user' not in filter_dict \
                and 'text' not in filter_dict \
                and 'type' not in filter_dict:
            return False

        author = message.author
        chat = message.chat
        match_user, match_text, match_type = True, True, True
        if 'user' in filter_dict:
            if filter_dict['user'] != author.chat_uid:
                match_user = False
        if 'text' in filter_dict:
            k = re.compile(str(filter_dict['text']))
            if not re.search(k, message.text):
                match_text = False
        if 'type' in filter_dict:
            types = filter_dict['type']
            m_type = message.type
            if not('image' in types and m_type == MsgType.Image \
                    or 'audio' in types and m_type == MsgType.Audio \
                    or 'file' in types and m_type == MsgType.File \
                    or 'link' in types and m_type == MsgType.Link \
                    or 'location' in types and m_type == MsgType.Location \
                    or 'status' in types and m_type == MsgType.Status \
                    or 'sticker' in types and m_type == MsgType.Sticker \
                    or 'text' in types and m_type == MsgType.Text \
                    or 'video' in types and m_type == MsgType.Video \
                    or 'unsupported' in types and m_type == MsgType.Unsupported):
                match_type = False
        if match_user:
            # print('user matched')
            self.logger.info('user_id matched')
        if match_type:
            # print('type matched')
            self.logger.info('type matched')
        if match_text:
            # print('text matched')
            self.logger.info('text matched')
        match = match_user and match_text and match_type
        return match

    def process_message(self, message: EFBMsg) -> Optional[EFBMsg]:
        """
        Process a message with middleware

        Args:
            message (:obj:`.EFBMsg`): Message object to process

        Returns:
            Optional[:obj:`.EFBMsg`]: Processed message or None if discarded.
        """
        author, chat, target = message.author, message.chat, message.target
        # print()
        # print()
        # print("message", message.__dict__)
        # print("author:", author.__dict__)
        # print("chat:", chat.__dict__)
        if target:
            # print("target:", target.__dict__)
            # print("target.author:", target.author.__dict__)
            # print("target.target:", target.chat.__dict__)
        msg_text = message.text.strip()
        if self.sent_by_me(message):
            if msg_text.startswith('\\'):
                # command message
                cmd_arg = msg_text[1:].split(' ', 1)
                if len(cmd_arg) > 1:
                    cmd, arg = cmd_arg
                else:
                    cmd, arg = cmd_arg[0], ''
                if cmd in self.commands:
                    return self.commands[cmd](message, arg)
                else:
                    return None
            else:
                # normal message, pass it.
                return message
        # message to be filtered
        matched = False
        for fi in self.get_filters(message):
            filter_dict = eval(fi.filter_text)
            # print('filter:', filter_dict)
            matched = self.match_msg(message, filter_dict)
            if matched:
                break
            # try:
            #     filter_dict = eval(fi.filter_text)
            #     msg_pass = not filter_msg(message, filter_dict)
            # except Exception as e:
            #     self.logger.info("Failed to load filter: %s", str(e))
            #     pass
        if matched == False:
            return message
        else:
            # print('Message blocked!')
            self.logger.info('Message blocked: %s', message.__dict__)
            return None
