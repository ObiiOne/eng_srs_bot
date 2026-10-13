import json
from dataclasses import dataclass
from pathlib import Path


class VerbConfigError(Exception):
    pass


@dataclass(frozen=True)
class VerbEntry:
    base: str
    past: str
    pp: str
    ru: str

    @property
    def english_display(self) -> str:
        return f"{self.base} {self.past} {self.pp}"


def load_verbs(path: str) -> list[VerbEntry]:
    p = Path(path)
    if not p.exists():
        raise VerbConfigError(f"Файл глаголов не найден: {path}")
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise VerbConfigError(f"Битый JSON: {e}") from e

    if not isinstance(raw, list):
        raise VerbConfigError("Корень JSON должен быть массивом")

    seen: set[str] = set()
    entries: list[VerbEntry] = []

    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise VerbConfigError(f"Элемент #{i} — не объект")
        for field in ("base", "past", "pp", "ru"):
            if field not in item:
                raise VerbConfigError(f"Элемент #{i}: нет поля {field!r}")
            if not isinstance(item[field], str) or not item[field].strip():
                raise VerbConfigError(
                    f"Элемент #{i}: поле {field!r} пустое или не строка"
                )

        base = item["base"].strip().lower()
        past = item["past"].strip().lower()
        pp = item["pp"].strip().lower()
        ru = item["ru"].strip()

        if base in seen:
            raise VerbConfigError(f"Дубликат base: {base!r}")
        seen.add(base)

        entries.append(VerbEntry(base=base, past=past, pp=pp, ru=ru))

    return entries
    