#!/usr/bin/env python3
"""Check Traditional Chinese audiobook and voice-script risks."""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import BadZipFile, ZipFile


MODE_LABELS = {
    "aphorism": "語錄關鍵字拆解",
    "counseling": "心理故事與諮商對話",
    "workplace": "職場寓言與人性反轉",
    "social-ai": "AI／社會議題問答論述",
    "dialogue": "雙人對話式有聲書",
    "classic": "經典作品現代超譯",
}

CONNECTIVES = ("其實", "然而", "也就是", "因此", "最後", "此外", "換言之")
SECOND_PERSON = ("你", "我們", "大家", "讀者", "聽眾")
METAPHORS = ("像", "如同", "就像", "彷彿", "好比")
REVERSALS = ("真正", "關鍵", "重點", "問題是", "更值得注意", "沒想到", "結果", "表面")
CLOSINGS = ("因此", "所以", "最後", "只要", "唯有", "提醒", "下一次", "從現在開始")

FORBIDDEN_PATTERN = re.compile(r"(?:(?:這|那|此)?(?:並)?不是|並非)[^。！？\n]{0,40}而是")

SOURCE_HEADING_RE = re.compile(
    r"(?m)^#{0,3}\s*(?:資料來源|參考資料|Sources?)\s*[：:]?\s*$",
    re.I,
)

ATTRIBUTED_QUOTE_RE = re.compile(
    r"[\u3400-\u9fffA-Za-z·]{2,20}(?:曾經說|也曾說|曾說|表示|指出|寫道|提醒|強調)"
    r"[^。！？\n]{0,24}[：:]?\s*[「『][^」』\n]{4,}[」』]"
)

HEADING_RE = re.compile(
    r"^(?:#{1,6}\s*|第[一二三四五六七八九十百0-9]+[章篇輯句]|作者序|編者序|序言|前言|資料來源|參考資料)"
)

ROLE_LINE_RE = re.compile(
    r"(?m)^\s*(?:#{1,6}\s*)?(?P<role>A|B|甲|乙|主持人|來賓)\s*(?P<colon>[：:])\s*(?P<speech>.+)$"
)
GENERIC_ROLE_LINE_RE = re.compile(
    r"(?m)^\s*(?:#{1,6}\s*)?(?P<role>[\u3400-\u9fffA-Za-z][\u3400-\u9fffA-Za-z0-9·]{0,11})\s*[：:]\s*(?P<speech>.+)$"
)
VOICE_SPEC_TERMS = (
    "聲音人格", "聲線", "配音員", "朗讀者", "語速", "音調", "停頓", "風格權重", "角色設定", "聲音規格"
)
HARD_SYMBOL_RE = re.compile(r"[•●■◆◇→←↑↓↔※★☆✓✔✕×÷=+<>|\\^~]{1,}")
ENGLISH_TOKEN_RE = re.compile(r"(?<![\w])(?:[A-Z]{2,}|[A-Za-z]+\d+|\d+[A-Za-z]+)(?![\w])")
RISKY_NUMBER_RE = re.compile(r"(?<![\w])(?:19|20)\d{2}|\d{4,}|\d+(?:\.\d+)?%")


def read_docx(path: Path) -> str:
    try:
        with ZipFile(path) as archive:
            xml = archive.read("word/document.xml")
    except (BadZipFile, KeyError) as exc:
        raise ValueError(f"無法讀取 DOCX：{exc}") from exc

    root = ET.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for paragraph in root.findall(".//w:p", ns):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", ns)).strip()
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


