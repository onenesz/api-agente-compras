import psycopg
import pytest

from app.database import connect_database, get_database
from app.main import app


def test_openapi_docs(client):
    assert client.get('/docs').status_code == 200
    response = client.get('/openapi.json')
    assert response.status_code == 200
    spec = response.json()
    assert spec['info']['title'] == 'API Agente de Compras'
    assert spec['info']['version'] == '1.0.0'
    assert len(spec['paths']) == 9
    operations = []
    for path in spec['paths'].values():
        assert set(path) == {'get'}
        assert path['get']['summary'] and path['get']['description']
        assert path['get']['responses']['200']['content']['application/json']['schema']
        operations.append(path['get']['operationId'])
    assert len(set(operations)) == 9


@pytest.mark.parametrize('method', ['post', 'put', 'patch', 'delete'])
def test_no_escritura(client, method):
    for path in app.openapi()['paths']:
        assert getattr(client, method)(path.replace('{codigo_producto}', 'PRD-001')).status_code == 405


def test_transaccion_solo_lectura():
    with connect_database() as db:
        assert db.execute('SHOW transaction_read_only').fetchone()['transaction_read_only'] == 'on'
        assert db.execute('SHOW transaction_isolation').fetchone()['transaction_isolation'] == 'repeatable read'
        # No cambia filas ni siquiera si la protección se rompiera.
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            db.execute('UPDATE public.productos SET stock_actual = stock_actual WHERE false')
        db.rollback()


def test_error_bd_sin_detalles(client):
    def unavailable():
        raise psycopg.OperationalError('dato sensible de prueba')
    app.dependency_overrides[get_database] = unavailable
    try:
        response = client.get('/productos')
        assert response.status_code == 503
        assert response.json() == {'detail': 'No se pudo consultar PostgreSQL'}
    finally:
        app.dependency_overrides.clear()
