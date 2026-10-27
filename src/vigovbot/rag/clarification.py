"""Metadata-backed menus. Client hints select evidence; they never supply it."""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets

from vigovbot.retrieval.retriever import _contains_phrase, _fold, extract_source_codes, preferred_section_types
from vigovbot.utils.helpers import json_hash

SECTION_LABELS = {
    "metadata_identity": "Thông tin chung",
    "procedure_step": "Trình tự thực hiện",
    "required_documents": "Hồ sơ, giấy tờ",
    "submission_deadline_fee": "Cách thức nộp, thời hạn và phí",
    "legal_basis": "Căn cứ pháp lý",
    "other": "Nội dung khác",
}
_SECRET = secrets.token_bytes(32)
_MIXED = "\nPhần yêu cầu ngoài thủ tục hành chính nằm ngoài phạm vi hỗ trợ."
_PROCEDURE_LIST = re.compile(
    r"\b(?:(?:tat ca )?(?:cac|nhung) thu tuc|danh sach (?:cac )?thu tuc|"
    r"liet ke (?:cac )?thu tuc|tat ca thu tuc)\b")
_DISCOVERY_STOP = frozenset((
    "thu tuc cac nhung lien quan ve den toi muon hoi xem tim hieu cho biet la nao"
).split())


def has_goal(text):
    folded = _fold(text)
    return bool(preferred_section_types(text) or any(_contains_phrase(folded, term) for term in (
        "tong quan", "toan bo", "tat ca", "day du", "dieu kien", "yeu cau", "can cu", "bieu mau",
        "mau don", "o dau", "noi nop", "co duoc", "duoc khong", "the nao", "nhu the nao",
    )))


def _signature(value):
    return hmac.new(_SECRET, json.dumps(value, ensure_ascii=False, sort_keys=True).encode(), hashlib.sha256).hexdigest()


def selection_index(text):
    match = re.fullmatch(r"(?:(?:toi|minh|em) )?(?:muon )?(?:chon )?(?:(?:muc|so|thu tuc)(?: thu| so)? )?(\d+)",
                         _fold(text).strip(" .?!"))
    return int(match[1]) if match else None


