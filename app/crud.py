"""
CRUD-операции для работы с конструкциями и их сторонами.

Две основные сущности:
  • Construction — рекламная конструкция (щит, экран, арка...)
  • ConstructionSide — сторона конструкции (А, Б, А1...)

Каждая сторона = отдельная запись. Именно стороны попадают в выгрузку.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from .models import Construction, ConstructionSide
from .schemas import ConstructionCreate, ConstructionSideCreate


# ════════════════════════════════════════════════════════════════
# КОНСТРУКЦИИ
# ════════════════════════════════════════════════════════════════

def get_construction(db: Session, construction_id: int) -> Optional[Construction]:
    """Найти конструкцию по внутреннему ID."""
    return db.query(Construction).filter(Construction.id == construction_id).first()


def get_construction_by_gid(db: Session, gid: str) -> Optional[Construction]:
    """Найти конструкцию по gid (ID с сайта boards.by)."""
    return db.query(Construction).filter(Construction.gid == gid).first()


def get_constructions(db: Session, skip: int = 0, limit: int = 100) -> List[Construction]:
    """Получить список конструкций (с пагинацией)."""
    return db.query(Construction).offset(skip).limit(limit).all()


def get_all_constructions(db: Session) -> List[Construction]:
    """Получить все конструкции (для выгрузки)."""
    return db.query(Construction).all()


def create_construction(db: Session, data: ConstructionCreate) -> Construction:
    """Создать новую конструкцию."""
    obj = Construction(**data.model_dump())
    db.add(obj)
    db.flush()
    return obj


def upsert_construction(db: Session, data: ConstructionCreate) -> Construction:
    """Создать конструкцию или обновить, если уже есть с таким gid."""
    existing = get_construction_by_gid(db, data.gid)
    if existing:
        for key, value in data.model_dump().items():
            setattr(existing, key, value)
        db.flush()
        return existing
    return create_construction(db, data)


def delete_construction(db: Session, construction_id: int) -> bool:
    """Удалить конструкцию по ID. Возвращает True если удалено."""
    obj = get_construction(db, construction_id)
    if obj:
        db.delete(obj)
        db.flush()
        return True
    return False


# ════════════════════════════════════════════════════════════════
# СТОРОНЫ КОНСТРУКЦИЙ
# ════════════════════════════════════════════════════════════════

def get_construction_side(db: Session, side_id: int) -> Optional[ConstructionSide]:
    """Найти сторону по ID."""
    return db.query(ConstructionSide).filter(ConstructionSide.id == side_id).first()


def get_construction_sides(db: Session, construction_id: int) -> List[ConstructionSide]:
    """Получить все стороны одной конструкции."""
    return db.query(ConstructionSide).filter(ConstructionSide.construction_id == construction_id).all()


def get_all_sides(db: Session) -> List[ConstructionSide]:
    """Получить все стороны всех конструкций (для выгрузки)."""
    return db.query(ConstructionSide).all()


def create_construction_side(db: Session, data: ConstructionSideCreate) -> ConstructionSide:
    """Создать сторону конструкции."""
    obj = ConstructionSide(**data.model_dump())
    db.add(obj)
    db.flush()
    return obj


def create_side_if_not_exists(db: Session, data: ConstructionSideCreate) -> ConstructionSide:
    """Создать сторону, только если (construction_id, name) ещё нет."""
    existing = (
        db.query(ConstructionSide)
        .filter(
            ConstructionSide.construction_id == data.construction_id,
            ConstructionSide.name == data.name,
        )
        .first()
    )
    if existing:
        return existing
    return create_construction_side(db, data)


def delete_construction_side(db: Session, side_id: int) -> bool:
    """Удалить сторону по ID. Возвращает True если удалено."""
    obj = get_construction_side(db, side_id)
    if obj:
        db.delete(obj)
        db.flush()
        return True
    return False
