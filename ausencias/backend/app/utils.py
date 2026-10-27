from datetime import datetime, timedelta, timezone


def now() -> datetime:
    """Horário atual em UTC (naive) — padrão de armazenamento do sistema."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_brt(dt: datetime | None) -> datetime | None:
    return dt - timedelta(hours=3) if dt else None


def fmt_dt(dt: datetime | None) -> str:
    """Formata para exibição em Brasília (UTC-3)."""
    return to_brt(dt).strftime("%d/%m/%Y %H:%M") if dt else "-"


def fmt_date(d) -> str:
    return d.strftime("%d/%m/%Y") if d else "-"
