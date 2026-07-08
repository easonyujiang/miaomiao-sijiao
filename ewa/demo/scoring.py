"""混合评分引擎

关键词匹配（第一层）+ LLM 语义判断（第二层回退）。

用于 lesson 答题评分。
"""

from __future__ import annotations

import json
import re

from ewa.llm import LLMClient


# ── 关键词评分 ────────────────────────────────────────────────

def score_answer(answer: str, answer_key: list[str], wrong_key: list[str] | None = None) -> dict:
    """关键词匹配评分。

    从 answer_key 每条提取所有 2+ 字词，
    任意词命中 OR 括号外主干内有 3+ 字公共子串即算匹配。

    Returns:
        {score, matched, missed, wrong_hits}
    """
    wrong_key = wrong_key or []

    def extract_words(text: str) -> list[str]:
        main = re.sub(r"[（(][^）)]*[）)]", "", text)
        cleaned = re.sub(r"[，,。.·：:；;！!？?\[\]【】]", " ", main)
        return [w.strip() for w in cleaned.split() if len(w.strip()) >= 2]

    def any_substr_match(needle_words: list[str], haystack: str) -> bool:
        for w in needle_words:
            if w in haystack:
                return True
            if len(w) >= 4:
                for i in range(len(w) - 2):
                    if w[i : i + 3] in haystack:
                        return True
        return False

    matched = []
    missed = []
    for key in answer_key:
        words = extract_words(key)
        if any_substr_match(words, answer):
            matched.append(key)
        else:
            missed.append(key)

    wrong_hits = []
    for w in wrong_key:
        words = extract_words(w)
        if any_substr_match(words, answer):
            wrong_hits.append(w)

    score = len(matched) / max(len(answer_key), 1)
    if wrong_hits:
        score *= 0.5

    return {
        "score": round(score, 3),
        "matched": matched,
        "missed": missed,
        "wrong_hits": wrong_hits,
    }


# ── LLM 混合评分 ──────────────────────────────────────────────

async def score_answer_with_llm(
    answer: str,
    answer_key: list[str],
    wrong_key: list[str],
    min_correct: int,
    question: str,
    key_point: str,
) -> dict:
    """混合评分：先关键词匹配，不达标时调用 LLM 做语义判断。

    Returns:
        与 score_answer() 相同结构 + llm_used: bool
    """
    # 第一层：关键词匹配
    result = score_answer(answer, answer_key, wrong_key)
    kw_passed = len(result["matched"]) >= min_correct and len(result["wrong_hits"]) == 0

    if kw_passed:
        result["llm_used"] = False
        return result

    # 第二层：LLM 语义判断
    llm_result = await _llm_judge(answer, question, answer_key, wrong_key, key_point)
    if llm_result is None:
        result["llm_used"] = False
        return result

    # 合并：LLM 确认命中的要点追加到 matched
    llm_matched = llm_result.get("matched_points", [])
    llm_wrong = llm_result.get("wrong_points", [])

    for pt in llm_matched:
        if pt not in result["matched"]:
            for key in answer_key:
                if key not in result["matched"]:
                    if _fuzzy_overlap(pt, key) > 0.5 or any(
                        char in key for char in pt if len(char) >= 2
                    ):
                        result["matched"].append(key)
                        if key in result["missed"]:
                            result["missed"].remove(key)
                        break

    for wp in llm_wrong:
        if wp not in result["wrong_hits"]:
            result["wrong_hits"].append(wp)

    # 重新计算分数
    new_score = len(result["matched"]) / max(len(answer_key), 1)
    if result["wrong_hits"]:
        new_score *= 0.5
    result["score"] = round(min(new_score, 1.0), 3)
    result["llm_used"] = True
    result["llm_comment"] = llm_result.get("comment", "")

    return result


def _fuzzy_overlap(a: str, b: str) -> float:
    """两个字符串的简单模糊重叠度（Jaccard-like on characters）。"""
    if not a or not b:
        return 0.0
    set_a = set(a.replace(" ", ""))
    set_b = set(b.replace(" ", ""))
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union


async def _llm_judge(
    answer: str,
    question: str,
    answer_key: list[str],
    wrong_key: list[str],
    key_point: str,
) -> dict | None:
    """调用 LLM 进行语义评分。

    Returns:
        {matched_points, wrong_points, comment} 或 None
    """
    system = """你是一名法学私教评分助手。你的任务是判断学生的回答是否涵盖了参考答案中的要点。

请严格按以下 JSON 格式返回，不要加任何其他文字：
{
  "matched_points": ["被学生命中的要点（从参考答案中摘取）"],
  "wrong_points": ["学生理解有误的表述"],
  "comment": "一句话简评（不超过50字）"
}

评分原则：
1. 只要学生表达的意思与参考答案要点一致，即使措辞不同也应认为命中
2. 关注实质性理解，不是字面匹配
3. 如果学生指出了参考答案中没有的但法律上正确的观点，不算错误
4. 只有明确的法律错误才计入 wrong_points"""

    user = f"""题目：{question}

参考答案要点：
{json.dumps(answer_key, ensure_ascii=False, indent=2)}

常见错误表述：
{json.dumps(wrong_key, ensure_ascii=False, indent=2)}

核心要点：{key_point}

学生的回答：
{answer}

请判断学生的回答命中了哪些要点，以及有哪些错误理解。"""

    client = LLMClient()
    return await client.chat_json(system, user, max_tokens=300)
