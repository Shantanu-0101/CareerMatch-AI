"""Interview answer evaluation: AI when configured, otherwise a transparent keyword check."""
import re

from .ai_service import AIError, get_ai

STOPWORDS = set("""a an the and or but if then else when while of to in on at by for with from into over under
is are was were be been being it its this that these those as can could should would will may might must do does
did not no yes so such than too very you your we our they their them he she his her which who whom what where why
how all any each other some more most also only own same just about after before because between both during
used use using uses like into same through""".split())


def _keywords(text):
    words = re.findall(r"[a-zA-Z][a-zA-Z+#.\-]{3,}", text.lower())
    seen, out = set(), []
    for w in words:
        w = w.strip(".-")
        if w not in STOPWORDS and w not in seen and len(w) > 3:
            seen.add(w)
            out.append(w)
    return out


def rule_evaluate(model_answer, user_answer):
    keys = _keywords(model_answer)
    answer = user_answer.lower()
    covered = [k for k in keys if k in answer]
    coverage = len(covered) / len(keys) if keys else 0
    score = round(10 * min(1.0, coverage / 0.6))  # covering ~60% of key terms earns full marks
    if len(user_answer.split()) < 8:
        score = min(score, 3)
    missed = [k for k in keys if k not in covered][:8]
    feedback = (f"Your answer covers {len(covered)} of {len(keys)} key terms from the reference answer. "
                + ("Good coverage of the main ideas." if score >= 7 else
                   "Try to explain the core concepts more completely."))
    return {"score": score, "feedback": feedback, "missing_points": missed, "covered": covered[:10]}


def evaluate(question, model_answer, user_answer):
    """Returns (result_dict, method) where method is 'ai' or 'rule'."""
    ai = get_ai()
    if ai.enabled:
        try:
            return ai.evaluate_answer(question, model_answer, user_answer), "ai"
        except AIError as e:
            result = rule_evaluate(model_answer, user_answer)
            result["ai_error"] = str(e)
            return result, "rule"
    return rule_evaluate(model_answer, user_answer), "rule"