class Clarifier:
    def __init__(self, retriever, scope=""):
        self.retriever = retriever
        self.catalog = retriever.clarification_catalog()
        self.scope = scope

    def matches(self, query):
        codes = extract_source_codes(query)
        if codes:
            return [code for code in self.catalog if code.casefold() in {c.casefold() for c in codes}]
        folded = _fold(query)
        matched = [code for code, item in self.catalog.items() if _contains_phrase(folded, _fold(item["name"]))]
        # A specific name takes precedence over a generic name contained within it.
        return [code for code in matched if not any(
            _fold(self.catalog[code]["name"]) != _fold(self.catalog[other]["name"])
            and _contains_phrase(_fold(self.catalog[other]["name"]), _fold(self.catalog[code]["name"]))
            for other in matched)]

    def discover(self, query):
        """Find catalog names for a short action/object description without semantic drift."""
        words = [word for word in re.findall(r"\w+", _fold(query)) if word not in _DISCOVERY_STOP]
        # "đất đai" is one object; keeping the second token would reject names using "đất".
        words = [word for i, word in enumerate(words) if not (word == "dai" and i and words[i - 1] == "dat")]
        words = list(dict.fromkeys(words))
        if len(words) < 2:
            return []
        ranked = []
        for code, item in self.catalog.items():
            name_words = re.findall(r"\w+", _fold(item["name"]))
            positions = []
            for word in words:
                matches = [i for i, candidate in enumerate(name_words) if candidate == word]
                if not matches:
                    break
                positions.append(matches[0])
            if len(positions) != len(words):
                continue
            # Favor nearby words in query order. This keeps "thành lập trường" above
            # land procedures containing distant "thành lập doanh nghiệp"/"trường hợp".
            ordered = all(a <= b for a, b in zip(positions, positions[1:]))
            span = max(positions) - min(positions)
            phrase = " ".join(words) in " ".join(name_words)
            inverse = words[:2] == ["thanh", "lap"] and "giai the" in " ".join(name_words[:4])
            ranked.append(((inverse, not phrase, not ordered, span, min(positions), len(name_words), item["name"], code), code))
        return [code for _, code in sorted(ranked)]

    def goal(self, query, codes):
        remainder = _fold(query)
        for code in codes:
            name = _fold(self.catalog[code]["name"])
            remainder = re.sub(rf"(?<!\w){re.escape(name)}(?!\w)", " ", remainder)
        return query if has_goal(remainder) else ""

    def menu(self, kind, codes, goal="", mixed=False):
        codes = list(dict.fromkeys(codes))
        return {"kind": kind, "codes": codes[:5], "more": len(codes) > 5,
                "sections": sorted(self.catalog[codes[0]]["sections"],
                                   key=lambda s: (list(SECTION_LABELS).index(s) if s in SECTION_LABELS else len(SECTION_LABELS), s))
                if kind == "section" else [],
                "goal": " ".join(goal.split()), "mixed": mixed}

    def procedure_labels(self, code):
        """Use the same corpus-backed option text for rendering and selection."""
        name = self.catalog[code]["name"]
        identified = f"{name} — Mã: {code}"
        details = self.retriever.procedure_details(code)
        return (name, identified, identified + (f" ({details})" if details else ""))

    def render(self, menu):
        if menu["kind"] == "procedure":
            lines = (["Bạn muốn hỏi thủ tục nào trong danh sách sau?"] if menu["codes"] else
                     ["Chưa tìm thấy thủ tục phù hợp trong dữ liệu hiện có. Bạn vui lòng bổ sung tên, mã hoặc cơ quan thực hiện."])
            for i, code in enumerate(menu["codes"], 1):
                lines.append(f"{i}. {self.procedure_labels(code)[-1]}")
            if menu["more"]:
                lines.append("Còn nhiều thủ tục phù hợp; bạn có thể bổ sung tên, đối tượng hoặc cơ quan.")
        else:
            code = menu["codes"][0]
            lines = [f"Bạn muốn biết phần nào của thủ tục {self.catalog[code]['name']} — Mã: {code}?"]
            lines += [f"{i}. {SECTION_LABELS.get(section, section)}" for i, section in enumerate(menu["sections"], 1)]
            if not menu["sections"]:
                lines.append("Metadata hiện chưa có mục nội dung để lựa chọn.")
            lines.append("Bạn cũng có thể yêu cầu tổng quan hoặc toàn bộ thủ tục.")
        if menu["goal"]:
            lines.append("Nội dung đang hỏi: " + menu["goal"])
        if menu["codes"]:
            lines.append("Vui lòng trả lời bằng số thứ tự hoặc tên mục/thủ tục.")
        return "\n".join(lines) + (_MIXED if menu["mixed"] else "")

    def context(self, menu, history, question):
        text = self.render(menu)
        value = {**menu, "scope": self.scope, "corpus": json_hash(self.catalog),
                 "history_fingerprint": json_hash([*history, {"role": "user", "content": question},
                                                   {"role": "assistant", "content": text}])}
        return {**value, "signature": _signature(value)}

    def pending(self, history, context, *, recovery_depth=0):
        if not history or history[-1]["role"] != "assistant":
            return None
        if context is not None:
            if not isinstance(context, dict):
                return None
            value = {key: val for key, val in context.items() if key != "signature"}
            signature = context.get("signature")
            if (not isinstance(signature, str) or not hmac.compare_digest(signature, _signature(value))
                    or value.get("scope") != self.scope or value.get("corpus") != json_hash(self.catalog)
                    or value.get("history_fingerprint") != json_hash(history)):
                return None
            return value
        # Older clients carry only history. Rebuild menus from current server metadata
        # and accept only an exact match of our public menu format.
        text = history[-1]["content"]
        if text.startswith("Bạn muốn hỏi thủ tục nào trong danh sách sau?\n"):
            codes = re.findall(r"^\d+\. .* — Mã: ([\w.-]+)", text, re.MULTILINE)
            kind = "procedure"
        elif text.startswith("Bạn muốn biết phần nào của thủ tục "):
            codes = re.findall(r" — Mã: ([\w.-]+)\?", text.splitlines()[0])
            kind = "section"
        else:
            # Recover an unresolved menu after the old selection parser returned
            # our no-candidate notice. Never cross an unrelated question/answer.
            if (recovery_depth < 3 and len(history) >= 4 and text.startswith(
                    "Chưa tìm thấy thủ tục phù hợp trong dữ liệu hiện có.")):
                previous = self.pending(history[:-2], None, recovery_depth=recovery_depth + 1)
                menu, resolved = self.consume(history[-2]["content"], previous)
                if menu or resolved:
                    return menu or previous
            return None
        if not codes or len(codes) > 5 or any(code not in self.catalog for code in codes):
            return None
        goals = re.findall(r"^Nội dung đang hỏi: (.*)$", text, re.MULTILINE)
        menu = self.menu(kind, codes, goals[0] if goals else "", text.endswith(_MIXED))
        menu["more"] = "\nCòn nhiều thủ tục phù hợp;" in text
        return menu if self.render(menu) == text else None

    def consume(self, question, pending):
        """Return (menu to repeat/advance, resolved query); neither means new topic."""
        if not pending:
            return None, None
        folded = _fold(question).strip(" .?!")
        number = selection_index(question)
        # A copied numbered label is a choice only if its text agrees with the
        # current menu. This also handles Markdown's escaped "4\\. label".
        copied = re.fullmatch(r"(\d+)\s*\\?[.)]\s+(.+)", folded)
        if copied:
            index, label = int(copied[1]), copied[2].strip()
            labels = ([(SECTION_LABELS.get(s, s),) for s in pending["sections"]]
                      if pending["kind"] == "section" else
                      [self.procedure_labels(c) for c in pending["codes"]])
            if not 0 < index <= len(labels) or label not in {_fold(text) for text in labels[index - 1]}:
                return pending, None
            number = index
        if pending["kind"] == "procedure":
            choices = pending["codes"]
            selected = ([choices[number - 1]] if number is not None and 0 < number <= len(choices) else [])
            if number is None:
                selected = [code for code in self.matches(question) if code in choices]
            if len(selected) == 1:
                code = selected[0]
                is_label = number is not None or folded in {_fold(text) for text in self.procedure_labels(code)}
                # Authority/level in a copied option describes the choice; it is
                # not a request to answer the metadata_identity section.
                goal = pending["goal"] if is_label else self.goal(question, [code]) or pending["goal"]
                if goal:
                    return None, f"{goal}\nThủ tục được chọn: {self.catalog[code]['name']}\nMã thủ tục: {code}"
                return self.menu("section", [code], mixed=pending["mixed"]), None
        else:
            choices = pending["sections"]
            code = pending["codes"][0]
            # An explicitly different subject wins over a pending section choice.
            named = self.matches(question)
            if (named and code not in named) or (extract_source_codes(question) and not named):
                return None, None
            selected = [choices[number - 1]] if number is not None and 0 < number <= len(choices) else []
            if number is None:
                selected = [s for s in choices if _contains_phrase(folded, _fold(s))
                            or _contains_phrase(folded, _fold(SECTION_LABELS.get(s, s)))]
            # A new, unknown subject must not silently inherit the previous code.
            # Only section language and conversational filler can be elliptical.
            vocabulary = set((
                "toi minh em muon biet hoi xem cho xin vui long giup hay ve phan muc noi dung "
                "con va hoac cua thu tuc nay do nay thi la gom co nhung gi nao can duoc khong "
                "ho so giay to thanh phan phi le thoi han bao lau cach thuc hinh nop trinh tu "
                "quy cac buoc thong tin chung tong quan toan bo tat ca day du dieu kien yeu cau "
                "can cu phap ly bieu mau don o dau co quan cap thuc hien nhu the nao chi tiet "
                "huong dan dang chon"
            ).split())
            remainder = folded
            for section in selected:
                remainder = remainder.replace(_fold(SECTION_LABELS.get(section, section)), "").replace(_fold(section), "")
            if not named and number is None and set(re.findall(r"\w+", remainder)) - vocabulary:
                return None, None
            if selected or self.goal(question, [code]):
                goal = (", ".join(SECTION_LABELS.get(s, s) for s in selected)
                        if number is not None else question)
                if number is None:
                    selected = list(dict.fromkeys([*selected, *preferred_section_types(question)]))
                section_query = "".join(f"\nMục dữ liệu: {section}" for section in selected)
                return None, f"{goal}\nThủ tục được chọn: {self.catalog[code]['name']}\nMã thủ tục: {code}{section_query}"
        if number is not None or folded in {"chon", "muc nay", "thu tuc nay"}:
            return pending, None
        return None, None

    def inspect(self, query, *, hits=None, mixed=False):
        codes = self.matches(query)
        explicit = extract_source_codes(query)
        list_request = not explicit and bool(_PROCEDURE_LIST.search(_fold(query)))
        if list_request and codes:
            # A catalog can contain both a generic exact name and longer variants.
            # Plural discovery must include those variants before choosing sections.
            names = [_fold(self.catalog[code]["name"]) for code in codes]
            related = [code for code, item in self.catalog.items()
                       if any(_contains_phrase(_fold(item["name"]), name) for name in names)]
            codes = sorted(related, key=lambda code: (
                _fold(self.catalog[code]["name"]) not in names, len(self.catalog[code]["name"]), code))
            goal_query = _PROCEDURE_LIST.sub("", _fold(query))
            return self.menu("procedure", codes, self.goal(goal_query, codes), mixed)
        if explicit and len(codes) != len(explicit):
            return None  # Preserve the existing unknown-code abstention.
        # Explicit comparisons/multi-procedure requests are already intentional.
        distinct_names = {_fold(self.catalog[code]["name"]) for code in codes}
        if len(codes) > 1 and (len(explicit) > 1 or _contains_phrase(_fold(query), "so sanh") or
                              (len(distinct_names) == len(codes) and _contains_phrase(_fold(query), "va"))):
            return None
        goal = self.goal(query, codes)
        if len(codes) > 1:
            return self.menu("procedure", codes, goal, mixed)
        if len(codes) == 1:
            return None if goal else self.menu("section", codes, mixed=mixed)
        if hits is not None:
            subject = re.sub(r"\b(?:thu tuc|ho so|giay to|viet nam|dang ky|cap lai|cap moi|gia han|thoi han|le phi)\b",
                             " ", _fold(query))
            stop = set("o tai toi muon hoi ve cho xin la cua va can phi bao lau cap".split())
            words = set(re.findall(r"\w+", subject)) - stop
            candidates = list(dict.fromkeys(h.get("source_code") for h in hits
                if h.get("source_code") in self.catalog
                and len(words & set(re.findall(r"\w+", _fold(self.catalog[h["source_code"]]["name"])))) >= 2))
            return self.menu("procedure", candidates, goal, mixed)
        return None
