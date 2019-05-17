Sticker2Img: A middleware for EFB
=================================

Notice
------

**Middleware ID**: ``catbaron.sticker2img``

**Sticker2Img** is a middleware for EFB, to convert stickers and ``gif``
files to ``jpeg`` images, if it is sent from master to slave channel.
This middleware should solve this
`issue <https://github.com/blueset/efb-wechat-slave/issues/48#issue-439681479>`__.

If a message has a attatched file with a ``.png`` or ``.gif`` suffix, or
if the message type is ``sticker``, the attatched file would be
converted to ``jpeg`` image. Note that the converted ``jpeg`` file may
be in low quality.

Also be aware that this is a very early develop version. Please let me
know if you found any problem.

You need to use **MessageBlocker** on top of
`EFB <https://ehforwarderbot.readthedocs.io>`__. Please check the
document and install EFB first.

Dependense
----------

-  Python >=3.6
-  EFB >=2.0.0b15
-  pillow

Install
-------

-  Install

   ::

       git clone https://github.com/catbaron0/efb-sticker2img-middleware
       cd efb-sticker2img-middleware
       python setup.py install

-  Register to EFB Following `this
   document <https://ehforwarderbot.readthedocs.io/en/latest/getting-started.html>`__
   to edit the config file. The config file by default is
   ``~/.ehforwarderbot/profiles/default``. It should look like:

::

    master_channel: foo.demo_master
    slave_channels:
    - foo.demo_slave
    - bar.dummy
    middlewares:
    - foo.other_middlewares
    - catbaron.sticker2img

You only need to add the last line to your config file.

-  Restart EFB.
