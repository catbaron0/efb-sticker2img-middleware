# coding: utf-8
import io
import os
import logging
from typing import IO, Any, Dict, Optional, List, Tuple
from tempfile import NamedTemporaryFile

from ehforwarderbot import EFBMiddleware, EFBMsg, MsgType
from . import __version__ as version
from PIL import Image

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

    middleware_id = "catbaron.sticker2img"
    middleware_name = "Sticker2Image"
    __version__ = version.__version__
    logger: logging.Logger = logging.getLogger("plugins.%s.MessageBlockerMiddleware" % middleware_id)


    def __init__(self, instance_id=None):
        super().__init__()
        self.types = {'image', 'audio', 'file', 'link', 'location', 'status', 'sticker', 'text', 'video', 'unsupported'}
        self.filters = dict()

    def sent_by_master(self, message: EFBMsg) -> bool:
        author = message.author
        if author and author.module_id and author.module_id == 'blueset.telegram':
            return True
        else:
            return False

    def process_message(self, message: EFBMsg) -> Optional[EFBMsg]:
        """
        Process a message with middleware

        Args:
            message (:obj:`.EFBMsg`): Message object to process

        Returns:
            Optional[:obj:`.EFBMsg`]: Processed message or None if discarded.
        """
        if not self.sent_by_master(message):
            return message
        fn = message.filename
        if not (message.type == MsgType.Sticker or (fn and (fn.endswith('.png') or fn.endswith('.gif')))):
            return message
        filename = message.filename
        self.logger.info(f"Converting {filename} to JPEG...")
        sticker = Image.open(message.file.file.raw)
        img = Image.new("RGB", sticker.size, (256, 256, 256))
        img.paste(sticker, sticker)

        # Create a new file 
        message.file.close()
        message.file = NamedTemporaryFile(suffix='.jpg')
        message.filename = os.path.basename(message.file.name)
        img_data = io.BytesIO()
        img.save(img_data, format='jpeg')
        message.file.write(img_data.getvalue())
        message.file.file.seek(0)

        message.type = MsgType.Image
        message.mime = 'image/jpeg'
        message.path = message.file.name
        return message
