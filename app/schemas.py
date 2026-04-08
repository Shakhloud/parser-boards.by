"""
Схемы данных (Pydantic) и логика нормализации для парсера boards.by.

Структура:
  1. Справочники — какие значения допустимы для display_type и construction_format
  2. Маппинг — как исходные значения с сайта превращаются в нормализованные
  3. Функции нормализации — обработка display_type, construction_format, размера
  4. Схемы для создания/чтения записей в БД
  5. Схема для выгрузки — точно по формату из задания
"""

from enum import Enum
from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, Field, field_validator
import re


# ════════════════════════════════════════════════════════════════
# 1. СПРАВОЧНИКИ — допустимые нормализованные значения
# ════════════════════════════════════════════════════════════════

class DisplayType(str, Enum):
    """Тип отображения рекламной поверхности."""
    PRISMATIC = "Призматрон"    # Призматрон, Призмавижн
    SCROLLER = "Скроллер"       # Скролл
    VIDEO_SCREEN = "Видеоэкран" # LED-экран, Светодиодный экран, Экран
    STATIC = "Статика"          # Обычная плоскость без смены изображения


class ConstructionFormat(str, Enum):
    """Формат конструкции (тип сооружения)."""
    BILLBOARD = "Билборды"           # Билборд
    ARCH = "Арки"                    # Арка
    BRIDGE = "Мосты"                 # Путепровод
    FIREWALL = "Брандмауэры"         # Брандмауэр
    CITYBOARD = "Ситиборды"          # Ситиборд
    CITY_FORMAT = "Сити-форматы"     # Световой короб
    ATYPICAL = "Нетиповые форматы"   # Юнипол, Мегаборд и всё остальное


# ════════════════════════════════════════════════════════════════
# 2. МАППИНГ — исходное значение с сайта → нормализованное
# ════════════════════════════════════════════════════════════════
#
# Как пользоваться:
#   normalized = DISPLAY_TYPE_MAP.get("Призмавижн")  # → "Призматрон"
#   normalized = CONSTRUCTION_FORMAT_MAP.get("Путепровод")  # → "Мосты"
#
# Если значения нет в маппинге:
#   display_type → None (поле опциональное)
#   construction_format → "Нетиповые форматы" (по заданию)
#

DISPLAY_TYPE_MAP = {
    # Исходное с сайта          → Нормализованное
    "Призматрон":               DisplayType.PRISMATIC.value,
    "Призмавижн":               DisplayType.PRISMATIC.value,
    "Скролл":                   DisplayType.SCROLLER.value,
    "LED - экран":              DisplayType.VIDEO_SCREEN.value,
    "Светодиодный экран":       DisplayType.VIDEO_SCREEN.value,
    "Экран":                    DisplayType.VIDEO_SCREEN.value,
}

CONSTRUCTION_FORMAT_MAP = {
    # Исходное с сайта          → Нормализованное
    "Билборд":                  ConstructionFormat.BILLBOARD.value,
    "Арка":                     ConstructionFormat.ARCH.value,
    "Путепровод":               ConstructionFormat.BRIDGE.value,
    "Брандмауэр":               ConstructionFormat.FIREWALL.value,
    "Ситиборд":                 ConstructionFormat.CITYBOARD.value,
    "Световой короб":           ConstructionFormat.CITY_FORMAT.value,
    "Юнипол":                   ConstructionFormat.ATYPICAL.value,
    "Мегаборд":                 ConstructionFormat.ATYPICAL.value,
}


# ════════════════════════════════════════════════════════════════
# 3. ФУНКЦИИ НОРМАЛИЗАЦИИ
# ════════════════════════════════════════════════════════════════

def normalize_display_type(raw: Optional[str]) -> Optional[str]:
    """
    Превращает исходное значение с сайта в нормализованное.

    Примеры:
        "Призмавижн"       → "Призматрон"
        "LED - экран"      → "Видеоэкран"
        "Скролл"           → "Скроллер"
        None               → None
        "Что-то странное"  → None  (нет в справочнике)
    """
    if not raw:
        return None
    return DISPLAY_TYPE_MAP.get(raw.strip())


def normalize_construction_format(raw: Optional[str]) -> str:
    """
    Превращает исходное значение с сайта в нормализованное.
    Если значение не найдено — возвращает «Нетиповые форматы».

    Примеры:
        "Путепровод"       → "Мосты"
        "Билборд"          → "Билборды"
        None               → "Нетиповые форматы"
        "Что-то странное"  → "Нетиповые форматы"
    """
    if not raw:
        return ConstructionFormat.ATYPICAL.value
    return CONSTRUCTION_FORMAT_MAP.get(raw.strip(), ConstructionFormat.ATYPICAL.value)


