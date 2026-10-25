"""Respaldo de entrega (`rappi-ia dump-entrega`): la base lista para pasársela a otro equipo, sin las personas del
prototipo.

Trae el catálogo, los conceptos, las capas, los embeddings y la población simulada (`source = 'synthetic'`). No trae a
las personas del prototipo (`source = 'prototype'`), ni sus eventos, búsquedas y pedidos, ni lo que el motor aprendió
de ellas (`data_source = 'prototype'`).

Solo lee la base, en una sola foto: una transacción de solo lectura exporta su snapshot, `pg_dump` vuelca con él todo
salvo los datos de las tablas de personas, y la misma transacción copia de esas tablas solo las filas simuladas. Nada
del prototipo pasa por un archivo. Deja una carpeta con:

- `catalogo.dump`: `pg_dump` en formato custom, sin dueño ni permisos, con las tablas de personas vacías;
- `poblacion-simulada.sql`: las filas simuladas de esas tablas, para `psql`;
- `LEEME.txt`: qué trae y cómo restaurarlo.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path

import psycopg
from psycopg import sql
from rappi_scraper.storage.backup import connection_args, find_pg_dump, run_tool

from . import config

log = logging.getLogger(__name__)

SYNTHETIC = "synthetic"
_USERS = "user_id IN (SELECT user_id FROM public.app_users WHERE source = 'synthetic')"
_ORDERS = f"source = 'synthetic' AND {_USERS}"
# Las tablas con datos de personas (o aprendidos de ellas) y qué filas van, en el orden en que se restauran (las que
# otras referencian, primero). Una tabla nueva con `user_id`, `session_id` o `data_source` tiene que estar aquí: si no,
# `dump-entrega` se niega (`unknown_person_tables`).
PERSON_TABLES = {
    "app_users": "source = 'synthetic'",
    "app_events": f"source = 'synthetic' AND {_USERS}",
    "app_orders": _ORDERS,
    "app_order_lines": f"order_id IN (SELECT order_id FROM public.app_orders WHERE {_ORDERS})",
    "user_segments": _USERS,  # su `source` es la regla que asignó el segmento, no la población
    "user_segment_history": _USERS,
    "user_vertical_affinity": _USERS,
    "replenishment": _USERS,
    "vertical_transitions": "data_source = 'synthetic'",
    "combo_stats": "data_source = 'synthetic'",
    "combo_steps": "data_source = 'synthetic'",
    "cross_sell_rules": "data_source = 'synthetic'",
    "trends": "data_source = 'synthetic'",
    # El grafo de conocimiento: lo curado y lo del catálogo va; de lo aprendido de personas, solo lo simulado.
    "knowledge_edges": "data_source <> 'prototype'",
}
PERSON_COLUMNS = ("user_id", "session_id", "data_source")

DUMP_FILE = "catalogo.dump"
POPULATION_FILE = "poblacion-simulada.sql"
README_FILE = "LEEME.txt"


def unknown_person_tables(conn: psycopg.Connection) -> list[str]:
    """Tablas con columnas de personas que PERSON_TABLES no sabe filtrar (en cualquier esquema que no sea del
    sistema)."""
    rows = conn.execute(
        """SELECT DISTINCT c.table_schema, c.table_name
           FROM information_schema.columns c
           JOIN information_schema.tables t USING (table_schema, table_name)
           WHERE t.table_type = 'BASE TABLE' AND c.column_name = ANY(%s)
             AND c.table_schema NOT IN ('pg_catalog', 'information_schema')
           ORDER BY 1, 2""",
        (list(PERSON_COLUMNS),),
    ).fetchall()
    return [f"{schema}.{table}" for schema, table in rows if schema != "public" or table not in PERSON_TABLES]


def _columns(conn: psycopg.Connection, table: str) -> list[str]:
    """Las columnas que se pueden copiar (sin las generadas), en orden."""
    rows = conn.execute(
        """SELECT attname FROM pg_attribute
           WHERE attrelid = %s::regclass AND attnum > 0 AND NOT attisdropped AND attgenerated = ''
           ORDER BY attnum""",
        (f"public.{table}",),
    ).fetchall()
    return [name for (name,) in rows]


def _write_population(conn: psycopg.Connection, path: Path, source_name: str) -> dict[str, int]:
    """Las filas simuladas de cada tabla de personas, como `COPY … FROM stdin` en una transacción. Devuelve cuántas."""
    counts = {}
    with path.open("wb") as out:
        out.write(
            f"-- Población simulada (source = '{SYNTHETIC}') de la base {source_name}, para restaurar con psql después"
            f" de {DUMP_FILE}.\n\\set ON_ERROR_STOP on\nBEGIN;\n".encode()
        )
        for table, condition in PERSON_TABLES.items():
            columns = sql.SQL(", ").join(map(sql.Identifier, _columns(conn, table)))
            name = sql.Identifier("public", table)
            header = sql.SQL("COPY {} ({}) FROM stdin;\n").format(name, columns).as_string(conn)
            out.write(header.encode())
            query = sql.SQL("COPY (SELECT {} FROM {} WHERE {}) TO STDOUT").format(columns, name, sql.SQL(condition))
            with conn.cursor().copy(query) as copy:
                for chunk in copy:
                    out.write(chunk)
            out.write(b"\\.\n")
            counts[table] = conn.execute(
                sql.SQL("SELECT count(*) FROM {} WHERE {}").format(name, sql.SQL(condition))
            ).fetchone()[0]
        out.write(b"COMMIT;\n")
    return counts


def _excluded(conn: psycopg.Connection) -> dict[str, int]:
    """Cuántas filas de cada tabla de personas quedan fuera (las del prototipo)."""
    out = {}
    for table, condition in PERSON_TABLES.items():
        query = sql.SQL("SELECT count(*) FROM {} WHERE NOT ({})").format(
            sql.Identifier("public", table), sql.SQL(condition)
        )
        out[table] = conn.execute(query).fetchone()[0]
    return out


def _readme(source_name: str, last_migration: str, counts: dict[str, int], excluded: dict[str, int]) -> str:
    when = f"{datetime.now():%d-%m-%Y %H:%M}"
    return f"""Respaldo de entrega de rappi-dlab: base {source_name} al {when}, migraciones hasta {last_migration}.

