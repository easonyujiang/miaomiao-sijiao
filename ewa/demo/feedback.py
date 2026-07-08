"""猫咪反馈消息生成

根据答题结果生成妙喵的个性化反馈消息和状态。
"""

from __future__ import annotations


def build_cat_message(
    passed: bool,
    matched: list[str],
    missed: list[str],
    wrong_hits: list[str],
    attempt_num: int,
    step_title: str,
    key_point: str,
) -> str:
    """根据评分结果生成猫咪反馈消息。"""
    if passed:
        if attempt_num == 1:
            return (
                f"完美！第一次就答对了 🌟\n"
                f"核心要点你都掌握了：{matched[0] if matched else '关键要件'}。\n"
                f"小鱼干 +3 🐟"
            )
        else:
            return (
                f"这次过了！{attempt_num}次尝试，坚持就是胜利 ✨\n"
                f"关键是你抓住了：{matched[0] if matched else '核心要件'}。"
            )
    else:
        msg_parts = ["猫猫看了你的答案，差一点点~\n"]
        if wrong_hits:
            msg_parts.append(
                f"⚠️ 注意：{wrong_hits[0]} —— 这个理解有误，要回去看看。\n"
            )
        if missed:
            msg_parts.append("漏掉了关键点：\n")
            for m in missed[:2]:
                msg_parts.append(f"  · {m}\n")
        msg_parts.append(f"\n💡 记住：{key_point}")
        if missed:
            msg_parts.append("\n\n⏪ 猫猫帮你找到了对应片段，点下面跳回去再看一遍 👇")
        return "".join(msg_parts)


def calc_cat_state(session: dict, current_idx: int, total: int) -> str:
    """计算当前猫咪表情状态。

    Returns:
        celebrating | correcting | watching | idle
    """
    if current_idx >= total:
        return "celebrating"
    results = session["step_results"]
    if not results:
        return "idle"
    last = list(results.values())[-1]
    if not last.get("passed") and last.get("attempts", 0) > 0:
        return "correcting"
    return "watching"
