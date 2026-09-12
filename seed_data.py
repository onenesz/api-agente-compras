import argparse
import json
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg import sql


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA = (
    SCRIPT_DIR.parent / "bd-agente-compras" / "tests_data" / "expected_cases.json"
)
# Orden de inserción: primero las tablas referenciadas por claves foráneas.
TABLES = {
    "productos": (
        ("codigo_producto", "nombre", "categoria", "stock_actual", "stock_minimo"),
        ("codigo_producto",),
    ),
    "proveedores": (("codigo_proveedor", "nombre"), ("codigo_proveedor",)),
    "producto_proveedor": (
        ("codigo_producto", "codigo_proveedor", "precio_unitario", "plazo_entrega_dias"),
        ("codigo_producto", "codigo_proveedor"),
    ),
    "solicitudes": (
        ("codigo_solicitud", "codigo_producto", "cantidad", "estado", "fecha_solicitud"),
        ("codigo_solicitud",),
    ),
}


def connection_settings(env_file):
    load_dotenv(env_file, override=False)
    # La contraseña puede estar vacía si la autenticación del servidor lo permite.
    names = ("HOST", "PORT", "DB", "USER")
    missing = [f"POSTGRES_{name}" for name in names if not os.getenv(f"POSTGRES_{name}")]
    if missing:
        raise ValueError("Faltan variables: " + ", ".join(missing))
    port = int(os.environ["POSTGRES_PORT"])
    if not 1 <= port <= 65535:
        raise ValueError("POSTGRES_PORT debe estar entre 1 y 65535.")
    return {
        "host": os.environ["POSTGRES_HOST"],
        "port": port,
        "dbname": os.environ["POSTGRES_DB"],
        "user": os.environ["POSTGRES_USER"],
        "password": os.getenv("POSTGRES_PASSWORD", ""),
        "connect_timeout": 10,
    }


def load_fixture(path):
    with path.open(encoding="utf-8") as source:
        fixture = json.load(source)
    for table, (columns, keys) in TABLES.items():
        rows = fixture["datos_referencia"][table]
        if len(rows) != fixture["conteos"][table]:
            raise ValueError(f"Conteo incorrecto en el fixture: {table}.")
        seen = set()
        for row in rows:
            if set(row) != set(columns):
                raise ValueError(f"Columnas incorrectas en el fixture: {table}.")
            key = tuple(row[column] for column in keys)
            if key in seen:
                raise ValueError(f"Clave duplicada en el fixture: {table}.")
            seen.add(key)
            if table == "producto_proveedor" and row["precio_unitario"] is not None:
                row["precio_unitario"] = Decimal(row["precio_unitario"])
            if table == "solicitudes":
                row["fecha_solicitud"] = date.fromisoformat(row["fecha_solicitud"])
    return fixture


def upsert_data(cursor, data):
    for table, (columns, keys) in TABLES.items():
        assignments = sql.SQL(", ").join(
            sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(column), sql.Identifier(column))
            for column in columns if column not in keys
        )
        statement = sql.SQL(
            "INSERT INTO public.{} ({}) VALUES ({}) "
            "ON CONFLICT ({}) DO UPDATE SET {}"
        ).format(
            sql.Identifier(table),
            sql.SQL(", ").join(map(sql.Identifier, columns)),
            sql.SQL(", ").join(sql.Placeholder() for _ in columns),
            sql.SQL(", ").join(map(sql.Identifier, keys)),
            assignments,
        )
        cursor.executemany(statement, [tuple(row[c] for c in columns) for row in data[table]])


def require_equal(actual, expected, label):
    if actual != expected:
        raise ValueError(f"Validación fallida: {label}.")


def validate_data(cursor, fixture):
    data = fixture["datos_referencia"]
    codes = [row["codigo_producto"] for row in data["productos"]]
    expected = fixture["validacion_reposicion"]
    cursor.execute(
        """SELECT codigo_producto, stock_minimo - stock_actual AS deficit
           FROM public.productos
           WHERE codigo_producto = ANY(%s) AND stock_actual < stock_minimo
           ORDER BY deficit DESC, stock_actual ASC, codigo_producto ASC""",
        (codes,),
    )
    require_equal(
        cursor.fetchall(),
        [(row["codigo_producto"], row["deficit"]) for row in expected["prioridades"]],
        "reposición, déficit y orden de prioridades",
    )
    exclusions = {
        "excluidos_stock_minimo_null": sql.SQL("stock_minimo IS NULL"),
        "excluidos_stock_igual_minimo": sql.SQL("stock_actual = stock_minimo"),
        "excluidos_stock_mayor_minimo": sql.SQL("stock_actual > stock_minimo"),
    }
    for name, condition in exclusions.items():
        cursor.execute(
            sql.SQL("SELECT codigo_producto FROM public.productos "
                    "WHERE codigo_producto = ANY(%s) AND {} ORDER BY codigo_producto").format(
                condition  # Predicados SQL construidos exclusivamente con literales.
            ),
            (codes,),
        )
        require_equal([row[0] for row in cursor.fetchall()], sorted(expected[name]), name)

    # Verificar todos los campos persistidos, incluidos NULL, precios y estados.
    # Consultar por cada clave evita traer filas ajenas o tablas completas a memoria.
    totals = {}
    for table, (columns, keys) in TABLES.items():
        query = sql.SQL("SELECT {} FROM public.{} WHERE {}").format(
            sql.SQL(", ").join(map(sql.Identifier, columns)),
            sql.Identifier(table),
            sql.SQL(" AND ").join(
                sql.SQL("{} = %s").format(sql.Identifier(key)) for key in keys
            ),
        )
        for row in data[table]:
            cursor.execute(query, tuple(row[key] for key in keys))
            require_equal(cursor.fetchone(), tuple(row[c] for c in columns), table)
        cursor.execute(sql.SQL("SELECT count(*) FROM public.{}").format(sql.Identifier(table)))
        totals[table] = cursor.fetchone()[0]
    return totals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Ruta a expected_cases.json")
    parser.add_argument("--env-file", type=Path, default=SCRIPT_DIR / ".env", help="Ruta al archivo .env")
    args = parser.parse_args()
    try:
        fixture = load_fixture(args.data)
        settings = connection_settings(args.env_file)
        if settings["dbname"] != fixture["base_datos"]:
            raise ValueError("POSTGRES_DB no coincide con la base indicada en el fixture.")
        # El contexto confirma al terminar o revierte todo si hay una excepción.
        with psycopg.connect(**settings) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL lock_timeout = '10s'")
                cursor.execute("SET LOCAL statement_timeout = '60s'")
                upsert_data(cursor, fixture["datos_referencia"])
                totals = validate_data(cursor, fixture)
    except psycopg.Error as error:
        # No imprimir el DSN, la contraseña ni detalles de conexión del servidor.
        state = error.sqlstate or "sin SQLSTATE"
        print(f"Error PostgreSQL ({state}). Carga no confirmada. "
              "Revise conexión, credenciales, tablas y permisos.", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Error: {error} Carga no confirmada.", file=sys.stderr)
        return 1

    print("Carga confirmada. Validaciones de datos, déficit y prioridades correctas.")
    for table, count in fixture["conteos"].items():
        print(f"{table}: {count} registros insertados o actualizados; total en BD: {totals[table]}")
    if any(totals[table] != count for table, count in fixture["conteos"].items()):
        print("Hay filas adicionales: se conservaron. Las expectativas globales de Watson "
              "requieren una base que contenga únicamente el fixture.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
