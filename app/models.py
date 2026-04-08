from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


# ════════════════════════════════════════════════════════════════
# Рекламная конструкция — один объект с сайта boards.by
# ════════════════════════════════════════════════════════════════
#
# Конструкция — это физический щит/экран/арка и т.д.
# У одной конструкции может быть несколько сторон (А, Б, А1...),
# каждая сторона хранится отдельно в таблице construction_sides.
#
# Пример: билборд «г. Минск, пр. Независимости, 100»
#   → сторона А (6x3, призматрон)
#   → сторона Б (6x3, статика)
#
class Construction(Base):
    __tablename__ = "constructions"

    # --- Идентификаторы ---
    id = Column(Integer, primary_key=True, index=True)
    gid = Column(
        String,
        nullable=False,
        unique=True,
        index=True,
        comment="ID с сайта boards.by (из URL или карточки). Генерировать нельзя!",
    )

    # --- География ---
    address = Column(
        String,
        nullable=False,
        comment="Полный адрес: «г. Минск, пр. Независимости, 100»",
    )
    lon = Column(
        Float, nullable=False, comment="Долгота (десятичный формат, напр. 27.5766)"
    )
    lat = Column(
        Float, nullable=False, comment="Широта (десятичный формат, напр. 53.9)"
    )

    # --- Характеристики конструкции ---
    construction_format = Column(
        String,
        nullable=False,
        comment=(
            "Нормализованный формат конструкции. "
            "Варианты: Билборды, Арки, Мосты, Брандмауэры, "
            "Ситиборды, Сити-форматы, Нетиповые форматы"
        ),
    )
    display_type = Column(
        String,
        nullable=True,
        comment=(
            "Нормализованный тип отображения. "
            "Варианты: Призматрон, Скроллер, Видеоэкран, Статика, null"
        ),
    )
    lighting = Column(
        Boolean,
        nullable=True,
        comment="Подсветка: true = есть, false = нет, null = неизвестно",
    )

    # --- Служебные поля ---
    source_url = Column(String, nullable=True, comment="URL карточки на boards.by")
    raw_data = Column(Text, nullable=True, comment="Сырой JSON с сайта (для отладки)")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # --- Связи ---
    sides = relationship(
        "ConstructionSide",
        back_populates="construction",
        cascade="all, delete-orphan",
    )


# ════════════════════════════════════════════════════════════════
# Сторона рекламной конструкции — ОДНА СТОРОНА = ОДНА ЗАПИСЬ
# ════════════════════════════════════════════════════════════════
#
# По заданию каждая сторона должна быть отдельной записью.
# Именно эта таблица — основная для выгрузки в JSON/Excel.
#
# Если у конструкции нет сторон — создаём одну запись,
# где name = gid конструкции.
#
class ConstructionSide(Base):
    __tablename__ = "construction_sides"

    # --- Идентификаторы ---
    id = Column(Integer, primary_key=True, index=True)
    construction_id = Column(
        Integer,
        ForeignKey("constructions.id"),
        nullable=False,
        index=True,
        comment="Ссылка на родительскую конструкцию",
    )

    # --- Название стороны ---
    name = Column(
        String,
        nullable=False,
        comment="Название стороны: А, Б, А1 и т.д. Если сторон нет — gid",
    )

    # --- Размер ---
    size = Column(
        String,
        nullable=True,
        comment="Нормализованный размер: «6x3», «3.4x1.8». Формат: Ширина x Высота",
    )

    # --- Материал ---
    material = Column(
        String,
        nullable=True,
        comment="Материал поверхности (баннер, самоклейка и т.д.)",
    )

    # --- Тип отображения стороны (может отличаться от конструкции) ---
    display_type = Column(
        String,
        nullable=True,
        comment="Призматрон / Скроллер / Видеоэкран / Статика / null",
    )

    # --- Подсветка стороны ---
    lighting = Column(
        Boolean,
        nullable=True,
        comment="Подсветка стороны: true / false / null",
    )

    # --- Служебные поля ---
    source_url = Column(String, nullable=True, comment="URL стороны на boards.by")
    raw_data = Column(Text, nullable=True, comment="Сырой JSON стороны (для отладки)")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # --- Связи ---
    construction = relationship("Construction", back_populates="sides")

    # У одной конструкции не может быть двух сторон с одинаковым именем
    __table_args__ = (
        UniqueConstraint("construction_id", "name", name="uq_construction_side_name"),
    )
