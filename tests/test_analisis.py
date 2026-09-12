def test_prioridades(client, cases):
    response = client.get('/analisis/prioridades')
    assert response.status_code == 200
    rows = response.json()
    assert [dict(codigo_producto=p['codigo_producto'], deficit=p['deficit']) for p in rows] == [dict(codigo_producto=p['codigo_producto'], deficit=p['deficit']) for p in cases['validacion_reposicion']['prioridades']]
    assert rows == sorted(rows, key=lambda p: (-p['deficit'], p['stock_actual'], p['codigo_producto']))
    # Confirmar que los datos ejercitan ambos desempates.
    assert any(a['deficit'] == b['deficit'] and a['stock_actual'] != b['stock_actual'] for a, b in zip(rows, rows[1:]))
    assert any(a['deficit'] == b['deficit'] and a['stock_actual'] == b['stock_actual'] and a['codigo_producto'] < b['codigo_producto'] for a, b in zip(rows, rows[1:]))
    assert client.get('/analisis/prioridades').json() == rows


def test_consolidado(client, data):
    for p in data['productos']:
        code = p['codigo_producto']
        response = client.get('/analisis/producto/' + code)
        assert response.status_code == 200
        result = response.json()
        assert result['producto'] == p
        need = None if p['stock_minimo'] is None else p['stock_actual'] < p['stock_minimo']
        assert result['necesita_reposicion'] is need
        assert result['deficit'] == (p['stock_minimo'] - p['stock_actual'] if need else None)
        assert result['proveedores_disponibles'] == client.get('/proveedores/producto/' + code).json()
    assert client.get('/analisis/producto/NO-EXISTE').status_code == 404


def test_datos_faltantes(client, data):
    expected = []
    for p in data['productos']:
        if p['stock_minimo'] is None:
            expected.append(dict(tabla='productos', codigo_producto=p['codigo_producto'], codigo_proveedor=None, campo='stock_minimo'))
    for p in data['producto_proveedor']:
        for field in ('precio_unitario', 'plazo_entrega_dias'):
            if p[field] is None:
                expected.append(dict(tabla='producto_proveedor', codigo_producto=p['codigo_producto'], codigo_proveedor=p['codigo_proveedor'], campo=field))
    expected.sort(key=lambda p: (p['tabla'], p['codigo_producto'], p['codigo_proveedor'] or '', p['campo']))
    response = client.get('/analisis/datos-faltantes')
    assert response.status_code == 200
    assert response.json() == expected
