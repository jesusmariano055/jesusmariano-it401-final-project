import os
import re
from typing import Iterable

import requests


class AiService:
    """Tiny provider wrapper with a deterministic local fallback."""

    def __init__(self, api_key=None, model=None, endpoint=None):
        self.api_key = api_key or os.environ.get("AI_SERVICE_API_KEY")
        self.model = model or os.environ.get("AI_SERVICE_MODEL", "gpt-4o-mini")
        self.endpoint = endpoint or os.environ.get("AI_SERVICE_ENDPOINT")

    def generate(self, prompt, **kwargs):
        if self.api_key and self.endpoint:
            try:
                return self._call_remote(prompt, **kwargs)
            except requests.RequestException:
                pass
        return self._local_generate(prompt, **kwargs)

    def _call_remote(self, prompt, **kwargs):
        payload = {
            "model": kwargs.get("model") or self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.2),
        }
        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=kwargs.get("timeout", 10),
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise ValueError("No choices returned from AI service.")
        message = choices[0].get("message") or {}
        content = message.get("content") or ""
        return content.strip() or "No summary available."

    def _local_generate(self, prompt, **kwargs):
        text = (prompt or "").strip()
        if not text:
            return "No prompt provided for local analysis."
        normalized = re.sub(r"\s+", " ", text)
        if len(normalized) <= 220:
            return normalized
        sentences = re.split(r"(?<=[.!?])\s+", normalized)
        summary = " ".join(sentences[:2]).strip()
        if len(summary) > 280:
            summary = summary[:277].rsplit(" ", 1)[0] + "..."
        return summary


def _normalize_keywords(value):
    text = (value or "")
    words = re.findall(r"[A-Za-z0-9]+", text.lower())
    return [word for word in words if len(word) > 2 and word not in {"with", "from", "that", "this", "into", "over", "your", "they", "them"}]


def summarize_player_record(record):
    if record is None:
        return "No player record was available for analysis."

    name = record.name or "Unnamed player"
    team = record.team_name or record.team_abbreviation or "an unknown team"
    position = record.position or "an unspecified role"
    description = (record.description or "").strip()
    summary_parts = [
        f"{name} is a player profile centered on {team} and listed as {position}.",
    ]

    if description:
        short_description = re.sub(r"\s+", " ", description)
        if len(short_description) > 200:
            short_description = short_description[:197].rsplit(" ", 1)[0] + "..."
        summary_parts.append(f"The saved scouting notes describe: {short_description}.")

    if record.height or record.weight:
        summary_parts.append(
            f"Physical profile: {record.height or 'height not listed'} and {record.weight or 'weight not listed'}."
        )

    summary_parts.append(f"This record was saved from {record.source or 'an unspecified source'}.")
    return " ".join(summary_parts)


def suggest_related_queries(record, other_records=None, limit=3):
    if record is None:
        return []

    keywords = _normalize_keywords(f"{record.name} {record.description} {record.position} {record.team_abbreviation or ''}")
    seeds = []
    for keyword in keywords:
        if keyword not in {"player", "team", "source", "record"}:
            seeds.append(keyword)

    if record.team_abbreviation:
        seeds.insert(0, record.team_abbreviation)
    if record.position:
        seeds.insert(0, record.position.lower())

    suggestions = []
    for token in seeds[:6]:
        suggestion = token.strip()
        if suggestion and suggestion not in suggestions:
            suggestions.append(suggestion)

    if record.team_abbreviation and record.position:
        suggestions.append(f"{record.team_abbreviation} {record.position.lower()}")
    if record.team_abbreviation:
        suggestions.append(f"{record.team_abbreviation} playmaking")

    if other_records:
        for candidate in other_records:
            if candidate.id == record.id:
                continue
            label = (candidate.team_abbreviation or candidate.team_name or "").strip()
            if label:
                suggestion = f"{label} {candidate.position or 'player'}"
                if suggestion not in suggestions:
                    suggestions.append(suggestion)
            if len(suggestions) >= limit + 2:
                break

    return suggestions[:limit]


def recommend_related_players(record, other_records=None, limit=3):
    if record is None:
        return []

    candidates = []
    other_records = other_records or []
    for candidate in other_records:
        if candidate.id == record.id:
            continue
        score = 0
        reasons = []

        if record.team_abbreviation and candidate.team_abbreviation == record.team_abbreviation:
            score += 4
            reasons.append(f"same team ({record.team_abbreviation})")
        elif record.team_name and candidate.team_name == record.team_name:
            score += 3
            reasons.append(f"same club ({record.team_name})")

        if record.position and candidate.position and record.position.lower() == candidate.position.lower():
            score += 3
            reasons.append(f"same position ({record.position})")

        if record.source and candidate.source == record.source:
            score += 2
            reasons.append(f"same source ({record.source})")

        shared_tokens = set(_normalize_keywords(f"{record.name} {record.description}")) & set(
            _normalize_keywords(f"{candidate.name} {candidate.description}")
        )
        if shared_tokens:
            score += min(len(shared_tokens), 3)
            reasons.append(f"shared context: {', '.join(sorted(shared_tokens)[:2])}")

        if score > 0:
            candidates.append({
                "record": candidate,
                "score": score,
                "reason": "; ".join(reasons[:3]),
            })

    candidates.sort(key=lambda item: (-item["score"], item["record"].name.lower(), item["record"].id))
    return candidates[:limit]
