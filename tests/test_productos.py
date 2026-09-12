def test_productos(client, data):
    response = client.get('/productos')
    assert response.status_code == 200
    assert response.json() == sorted(data['productos'], key=lambda p: p['codigo_producto'])
    for row in response.json():
        assert client.get('/productos/' + row['codigo_producto']).json() == row


def test_inexistente(client):
    assert client.get('/productos/NO-EXISTE').status_code == 404
    assert client.get("/productos/x%27%20OR%201%3D1--").status_code == 404


def test_reposicion(client, data):
    expected = [dict(codigo_producto=p['codigo_producto'], nombre=p['nombre'],
                     stock_actual=p['stock_actual'], stock_minimo=p['stock_minimo'],
                     deficit=p['stock_minimo'] - p['stock_actual'])
                for p in data['productos'] if p['stock_minimo'] is not None and p['stock_actual'] < p['stock_minimo']]
    response = client.get('/productos/reposicion')
    assert response.status_code == 200
    assert response.json() == sorted(expected, key=lambda p: p['codigo_producto'])