def normalize_size(raw: Optional[str]) -> Optional[str]:
    """
    Приводит размер к унифицированному формату: «Ширина x Высота».

    Правила:
        • Разделитель → x  (вместо *, х, ×)
        • Убрать «м», «мм», лишние пробелы
        • Десятичный разделитель → точка (вместо запятой)

    Примеры:
        "2,0х6,0 м."  → "2.0x6.0"
        "8 х 4 м."    → "8x4"
        "6*3м"        → "6x3"
        "1,2x1,8"     → "1.2x1.8"
    """
    if not raw:
        return None

    s = raw.strip()

    # Убираем «м», «мм» с точками и пробелами
    s = re.sub(r"\s*мм?\.?", "", s, flags=re.IGNORECASE)

    # Заменяем разделители *, х, ×, Х на x
    s = re.sub(r"[*х×Х]", "x", s)

    # Запятая → точка (десятичный разделитель)
    s = s.replace(",", ".")

    # Убираем пробелы вокруг x
    s = re.sub(r"\s*x\s*", "x", s)

    # Убираем оставшиеся лишние пробелы
    s = s.strip()

    return s if s else None


# ════════════════════════════════════════════════════════════════
# 4. СХЕМЫ ДЛЯ РАБОТЫ С БД (создание / чтение)
# ════════════════════════════════════════════════════════════════

# --- Конструкция ---

class ConstructionCreate(BaseModel):
    """Данные для создания записи о конструкции."""
    gid: str = Field(..., description="ID с сайта boards.by")
    address: str = Field(..., description="Полный адрес")
    lon: float = Field(..., description="Долгота")
    lat: float = Field(..., description="Широта")
    construction_format: str = Field(..., description="Нормализованный формат: Билборды, Арки, Мосты...")
    display_type: Optional[str] = Field(None, description="Нормализованный тип: Призматрон, Скроллер...")
    lighting: Optional[bool] = Field(None, description="Подсветка: true/false/null")
    source_url: Optional[str] = Field(None, description="URL карточки на boards.by")
    raw_data: Optional[str] = Field(None, description="Сырой JSON для отладки")


class ConstructionRead(BaseModel):
    """Данные конструкции при чтении из БД."""
    id: int
    gid: str
    address: str
    lon: float
    lat: float
    construction_format: str
    display_type: Optional[str] = None
    lighting: Optional[bool] = None
    source_url: Optional[str] = None
    sides: List["ConstructionSideRead"] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Сторона конструкции ---

class ConstructionSideCreate(BaseModel):
    """Данные для создания записи о стороне конструкции."""
    construction_id: int = Field(..., description="ID родительской конструкции")
    name: str = Field(..., description="Название стороны: А, Б, А1... Если нет — gid")
    size: Optional[str] = Field(None, description="Нормализованный размер: «6x3»")
    material: Optional[str] = Field(None, description="Материал: баннер, самоклейка...")
    display_type: Optional[str] = Field(None, description="Тип отображения стороны")
    lighting: Optional[bool] = Field(None, description="Подсветка стороны")
    source_url: Optional[str] = Field(None, description="URL стороны на boards.by")
    raw_data: Optional[str] = Field(None, description="Сырой JSON для отладки")


class ConstructionSideRead(BaseModel):
    """Данные стороны при чтении из БД."""
    id: int
    construction_id: int
    name: str
    size: Optional[str] = None
    material: Optional[str] = None
    display_type: Optional[str] = None
    lighting: Optional[bool] = None
    source_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Обновляем forward reference
ConstructionRead.model_rebuild()


# ════════════════════════════════════════════════════════════════
# 5. СХЕМА ВЫГРУЗКИ — точно по формату из задания
# ════════════════════════════════════════════════════════════════
#
# Целевой формат:
# {
#   "construction_sides": [
#     {
#       "gid": "...",
#       "address": "...",
#       "name": "...",
#       "lon": 0,
#       "lat": 0,
#       "construction_format": "...",
#       "display_type": "...",
#       "lighting": true/false/null,
#       "size": "...",
#       "material": "..."
#     }
#   ]
# }
#

class ConstructionSideExport(BaseModel):
    """Одна строка выгрузки — одна сторона конструкции."""
    gid: str
    address: str
    name: str
    lon: float
    lat: float
    construction_format: str
    display_type: Optional[str] = None
    lighting: Optional[bool] = None
    size: Optional[str] = None
    material: Optional[str] = None

    @field_validator("size", mode="before")
    @classmethod
    def normalize_size_field(cls, v):
        return normalize_size(v)


class ExportResult(BaseModel):
    """Целевой формат выгрузки result.json."""
    construction_sides: List[ConstructionSideExport]
