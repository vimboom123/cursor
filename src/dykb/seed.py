"""内置示例口播：用方法论文案演示知识库，不夹带真实抖音视频文件。"""

from __future__ import annotations

from dykb.pipeline import ingest
from dykb.store import Store

SAMPLES = [
    {
        "title": "抖音口播怎么建成知识库",
        "author": "口播库示例",
        "tags": ["方法", "知识库", "短视频"],
        "collection": "方法示例",
        "source_url": "",
        "transcript": """
把抖音视频建成知识库，核心不是去爬别人的作品，而是把你已经有权使用的口播，变成可检索的卡片。
第一点，只入库自己的作品、客户授权的素材，或者团队内部培训视频。
第二点，一条视频要拆成四层信息：标题话题、口播语音、画面字幕、你自己补的笔记。
第三点，先拿到文案。创作者可以在剪映导出字幕，或把作品保存到相册后再转写。
然后把文案按句子切开，每段带上时间戳，这样追问时能回到原片位置。
知识卡片是指从口播里抽出的观点、步骤、金句和术语，而不是整段流水账。
记住：分享链接只用来引用编号，不要用非官方解析接口去下载别人的视频。
重点是先检索、再追问。检索找到原句，追问把多条口播拼成答案。
""",
    },
    {
        "title": "一周复盘四步法",
        "author": "口播库示例",
        "tags": ["复盘", "效率"],
        "collection": "方法示例",
        "source_url": "",
        "transcript": """
一周复盘可以压成四步，适合做成口播也适合写进知识库。
第一步，只看结果：这一周真正交付了什么，不要先讲情绪。
第二步，找偏差：计划和实际差在哪里，是范围、时间还是质量。
第三步，归因到动作，而不是性格。是沟通晚了，还是验收标准没写清。
第四步，下周只改一个动作。记住：一次改太多等于没改。
复盘卡片是指「动作 → 结果 → 下一次实验」，不要写成检讨书。
""",
    },
    {
        "title": "用户访谈怎么提问才不踩坑",
        "author": "口播库示例",
        "tags": ["访谈", "调研"],
        "collection": "方法示例",
        "source_url": "",
        "transcript": """
用户访谈最怕一上来就问你喜欢哪个功能。
首先问最近一次真实发生的事，让对方讲经过，而不是讲评价。
其次追问卡点：当时差一点点就放弃的地方在哪。
然后把对方的原话记下来，这些原话就是知识库里的金句。
「不要替用户总结，先把原话存进知识库」是访谈的铁律。
术语「工作-to-be-done」是指用户雇产品完成的那件任务，不是产品功能清单。
""",
    },
]


def seed_examples(store: Store) -> int:
    added = 0
    existing_titles = {v.title for v in store.list_videos()}
    for sample in SAMPLES:
        if sample["title"] in existing_titles:
            continue
        ingest(
            store,
            title=sample["title"],
            transcript=sample["transcript"],
            author=sample["author"],
            tags=sample["tags"],
            collection=sample["collection"],
            source_url=sample.get("source_url", ""),
        )
        added += 1
    return added
