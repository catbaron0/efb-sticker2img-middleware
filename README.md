# Sticker2Img: A middleware for EFB 

## Notice

**Middleware ID**: `catbaron.sticker2img`

**Sticker2Img** is a middleware for EFB, to convert stickers and `gif` file to `jpeg` image, if it is sent from master to slave channel. This middleware should solve this [issue](https://github.com/blueset/efb-wechat-slave/issues/48#issue-439681479). 

If a message has a attatched file whose a `.png` or `.gif` suffix, or if the message type is `sticker`, the attatched file would be converted to `jpeg` image. 
Note that the converted `jpeg` file may be in low quality.

Also be aware that this is a very early develop version. Please let me know if you found any problem.

You need to use **MessageBlocker** on top of [EFB](https://ehforwarderbot.readthedocs.io). Please check the document and install EFB first.

## Dependense

* Python >=3.6
* EFB >=2.0.0
* pillow

## Install

```
git clone https://github.com/catbaron/efb-sticker2img-middleware
cd efb-sticker2img-middleware
python setup.py install
```