Trae el catálogo (tiendas, productos, menús y precios), los conceptos, las capas de datos, los embeddings y documentos
de búsqueda, y la población simulada (source = '{SYNTHETIC}'). Es simulada: no es evidencia.
  personas: {counts["app_users"]}, eventos: {counts["app_events"]}, pedidos: {counts["app_orders"]}

No trae a las personas del prototipo (source = 'prototype'), ni sus eventos, búsquedas y pedidos, ni lo que el motor y
el grafo aprendieron de ellas (data_source = 'prototype'). Quedaron fuera:
  personas: {excluded["app_users"]}, eventos: {excluded["app_events"]}, pedidos: {excluded["app_orders"]}

Restaurar en Postgres 17 con pgvector 0.8 (unaccent, pg_trgm y pg_prewarm vienen con Postgres):

  createdb rappi
  pg_restore --no-owner --no-privileges --dbname=rappi {DUMP_FILE}
  psql --dbname=rappi --file={POPULATION_FILE}
  vacuumdb --analyze-only --dbname=rappi

Con un rol que no es superusuario, pg_restore no puede comentar las extensiones: se saltan con
  pg_restore --list {DUMP_FILE} | grep -v 'COMMENT - EXTENSION' > lista.txt
y agregando --use-list=lista.txt al pg_restore de arriba.

Después, en rappi-ia/ (con DATABASE_URL apuntando a esa base): make migrate (no debería quedar nada pendiente) y
make serve. Las dos partes van juntas: {DUMP_FILE} solo trae las tablas de personas vacías.
"""


def build_delivery(database_url: str, out_dir: Path | None = None) -> Path:
    """Arma la carpeta de entrega (ver el docstring del módulo) y devuelve su ruta. Nunca escribe en la base."""
    out_dir = out_dir or config.DATA_DIR / "entrega"
    target = out_dir / f"entrega_{datetime.now():%Y%m%d-%H%M%S}"
    partial = target.with_name(target.name + ".part")
    pg_dump = find_pg_dump()
    args, env = connection_args(database_url)
    with psycopg.connect(database_url) as conn:
        conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        conn.read_only = True
        unknown = unknown_person_tables(conn)
        if unknown:
            raise RuntimeError(
                f"Tablas con datos de personas que el respaldo no sabe filtrar: {', '.join(unknown)}. Agrégalas a "
                "PERSON_TABLES (rappi_ia/delivery.py) antes de entregar."
            )
        source_name = conn.info.dbname
        last_migration = conn.execute("SELECT max(name) FROM schema_migrations").fetchone()[0]
        snapshot = conn.execute("SELECT pg_export_snapshot()").fetchone()[0]
        partial.mkdir(parents=True)
        try:
            excluded_data = [f"--exclude-table-data=public.{table}" for table in PERSON_TABLES]
            command = [pg_dump, "--format=custom", "--no-owner", "--no-privileges", f"--snapshot={snapshot}"]
            run_tool("pg_dump", [*command, *excluded_data, f"--file={partial / DUMP_FILE}", *args], env=env)
            pg_restore = str(Path(pg_dump).with_name("pg_restore"))
            run_tool("pg_restore --list", [pg_restore, "--list", str(partial / DUMP_FILE)], capture_output=True)
            counts = _write_population(conn, partial / POPULATION_FILE, source_name)
            excluded = _excluded(conn)
            readme = _readme(source_name, last_migration, counts, excluded)
            (partial / README_FILE).write_text(readme, encoding="utf-8")
        except BaseException:
            shutil.rmtree(partial, ignore_errors=True)
            raise
        conn.rollback()
    partial.rename(target)
    log.info("Respaldo de entrega en %s", target)
    return target
