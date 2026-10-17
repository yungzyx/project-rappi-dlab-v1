"""Las tablas del backend que la API simulada de la demo sin conexión necesita y que la API no expone: los conceptos con
sus guardias de ofertas, los servicios sin catálogo, la tabla de combinaciones de Rappi (motor/combos.toml) y los
nombres visibles de las verticales. Lo corre `scripts/demo-snapshot.mjs` con el Python de rappi-ia; escribe JSON en la
salida estándar. No toca la base."""

import json

from rappi_ia.agent.grouped_search import SCREEN_VERTICALS
from rappi_ia.agent.tools import VERTICAL_LABELS
from rappi_ia.concepts.taxonomy import load_taxonomy
from rappi_ia.motor.combos import FINE_ORDER, OWN_SIGNALS_ONLY, SERVICES, load_combos
from rappi_ia.offers.guards import is_offerable

taxonomy = load_taxonomy()
combos = load_combos()

print(
    json.dumps(
        {
            "concepts": {
                c.id: {
                    "name": c.name,
                    "emoji": c.emoji,
                    "group": c.parent or c.id,
                    "offerable": is_offerable(c),
                }
                for c in taxonomy.concepts.values()
            },
            "services": {
                key: {
                    "id": taxonomy.services[payload].id,
                    "name": taxonomy.services[payload].name,
                    "pitch": taxonomy.services[payload].pitch,
                    "route": taxonomy.services[payload].route,
                }
                for key, payload in combos.services.items()
            },
            "combos": {
                "version": combos.version,
                "groups": combos.groups,
                "retention": {combo: row.retention_m1 for combo, row in combos.rappi.items()},
                "diminishing": {
                    "reduction_base": combos.diminishing.reduction_base,
                    "decay": combos.diminishing.decay,
                    "service": combos.diminishing.service,
                },
                "services": combos.services,
                "fine_order": list(FINE_ORDER),
                "service_keys": list(SERVICES),
                "own_signals_only": sorted(OWN_SIGNALS_ONLY),
            },
            "vertical_labels": VERTICAL_LABELS,
            "screen_verticals": SCREEN_VERTICALS,
        },
        ensure_ascii=False,
    )
)
