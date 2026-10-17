"""`deps.checked`, la revisión de una conexión antes de entregarla, con un pool falso: si Postgres la cortó, además de
descartarla se revisan todas las libres en otro hilo (una sola revisión a la vez), así tras un reinicio de Postgres el
request siguiente no encuentra las muertas una a una."""

import threading

import pytest
from psycopg import OperationalError

from rappi_ia.api import deps


class FakePool:
    """Cuenta las revisiones (`check`); la primera espera a `release` para ver que no se lanza otra encima."""

    def __init__(self, error: Exception | None = None):
        self.error = error
        self.checks = 0
        self.started = threading.Event()
        self.release = threading.Event()
        self.done = threading.Event()

    def check(self):
        self.checks += 1
        self.started.set()
        self.release.wait(timeout=5)
        self.done.set()
        if self.error:
            raise self.error


def broken(conn):
    raise OperationalError("server closed the connection unexpectedly")


def healthy(conn):
    return None


def eventually(condition) -> bool:
    """Lo que pasa en el hilo de la revisión, con un tope de 5 s."""
    for _ in range(500):
        if condition():
            return True
        threading.Event().wait(0.01)
    return False


def test_a_healthy_connection_does_not_check_the_pool():
    pool = FakePool()

    deps.checked(pool, object(), check=healthy)

    assert pool.checks == 0 and not pool.started.wait(timeout=0.1)


def test_a_broken_connection_checks_the_whole_pool_once():
    pool = FakePool()

    with pytest.raises(OperationalError):  # el pool la descarta y entrega otra
        deps.checked(pool, object(), check=broken)
    assert pool.started.wait(timeout=5)
    with pytest.raises(OperationalError):  # otra muerta mientras se revisa: no lanza otra revisión
        deps.checked(pool, object(), check=broken)
    pool.release.set()
    assert eventually(lambda: not deps._pool_check.locked())  # terminó: la próxima vez se revisa de nuevo

    assert pool.checks == 1


def test_a_failed_pool_check_is_logged_and_the_next_cut_checks_again(caplog):
    pool = FakePool(error=RuntimeError("the pool is closed"))
    pool.release.set()

    with pytest.raises(OperationalError):
        deps.checked(pool, object(), check=broken)
    assert eventually(lambda: "No se pudo revisar el pool" in caplog.text and not deps._pool_check.locked())
    with pytest.raises(OperationalError):
        deps.checked(pool, object(), check=broken)

    assert eventually(lambda: pool.checks == 2)
