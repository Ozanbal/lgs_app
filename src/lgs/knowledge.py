"""Paketle gelen LGS bilgi tabanını (YAML) yükler."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Any

import yaml


def _load(name: str) -> Any:
    with resources.files("lgs.data").joinpath(f"{name}.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass(frozen=True)
class Subject:
    id: str
    name: str
    code: str
    session: str
    order: int
    question_count: int
    weight: int


@lru_cache(maxsize=None)
def exam_spec() -> dict:
    return _load("sinav")


@lru_cache(maxsize=None)
def curriculum() -> dict[str, list[dict]]:
    return _load("mufredat")


@lru_cache(maxsize=None)
def pattern_catalog() -> dict:
    return _load("soru_kaliplari")


@lru_cache(maxsize=None)
def subjects() -> dict[str, Subject]:
    return {
        sid: Subject(
            id=sid,
            name=d["ad"],
            code=d["kod"],
            session=d["oturum"],
            order=d["sira"],
            question_count=d["soru_sayisi"],
            weight=d["katsayi"],
        )
        for sid, d in exam_spec()["dersler"].items()
    }


def session_subjects(session: str) -> list[Subject]:
    """Bir oturumdaki dersler, kitapçıktaki sırasıyla."""
    return sorted((s for s in subjects().values() if s.session == session), key=lambda s: s.order)


def subject_by_code(code: str) -> Subject:
    for s in subjects().values():
        if s.code == code.upper():
            return s
    raise KeyError(code)


def exam_years() -> list[int]:
    return [e["yil"] for e in exam_spec()["sinavlar"]]


def units(subject: str) -> list[dict]:
    return curriculum().get(subject, [])


def unit_index() -> dict[str, dict]:
    return {u["id"]: u for us in curriculum().values() for u in us}


def patterns(subject: str | None = None) -> list[dict]:
    """Kalıp listesi; ders verilirse o dersin ve genel kalıplar."""
    items = pattern_catalog()["kaliplar"]
    if subject is None:
        return items
    return [p for p in items if p["ders"] in (subject, "genel")]


def pattern_index() -> dict[str, dict]:
    return {p["id"]: p for p in pattern_catalog()["kaliplar"]}


def distractor_index() -> dict[str, dict]:
    return {c["id"]: c for c in pattern_catalog()["celdirici_tipleri"]}
