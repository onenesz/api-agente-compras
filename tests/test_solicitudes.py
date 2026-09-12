import pytest


@pytest.mark.parametrize('estado', [None, 'pendiente', 'aprobada', 'rechazada', 'completada'])
def test_solicitudes(client, data, estado):
    response = client.get('/solicitudes', params={} if estado is None else {'estado': estado})
    assert response.status_code == 200
    expected = [s for s in data['solicitudes'] if estado is None or s['estado'] == estado]
    assert response.json() == sorted(expected, key=lambda s: s['codigo_solicitud'])


def test_pendientes(client, data):
    response = client.get('/solicitudes/pendientes')
    assert response.status_code == 200
    assert response.json() == sorted([s for s in data['solicitudes'] if s['estado'] == 'pendiente'], key=lambda s: s['codigo_solicitud'])
    assert response.json()
    assert all(s['estado'] == 'pendiente' for s in response.json())


def test_estado_invalido(client):
    assert client.get('/solicitudes?estado=otro').status_code == 422
