"""El orden de los accesos chicos de la Home: Restaurantes y Turbo van fijos arriba; los otros seis se ordenan por lo
que la persona más usa (la afinidad propia del motor), y sin uso propio quedan en el orden de siempre."""

from psycopg import Connection

from ..agent.tools import VERTICAL_LABELS
from ..text import contract_articles
from .predict import next_verticals

HOME_FIXED = ("restaurantes", "turbo")
HOME_ORDERABLE = ("supermercado", "farmacia", "mall", "licores", "conveniencia", "chocolateria")


def home_verticals(conn: Connection, user_id: str) -> dict:
    """`{fixed, order, personalized}`: `order` son los 6 de `HOME_ORDERABLE`. Primero los que la persona usa (afinidad
    > 0), por puntaje de la predicción; después el resto, en el orden de `HOME_ORDERABLE`, para que la Home de quien
    no ha usado nada no cambie con la población. Solo el primero lleva `reason`, y solo si la persona lo usa."""
    scores = {s.vertical: s for s in next_verticals(conn, user_id)}
    used = [v for v in scores if v in HOME_ORDERABLE and scores[v].affinity > 0]  # `next_verticals` ya los ordena
    ids = used + [v for v in HOME_ORDERABLE if v not in used]
    order = [{"id": v, "score": round(scores[v].score, 4), "reason": None} for v in ids]
    if used:
        order[0]["reason"] = {
            "text": contract_articles(f"Porque pides seguido en {VERTICAL_LABELS[used[0]]}."),
            "basis": [{"kind": "afinidad_vertical", "id": used[0], "source": "eventos"}],
        }
    return {"fixed": list(HOME_FIXED), "order": order, "personalized": bool(used)}
