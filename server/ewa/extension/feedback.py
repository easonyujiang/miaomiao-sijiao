"""猫咪反馈消息生成

根据答题结果生成妙喵的个性化反馈。
"""

from __future__ import annotations

import random


# 语气词池 —— 小概率穿插，让猫更活
_FILLERS = ["喵~ ", "唔… ", "嗯，", "", "", "", ""]  # 空串占多数，不滥用

# 正确 — 首次通过
_PASS_FIRST = [
    "答对了！{matched}——记住这个就行。",
    "没错。{matched}，关键就是这个。",
    "一次过。{matched}，看来你是真看懂了。",
]

# 正确 — 重试后通过
_PASS_RETRY = [
    "这次对了。{matched}，{attempts}次搞明白也不亏。",
    "过了。关键在于{matched}，下次别再被{wrong}绕进去了。",
    "终于对了。记住{matched}就够了。",
]

# 错误 — 有错误理解
_FAIL_WRONG = [
    "不对。{wrong}这个理解是错的，回去看看{key_point}。",
    "偏了。{wrong}——不是这个方向，{key_point}才是对的。",
    "搞反了。{wrong}不成立，核心是{key_point}。",
]

# 错误 — 漏了要点
_FAIL_MISS = [
    "还差一点。漏了{missed}，{key_point}。",
    "不够全。{missed}没提到，记住：{key_point}。",
    "少了关键。{missed}——这才是核心，补上再试。",
]

# 错误 — 学生说不知道/不会
_FAIL_NON_ANSWER = [
    "没关系喵～{key_point}，我们再看一遍视频里的这段。",
    "还不熟没关系，核心是{key_point}，点下面的回退键跟我一起复习。",
    "慢慢来，记住{key_point}就好，再看一次就会了喵。",
]

# 错误 — 既漏了又有错误
_FAIL_BOTH = [
    "{wrong}这部分理解不对。另外{missed}没提到。核心就一句：{key_point}。",
    "两个问题：{wrong}是错的；{missed}没写出来。记住{key_point}。",
]


def build_cat_message(
    passed: bool,
    matched: list[str],
    missed: list[str],
    wrong_hits: list[str],
    attempt_num: int,
    step_title: str,
    key_point: str,
    is_non_answer: bool = False,
) -> str:
    """根据评分结果生成猫咪反馈。"""

    filler = random.choice(_FILLERS)

    if passed:
        matched_str = matched[0] if matched else "核心要点"
        if attempt_num == 1:
            msg = random.choice(_PASS_FIRST).format(matched=matched_str)
        else:
            wrong_str = wrong_hits[0] if wrong_hits else "干扰项"
            msg = random.choice(_PASS_RETRY).format(
                matched=matched_str, attempts=attempt_num, wrong=wrong_str
            )
        msg += f"\n⭐ {min(3, 4 - attempt_num)} 星 · 🐟 +3"
        return filler + msg

    # 未通过
    wrong_str = wrong_hits[0] if wrong_hits else ""
    missed_str = missed[0] if missed else ""
    kp_short = key_point[:40] if key_point else "视频里的讲解"

    if is_non_answer:
        msg = random.choice(_FAIL_NON_ANSWER).format(key_point=kp_short)
    elif wrong_hits and missed:
        msg = random.choice(_FAIL_BOTH).format(wrong=wrong_str, missed=missed_str, key_point=kp_short)
    elif wrong_hits:
        msg = random.choice(_FAIL_WRONG).format(wrong=wrong_str, key_point=kp_short)
    elif missed:
        msg = random.choice(_FAIL_MISS).format(missed=missed_str, key_point=kp_short)
    else:
        msg = f"还差一点。{kp_short}——再看看视频里的这段。"

    if missed or is_non_answer:
        msg += "\n\n⏪ 猫猫帮你找到了对应片段，点下面跳回去再看一遍 👇"
    return filler + msg


def calc_cat_state(session: dict, current_idx: int, total: int) -> str:
    """计算猫咪表情状态。"""
    if current_idx >= total:
        return "celebrating"
    results = session["step_results"]
    if not results:
        return "idle"
    last = list(results.values())[-1]
    if not last.get("passed") and last.get("attempts", 0) > 0:
        return "correcting"
    return "watching"
