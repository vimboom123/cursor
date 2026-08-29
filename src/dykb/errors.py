"""入库错误。抖音分享链接不会被拿去拉流。"""

from __future__ import annotations

DOUYIN_LINK_HELP = """抖音分享链接拿不到口播正文。

链接里只有作品编号。口播在音轨里，字幕在剪映/创作者侧；
开放平台的 video.data 也只返回标题、封面和播放数，没有转写。

请改用下面任一方式：
1. 剪映导出 SRT 或口播稿，粘贴/上传后入库
2. 自己的作品保存到相册，再上传视频（可本机转写）
3. 把已授权的 .srt / .txt / .mp4 放到你自己的网盘直链，填「文件链接」

不要用第三方「解析接口」去水印或跟跳短链，那是违约抓取。"""


class IngestError(ValueError):
    pass


class DouyinLinkError(IngestError):
    def __init__(self, url: str = "") -> None:
        self.url = url
        super().__init__(DOUYIN_LINK_HELP)


class FetchError(IngestError):
    pass
