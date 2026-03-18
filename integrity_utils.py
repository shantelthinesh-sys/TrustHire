import re
from collections import Counter
from difflib import SequenceMatcher

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DISFLUENCY_MARKERS = [
    "um",
    "uh",
    "erm",
    "hmm",
    "you know",
    "like",
]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def tokenize_words(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z']+", normalize_text(text))


def split_sentences(text: str) -> list[str]:
    sentences = [s.strip() for s in re.split(r"[.!?]+", text or "") if s.strip()]
    return sentences


def safe_similarity(a: str, b: str) -> float:
    a = normalize_text(a)
    b = normalize_text(b)
    if not a or not b:
        return 0.0

    vec = CountVectorizer()
    matrix = vec.fit_transform([a, b])
    return float(cosine_similarity(matrix)[0][1])


def lexical_diversity(text: str) -> float:
    tokens = tokenize_words(text)
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)


def repetition_ratio(text: str) -> float:
    tokens = tokenize_words(text)
    if not tokens:
        return 0.0

    counts = Counter(tokens)
    repeated = sum(count for _, count in counts.items() if count > 1)
    return repeated / len(tokens)


def disfluency_rate(text: str) -> float:
    normalized = normalize_text(text)
    tokens = tokenize_words(normalized)
    if not tokens:
        return 0.0

    hits = 0
    for marker in DISFLUENCY_MARKERS:
        hits += normalized.count(marker)
    return hits / len(tokens)


def avg_sentence_length(text: str) -> float:
    sentences = split_sentences(text)
    if not sentences:
        return 0.0

    token_counts = [len(tokenize_words(sentence)) for sentence in sentences]
    return sum(token_counts) / len(token_counts)


def sentence_match_ratio(answer: str, source: str) -> float:
    answer_sentences = split_sentences(normalize_text(answer))
    source_sentences = split_sentences(normalize_text(source))
    if not answer_sentences or not source_sentences:
        return 0.0

    matched = 0
    for ans in answer_sentences:
        if any(ans == src for src in source_sentences):
            matched += 1
    return matched / len(answer_sentences)


def sequence_match_ratio(answer: str, source: str) -> float:
    return SequenceMatcher(None, normalize_text(answer), normalize_text(source)).ratio()


def clamp_0_100(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 100:
        return 100.0
    return value


def interview_integrity_report(transcript: str, suspicious_source: str = "") -> dict:
    transcript = transcript or ""
    suspicious_source = suspicious_source or ""

    diversity = lexical_diversity(transcript)
    repetition = repetition_ratio(transcript)
    avg_len = avg_sentence_length(transcript)
    disfluency = disfluency_rate(transcript)
    source_similarity = safe_similarity(transcript, suspicious_source)

    scripted_risk = 0.0
    if avg_len > 24:
        scripted_risk += 35
    elif avg_len > 18:
        scripted_risk += 20

    if disfluency < 0.003:
        scripted_risk += 25
    elif disfluency < 0.01:
        scripted_risk += 10

    repetition_risk = 0.0
    if repetition > 0.58:
        repetition_risk += 30
    elif repetition > 0.45:
        repetition_risk += 15

    if diversity < 0.30:
        repetition_risk += 20
    elif diversity < 0.40:
        repetition_risk += 10

    source_risk = source_similarity * 100

    risk_total = (0.35 * scripted_risk) + (0.25 * repetition_risk) + (0.40 * source_risk)
    risk_total = clamp_0_100(risk_total)
    integrity_score = clamp_0_100(100 - risk_total)

    if integrity_score >= 70:
        verdict = "Likely Proper Interview"
    elif integrity_score >= 45:
        verdict = "Needs Manual Review"
    else:
        verdict = "Likely Not Proper"

    return {
        "integrity_score": round(integrity_score, 2),
        "risk_score": round(risk_total, 2),
        "verdict": verdict,
        "metrics": {
            "lexical_diversity": round(diversity, 4),
            "repetition_ratio": round(repetition, 4),
            "avg_sentence_length": round(avg_len, 2),
            "disfluency_rate": round(disfluency, 4),
            "source_similarity": round(source_similarity, 4),
        },
    }


def source_reading_report(answer: str, source: str) -> dict:
    answer = answer or ""
    source = source or ""

    cos = safe_similarity(answer, source)
    seq = sequence_match_ratio(answer, source)
    sent_match = sentence_match_ratio(answer, source)

    score = (0.55 * cos) + (0.30 * seq) + (0.15 * sent_match)
    suspicion = clamp_0_100(score * 100)

    if suspicion >= 75:
        label = "High chance of reading from source"
    elif suspicion >= 45:
        label = "Possible source reading"
    else:
        label = "Low source-reading signal"

    return {
        "suspicion_score": round(suspicion, 2),
        "label": label,
        "metrics": {
            "cosine_similarity": round(cos, 4),
            "sequence_similarity": round(seq, 4),
            "exact_sentence_match_ratio": round(sent_match, 4),
        },
    }
