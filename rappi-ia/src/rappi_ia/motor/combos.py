"""La tabla de combinaciones de verticales de Rappi (`combos.toml`) y el paso siguiente que sugiere.

Una combinación es el conjunto de grupos gruesos (`rest`, `turbo`, `retail`) que una persona usó en un mes. La tabla es
una correlación (quien pide mucho usa más verticales y además vuelve más), así que el motor la toma como punto de
partida: `expected_retention` la mezcla con lo que se aprende de las personas del prototipo cuando hay suficientes.
"""

import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from rappi_scraper.storage.search import VERTICALS

FILE = Path(__file__).resolve().parent / "combos.toml"
GROUP_ORDER: tuple[str, ...] = ("rest", "turbo", "retail")
NONE_COMBO = "ninguna"
SERVICE_COMBO = "favor"  # RappiFavor: servicio sin catálogo, fuera de la agrupación
# La retención de Rappi pesa como 100 personas al mezclarla con la aprendida; con menos de 30 personas de una
# combinación no se mezcla nada.
LEARNED_RETENTION_PRIOR = 100
LEARNED_RETENTION_MIN_USERS = 30


@dataclass(frozen=True)
class ComboRow:
    combo: str
    users: int
    pct_users: float
    pct_orders: float
    orders_per_user: float
    retention_m1: float
    spend_per_user: float


@dataclass(frozen=True)
class Combos:
    version: str
    groups: dict[str, tuple[str, ...]]
    group_of: dict[str, str]
    rappi: dict[str, ComboRow]
    rappi_total: ComboRow
    source_note: str


def _row(combo: str, data: dict) -> ComboRow:
    row = ComboRow(
        combo=combo,
        users=int(data["usuarios"]),
        pct_users=float(data["pct_usuarios"]),
        pct_orders=float(data["pct_pedidos"]),
        orders_per_user=float(data["pedidos_por_usuario"]),
        retention_m1=float(data["retencion_m1"]),
        spend_per_user=float(data["gasto_por_usuario"]),
    )
    if not 0 <= row.retention_m1 <= 1:
        raise ValueError(f"combos.toml: la retención de «{combo}» debe ser una fracción entre 0 y 1")
    return row


@cache
def load_combos() -> Combos:
    data = tomllib.loads(FILE.read_text(encoding="utf-8"))
    groups = {name: tuple(verticals) for name, verticals in data["grupos"].items()}
    if tuple(groups) != GROUP_ORDER:
        raise ValueError(f"combos.toml: los grupos deben ser {', '.join(GROUP_ORDER)}")
    group_of: dict[str, str] = {}
    for group, verticals in groups.items():
        for vertical in verticals:
            if vertical in group_of:
                raise ValueError(f"combos.toml: el vertical «{vertical}» está en dos grupos")
            group_of[vertical] = group
    missing = set(VERTICALS) - set(group_of)
    unknown = set(group_of) - set(VERTICALS)
    if missing or unknown:
        raise ValueError(f"combos.toml: verticales sin grupo {sorted(missing)} o desconocidos {sorted(unknown)}")
    rappi = {}
    for combo, values in data["combinaciones"].items():
        parts = combo.split("+")
        known = combo == SERVICE_COMBO or (
            all(p in GROUP_ORDER for p in parts) and combo == combo_key(parts) and len(set(parts)) == len(parts)
        )
        if not known:
            raise ValueError(f"combos.toml: la combinación «{combo}» no es de grupos conocidos en orden")
        rappi[combo] = _row(combo, values)
    return Combos(
        version=data["version"],
        groups=groups,
        group_of=group_of,
        rappi=rappi,
        rappi_total=_row("total", data["total"]),
        source_note=data["nota"],
    )


def combo_key(groups: Iterable[str]) -> str:
    """El nombre canónico de un conjunto de grupos: en el orden rest, turbo, retail, unidos por «+»."""
    present = set(groups)
    unknown = present - set(GROUP_ORDER)
    if unknown:
        raise ValueError(f"Grupo desconocido: {sorted(unknown)}")
    return "+".join(g for g in GROUP_ORDER if g in present) or NONE_COMBO


def combo_of_verticals(verticals: Iterable[str]) -> str:
    group_of = load_combos().group_of
    unknown = {v for v in verticals if v not in group_of}
    if unknown:
        raise ValueError(f"Vertical desconocido: {sorted(unknown)}")
    return combo_key(group_of[v] for v in verticals)


def expected_retention(combo: str, learned: dict[str, tuple[int, float]] | None = None) -> float | None:
    """La retención M+1 esperada de una combinación: la de Rappi, mezclada con la aprendida `(personas, retención)` si
    hay al menos `LEARNED_RETENTION_MIN_USERS`; solo la aprendida si Rappi no tiene la fila; `None` si no hay
    ninguna."""
    row = load_combos().rappi.get(combo)
    n, ret = (learned or {}).get(combo, (0, 0.0))
    enough = n >= LEARNED_RETENTION_MIN_USERS
    if row is None:
        return ret if enough else None
    if not enough:
        return row.retention_m1
    return (row.retention_m1 * LEARNED_RETENTION_PRIOR + ret * n) / (LEARNED_RETENTION_PRIOR + n)


def next_step(combo: str, learned: dict[str, tuple[int, float]] | None = None) -> tuple[str, str, float] | None:
    """El grupo que más retención gana al sumarlo: `(grupo_a_sumar, combinación_objetivo, ganancia)`. `None` si la
    persona no tiene pedidos, ya usa los tres grupos o ningún grupo suma retención."""
    if combo == NONE_COMBO:
        return None
    current = expected_retention(combo, learned)
    if current is None:
        return None
    have = combo.split("+")
    best: tuple[str, str, float] | None = None
    for group in GROUP_ORDER:
        if group in have:
            continue
        target = combo_key([*have, group])
        expected = expected_retention(target, learned)
        if expected is None:
            continue
        gain = expected - current
        if gain > 0 and (best is None or gain > best[2]):
            best = (group, target, gain)
    return best
