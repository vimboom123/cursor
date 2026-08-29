from dykb.chunk import segments_from_plain
from dykb.knowledge import extract_cards


def test_extracts_steps_terms_and_warnings() -> None:
    text = """
第一点，只入库自己的作品。
知识卡片是指从口播抽出的观点。
记住：分享链接只用来引用。
「不要替用户总结」是访谈铁律。
"""
    segs = segments_from_plain("v1", text, 8000)
    cards = extract_cards("v1", segs)
    kinds = {c.kind for c in cards}
    assert "step" in kinds
    assert "term" in kinds
    assert "warning" in kinds
    bodies = " ".join(c.body for c in cards)
    assert "知识卡片" in bodies