def read_input(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return read_docx(path)
    if suffix in {".txt", ".md", ".markdown"}:
        try:
            return path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            return path.read_text(encoding="utf-8")
    raise ValueError("只支援 .txt、.md、.markdown、.docx")


def compact_length(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def count_terms(text: str, terms: tuple[str, ...]) -> int:
    return sum(text.count(term) for term in terms)


def infer_mode(text: str) -> tuple[str, dict[str, int]]:
    scores = {
        "aphorism": 3 * len(re.findall(r"第(?:[一二三四五六七八九十百]+|\d+)句", text))
        + 4 * text.count("關鍵字")
        + 2 * count_terms(text, ("語錄", "提醒我們", "告訴我們")),
        "counseling": 3 * count_terms(text, ("諮商", "心理醫師", "心理醫生", "故事背後的問題"))
        + count_terms(text, ("焦慮", "自卑", "關係", "努力", "感受")),
        "workplace": 2 * count_terms(text, ("職場", "公司", "主管", "同事", "總經理"))
        + 2 * count_terms(text, ("厚黑", "出賣", "算計", "騙")),
        "social-ai": 3 * text.upper().count("AI")
        + 2 * count_terms(text, ("科技", "演算法", "社會", "時代", "未來")),
        "dialogue": 4 * len(re.findall(r"(?m)^(?:A|B|甲|乙|主持人|來賓)[：:]", text))
        + 2 * count_terms(text, ("對話", "閨密", "陪伴", "你覺得")),
        "classic": 3 * count_terms(text, ("原著", "原作", "超譯", "編者", "魯迅", "李宗吾"))
        + len(re.findall(r"第[一二三四五六七八九十百]+章", text)),
    }
    mode = max(scores, key=scores.get)
    if scores[mode] == 0:
        mode = "social-ai"
    return mode, scores


def split_paragraphs(text: str) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n|\r\n\s*\r\n", text) if part.strip()]
    if len(paragraphs) <= 1:
        paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
    return paragraphs


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[。！？!?；;]+", text) if part.strip()]


def issue(severity: str, code: str, message: str, suggestion: str) -> dict[str, str]:
    return {"severity": severity, "code": code, "message": message, "suggestion": suggestion}


def template_markers(text: str, mode: str) -> tuple[int, int, list[str]]:
    markers = {
        "aphorism": [
            ("原句或引言", bool(re.search(r"[「『].{4,}[」』]", text))),
            ("關鍵字", "關鍵字" in text),
            ("生活解釋", count_terms(text, ("生活", "職場", "例如", "譬如")) > 0),
            ("提醒收尾", count_terms(text[-400:], ("提醒", "告訴", "下一次", "因此")) > 0),
        ],
        "counseling": [
            ("具體困境", count_terms(text, ("困難", "問題", "煩惱", "壓力", "焦慮")) > 0),
            ("人物對話", len(re.findall(r"[：:][「『]", text)) >= 2),
            ("心理機制", count_terms(text, ("感受", "需求", "期待", "自卑", "界線")) > 0),
            ("行動方向", count_terms(text[-600:], ("可以", "試著", "練習", "學會", "方法")) > 0),
        ],
        "workplace": [
            ("人物利害", count_terms(text, ("主管", "同事", "公司", "利益", "競爭")) > 0),
            ("事件轉折", count_terms(text, ("沒想到", "豈知", "結果", "突然", "原來")) > 0),
            ("動機解釋", count_terms(text, ("動機", "原因", "目的", "盤算", "算計")) > 0),
            ("保護原則", count_terms(text[-600:], ("提醒", "避免", "保護", "警惕", "方法")) > 0),
        ],
        "social-ai": [
            ("當代問題", (text.count("？") + text.count("?")) > 0),
            ("可觀察現象", count_terms(text, ("現在", "目前", "近年", "現象", "時代")) > 0),
            ("核心命題", count_terms(text, ("真正", "關鍵", "重點", "值得注意")) > 0),
            ("人的選擇", count_terms(text[-600:], ("選擇", "行動", "練習", "我們", "人類")) > 0),
        ],
        "dialogue": [
            ("穩定角色標示", len(re.findall(r"(?m)^(?:A|B|甲|乙|主持人|來賓)[：:]", text)) >= 6),
            ("真實困惑", (text.count("？") + text.count("?")) >= 2),
            ("可理解分歧", count_terms(text, ("可是", "但", "同意", "不同", "也許")) > 0),
            ("界線或代價", count_terms(text[-800:], ("界線", "代價", "責任", "風險", "選擇")) > 0),
        ],
        "classic": [
            ("原作歸屬", count_terms(text, ("原著", "原作", "作者", "編者")) > 0),
            ("章節或背景", count_terms(text, ("第", "背景", "當時", "年代")) > 0),
            ("現代轉述", count_terms(text, ("換成今天", "現代", "簡單來說", "大白話", "超譯")) > 0),
            ("現代連結", count_terms(text[-800:], ("今天", "現在", "我們", "現代人", "提醒")) > 0),
        ],
    }[mode]
    found = sum(1 for _, present in markers if present)
    missing = [label for label, present in markers if not present]
    return found, len(markers), missing


def analyze(path: Path, requested_mode: str) -> dict:
    text = read_input(path).strip()
    if not text:
        raise ValueError("稿件沒有可分析文字")

    inferred_mode, mode_scores = infer_mode(text)
    mode = inferred_mode if requested_mode == "auto" else requested_mode
    paragraphs = split_paragraphs(text)
    body_paragraphs = [p for p in paragraphs if not HEADING_RE.match(p) and compact_length(p) >= 20]
    sentences = split_sentences(text)
    chars = compact_length(text)
    paragraph_lengths = [compact_length(p) for p in body_paragraphs] or [chars]
    sentence_lengths = [compact_length(s) for s in sentences] or [chars]
    density_divisor = max(chars / 1000, 0.001)

    forbidden_hits = [match.group(0) for match in FORBIDDEN_PATTERN.finditer(text)]

    source_match = SOURCE_HEADING_RE.search(text)
    source_heading = source_match is not None
    narration = text[: source_match.start()] if source_match else text
    source_section = text[source_match.end() :] if source_match else ""
    narration_urls = re.findall(r"https?://\S+|www\.\S+", narration)
    source_urls = re.findall(r"https?://\S+|www\.\S+", source_section)
    unfinished = re.findall(r"【待查證】|\bTODO\b|\[TODO[^\]]*\]", text, flags=re.I)
    unmatched_quotes = (text.count("「") != text.count("」")) or (text.count("『") != text.count("』"))
    attributed_quotes = ATTRIBUTED_QUOTE_RE.findall(narration)
    factual_risk = bool(
        re.search(
            r"(?:19|20)\d{2}年|\d+(?:\.\d+)?%|研究(?:指出|顯示)|根據.{0,20}(?:報告|調查)",
            narration,
        )
        or attributed_quotes
        or (mode == "aphorism" and re.search(r"[「『][^」』\n]{4,}[」』]", narration))
    )
    sources_complete = bool(source_heading and source_urls)

    question_count = text.count("？") + text.count("?")
    second_person_count = count_terms(text, SECOND_PERSON)
    connective_counts = {term: text.count(term) for term in CONNECTIVES}
    metaphor_count = count_terms(text, METAPHORS)
    reversal_count = count_terms(text, REVERSALS)
    closing_count = count_terms(text[-500:], CLOSINGS)
    long_sentence_ratio = sum(length > 90 for length in sentence_lengths) / len(sentence_lengths)
    long_paragraph_ratio = sum(length > 220 for length in paragraph_lengths) / len(paragraph_lengths)
    question_density = question_count / density_divisor
    second_person_density = second_person_count / density_divisor
    max_connective_density = max(connective_counts.values(), default=0) / density_divisor
    template_found, template_total, missing_markers = template_markers(text, mode)

    role_matches = list(ROLE_LINE_RE.finditer(text))
    generic_role_matches = list(GENERIC_ROLE_LINE_RE.finditer(text))
    role_counts: dict[str, int] = {}
    role_colons: dict[str, set[str]] = {}
    long_units: list[dict[str, object]] = []
    for match in role_matches:
        role = match.group("role")
        speech_length = compact_length(match.group("speech"))
        role_counts[role] = role_counts.get(role, 0) + 1
        role_colons.setdefault(role, set()).add(match.group("colon"))
        if speech_length > 180:
            long_units.append({"role": role, "characters": speech_length, "excerpt": match.group("speech")[:40]})

    scripted_dialogue = len(role_matches) >= 4
    delivery_format = "dual-voice" if role_counts.get("A", 0) and role_counts.get("B", 0) else (
        "multi-voice" if len(role_counts) >= 2 else "single-voice"
    )
    expected_roles = {"A", "B"} if delivery_format == "dual-voice" else set(role_counts)
    unexpected_roles = sorted({match.group("role") for match in generic_role_matches} - expected_roles)
    mixed_colon_roles = sorted(role for role, colons in role_colons.items() if len(colons) > 1)
    role_marker_styles = sorted({match.group("colon") for match in role_matches})
    orphan_dialogue_lines = []
    if scripted_dialogue:
        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = re.sub(r"^#{1,6}\s*", "", line.strip())
            if stripped and re.match(r"^[「『].+[」』]", stripped) and not GENERIC_ROLE_LINE_RE.match(stripped):
                orphan_dialogue_lines.append(line_number)

    hard_symbols = HARD_SYMBOL_RE.findall(narration)
    english_tokens = ENGLISH_TOKEN_RE.findall(narration)
    risky_numbers = RISKY_NUMBER_RE.findall(narration)
    voice_spec_terms_found = [term for term in VOICE_SPEC_TERMS if term in text]
    voice_spec_present = len(voice_spec_terms_found) >= 2

    issues: list[dict[str, str]] = []
    if forbidden_hits:
        issues.append(issue("critical", "forbidden-contrast", f"發現 {len(forbidden_hits)} 處禁用對仗句法。", "改用『真正的關鍵在於』『重點落在』或拆成兩句。"))
    if unfinished:
        issues.append(issue("critical", "unfinished-marker", f"發現 {len(unfinished)} 個未完成或待查證標記。", "完成查證並移除所有工作標記後再交稿。"))
    if narration_urls:
        issues.append(issue("critical", "url-in-narration", f"朗讀正文偵測到 {len(narration_urls)} 個網址。", "將網址移到朗讀正文後的資料來源。"))
    if source_urls:
        issues.append(issue("info", "source-urls", f"資料來源區偵測到 {len(source_urls)} 個網址。", "人工確認每個來源都能支持對應主張。"))
    if factual_risk and not sources_complete:
        issues.append(issue("critical", "sources-missing", "稿件含年代、數字、研究或可辨識的具名引言，但資料來源區缺少可追溯連結。", "完成查證並在正文後附上來源標題與連結。"))
    if unmatched_quotes:
        issues.append(issue("warning", "unmatched-quotes", "引號數量不成對，可能造成朗讀或排版錯誤。", "補齊或移除不成對的引號。"))
    if long_sentence_ratio > 0.20:
        issues.append(issue("warning", "long-sentences", f"超過 90 字的句子占 {long_sentence_ratio:.0%}。", "用句號或分號拆開逗號串接的長句。"))
    if long_paragraph_ratio > 0.25:
        issues.append(issue("warning", "long-paragraphs", f"超過 220 字的正文段落占 {long_paragraph_ratio:.0%}。", "將段落拆成單一聽覺單位。"))
    if second_person_density < 4:
        issues.append(issue("warning", "low-dialogue-density", "與聽眾直接對話的密度偏低。", "在開場、案例轉折或收尾自然加入『你』『我們』。"))
    if metaphor_count == 0 and chars >= 600:
        issues.append(issue("warning", "no-life-metaphor", "長文中未偵測到生活化比喻。", "加入一個能幫助理解的具象比喻，避免堆疊多個意象。"))
    if reversal_count == 0 and chars >= 500:
        issues.append(issue("warning", "no-reversal", "未偵測到清楚的觀點翻轉或關鍵命題。", "指出多數人容易忽略的因素，並補足推理。"))
    if closing_count == 0 and chars >= 500:
        issues.append(issue("warning", "weak-closing", "結尾缺少可記憶的提醒或行動方向。", "回扣開場問題，留下新的理解、界線或下一步。"))
    if max_connective_density > 8:
        dominant = max(connective_counts, key=connective_counts.get)
        issues.append(issue("warning", "connective-overuse", f"轉折詞『{dominant}』使用密度偏高。", "改變段落起手方式，或直接陳述因果。"))
    if missing_markers:
        issues.append(issue("warning", "template-incomplete", f"{MODE_LABELS[mode]}尚缺：{'、'.join(missing_markers)}。", "依題材模板補齊必要功能，無須機械加入固定字眼。"))
    if scripted_dialogue and not (role_counts.get("A", 0) and role_counts.get("B", 0)):
        issues.append(issue("critical", "role-pair-incomplete", "稿件具有雙人腳本特徵，但 A／B 角色沒有成對出現。", "確認缺少的角色標示，或明確改成單人旁白稿。"))
    if mixed_colon_roles:
        issues.append(issue("warning", "role-marker-inconsistent", f"角色 {'、'.join(mixed_colon_roles)} 混用全形與半形冒號。", "全稿統一使用『角色：內容』格式。"))
    elif len(role_marker_styles) > 1:
        issues.append(issue("warning", "role-marker-style-inconsistent", "不同角色混用全形與半形冒號。", "全稿統一使用『角色：內容』格式。"))
    if unexpected_roles and delivery_format == "dual-voice":
        issues.append(issue("warning", "unexpected-role-label", f"A／B 稿中另偵測到角色標示：{'、'.join(unexpected_roles[:8])}。", "確認這些是正式角色，或修正誤標的對話歸屬。"))
    if orphan_dialogue_lines:
        issues.append(issue("warning", "dialogue-attribution", f"偵測到 {len(orphan_dialogue_lines)} 行引號對話缺少明確角色標示。", "在聽眾可能混淆前補上說話者或旁白歸屬。"))
    if long_units:
        issues.append(issue("warning", "long-auditory-units", f"偵測到 {len(long_units)} 個超過 180 字的角色發言。", "拆成單一意思的聽覺單位，並安排自然角色交接或停頓。"))
    if hard_symbols:
        issues.append(issue("warning", "hard-to-pronounce-symbols", f"朗讀正文偵測到 {len(hard_symbols)} 組難念符號。", "將符號改寫成可朗讀文字，或在讀音表中明確定義。"))
    if english_tokens or risky_numbers:
        issues.append(issue("warning", "pronunciation-risk", f"偵測到 {len(english_tokens)} 個英文／混合詞與 {len(risky_numbers)} 個高風險數字。", "建立英文、年份、長數字與百分比的逐項讀音表。"))
    if delivery_format in {"dual-voice", "multi-voice"} and not voice_spec_present:
        issues.append(issue("warning", "voice-spec-missing", "多角色配音稿未偵測到角色聲音規格。", "補上每個角色的功能、聲音人格、語速、音調、停頓與情緒方向。"))

    voice_score = 25
    if second_person_density < 4:
        voice_score -= 6
    if metaphor_count == 0 and chars >= 600:
        voice_score -= 5
    if reversal_count == 0 and chars >= 500:
        voice_score -= 7
    if closing_count == 0 and chars >= 500:
        voice_score -= 4
    if question_density == 0 and mode in {"counseling", "social-ai", "dialogue", "workplace"}:
        voice_score -= 3

    structure_score = round(25 * template_found / template_total)
    tts_score = 20
    tts_score -= min(8, round(long_sentence_ratio * 20))
    tts_score -= min(5, round(long_paragraph_ratio * 12))
    if unmatched_quotes:
        tts_score -= 3
    if narration_urls:
        tts_score -= 4

    language_score = 15
    language_score -= min(8, len(forbidden_hits) * 4)
    if max_connective_density > 8:
        language_score -= 3
    simplified_hits = count_terms(text, ("软件", "视频", "信息", "网络", "里面的", "质量"))
    if simplified_hits:
        language_score -= min(4, simplified_hits)
        issues.append(issue("warning", "taiwan-usage", f"偵測到 {simplified_hits} 處可能偏離台灣用語的詞彙。", "改用軟體、影片、訊息、網路、其中、品質等台灣常用詞。"))

    fact_score = 15
    if factual_risk and not sources_complete:
        fact_score -= 8
    if unfinished:
        fact_score -= 7

    dimensions = {
        "author_voice": max(0, voice_score),
        "structure": max(0, structure_score),
        "tts_fluency": max(0, tts_score),
        "language": max(0, language_score),
        "factual_safety": max(0, fact_score),
    }
    total_score = sum(dimensions.values())
    critical_count = sum(item["severity"] == "critical" for item in issues)

    return {
        "input": str(path.resolve()),
        "requested_mode": requested_mode,
        "mode": mode,
        "mode_label": MODE_LABELS[mode],
        "mode_scores": mode_scores,
        "delivery_format": delivery_format,
        "delivery_format_label": {"single-voice": "單人稿", "dual-voice": "A／B 雙人稿", "multi-voice": "多角色稿"}[delivery_format],
        "score": total_score,
        "passed": total_score >= 80 and critical_count == 0,
        "critical_count": critical_count,
        "dimensions": dimensions,
        "metrics": {
            "characters": chars,
            "paragraphs": len(body_paragraphs),
            "sentences": len(sentences),
            "median_paragraph_length": round(statistics.median(paragraph_lengths), 1),
            "average_sentence_length": round(statistics.mean(sentence_lengths), 1),
            "long_paragraph_ratio": round(long_paragraph_ratio, 4),
            "long_sentence_ratio": round(long_sentence_ratio, 4),
            "questions_per_1000_chars": round(question_density, 2),
            "second_person_per_1000_chars": round(second_person_density, 2),
            "metaphor_markers": metaphor_count,
            "reversal_markers": reversal_count,
            "connectives": connective_counts,
            "template_markers_found": template_found,
            "template_markers_total": template_total,
            "source_section_present": source_heading,
            "narration_url_count": len(narration_urls),
            "source_url_count": len(source_urls),
            "attributed_quote_count": len(attributed_quotes),
            "role_counts": role_counts,
            "mixed_colon_roles": mixed_colon_roles,
            "role_marker_styles": role_marker_styles,
            "unexpected_role_labels": unexpected_roles,
            "orphan_dialogue_lines": orphan_dialogue_lines,
            "long_auditory_units": long_units,
            "hard_symbol_count": len(hard_symbols),
            "english_token_count": len(english_tokens),
            "risky_number_count": len(risky_numbers),
            "voice_spec_present": voice_spec_present,
            "voice_spec_terms_found": voice_spec_terms_found,
        },
        "issues": issues,
    }


def render_text(report: dict) -> str:
    result = "通過" if report["passed"] else "需修訂"
    lines = [
        "# 風格檢查結果",
        f"- 檔案：{report['input']}",
        f"- 寫作模式：{report['mode_label']}",
        f"- 配音形式：{report['delivery_format_label']}",
        f"- 總分：{report['score']}/100",
        f"- 結果：{result}",
        "",
        "## 分項分數",
        f"- 作者特徵：{report['dimensions']['author_voice']}/25",
        f"- 題材結構：{report['dimensions']['structure']}/25",
        f"- 朗讀流暢：{report['dimensions']['tts_fluency']}/20",
        f"- 語言規範：{report['dimensions']['language']}/15",
        f"- 事實安全：{report['dimensions']['factual_safety']}/15",
        "",
        "## 主要指標",
        f"- 字數：{report['metrics']['characters']}",
        f"- 正文段落中位長度：{report['metrics']['median_paragraph_length']}",
        f"- 平均句長：{report['metrics']['average_sentence_length']}",
        f"- 每千字問句：{report['metrics']['questions_per_1000_chars']}",
        f"- 每千字第二人稱／群體稱呼：{report['metrics']['second_person_per_1000_chars']}",
        f"- 角色發言：{report['metrics']['role_counts']}",
        f"- 過長聽覺單位：{len(report['metrics']['long_auditory_units'])}",
        f"- 英文／數字讀音風險：{report['metrics']['english_token_count'] + report['metrics']['risky_number_count']}",
        "",
        "## 問題與建議",
    ]
    if not report["issues"]:
        lines.append("- 未發現規則型問題；仍須人工確認論點、事實與整體聽感。")
    else:
        severity_labels = {"critical": "重大", "warning": "警告", "info": "提示"}
        for item in report["issues"]:
            lines.append(f"- [{severity_labels[item['severity']]}] {item['message']} 建議：{item['suggestion']}")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="檢查繁中有聲書風格、配音稿與校聽前風險")
    parser.add_argument("input", type=Path, help="輸入 .txt、.md、.markdown 或 .docx")
    parser.add_argument("--mode", choices=["auto", *MODE_LABELS.keys()], default="auto", help="指定題材模式")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="輸出格式")
    parser.add_argument("--output", type=Path, help="另存檢查結果")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input.is_file():
        print(f"錯誤：找不到檔案 {args.input}", file=sys.stderr)
        return 2
    try:
        report = analyze(args.input, args.mode)
    except (OSError, ValueError, ET.ParseError) as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 2

    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n" if args.format == "json" else render_text(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
