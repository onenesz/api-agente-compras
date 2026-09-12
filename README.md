# API Agente de Compras

API REST local de solo lectura con FastAPI, psycopg y PostgreSQL. Consulta las cuatro tablas existentes de `db_compras_agente`. No crea tablas, carga datos, aprueba compras ni modifica registros. No incluye IA, autenticación, conexión a Watson ni despliegue.

## Instalación y configuración

Requiere Python 3.10 o posterior y PostgreSQL accesible con la base previamente creada y poblada.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Si ya existe `.env`, conservarlo. Configurar `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER` y `POSTGRES_PASSWORD`. La contraseña puede quedar vacía si PostgreSQL permite esa autenticación. No versionar credenciales. Las variables del proceso tienen precedencia sobre `.env`.

```bash
uvicorn app.main:app --reload
```

Documentación: http://127.0.0.1:8000/docs

Especificación: http://127.0.0.1:8000/openapi.json

La documentación puede abrirse sin conexión a PostgreSQL; las consultas requieren una conexión válida. Swagger UI carga sus recursos desde CDN y necesita acceso a Internet en el navegador.

## Endpoints y futuras tools

Los nueve endpoints están preparados para convertirse posteriormente en tools de watsonx Orchestrate mediante OpenAPI. Cada uno tiene `operationId` único, descripción y esquema Pydantic de respuesta. La integración todavía no se realiza.

| GET | Uso de la futura tool |
| --- | --- |
| `/productos` | Consultar catálogo completo con categoría y stocks. |
| `/productos/reposicion` | Identificar productos bajo el stock mínimo y su déficit. |
| `/productos/{codigo_producto}` | Obtener un producto exacto; 404 si no existe. |
| `/solicitudes` | Consultar todas las solicitudes, con filtro opcional `estado`. |
| `/solicitudes/pendientes` | Consultar únicamente solicitudes pendientes. |
| `/proveedores/producto/{codigo_producto}` | Comparar proveedores asociados, precios y plazos disponibles. |
| `/analisis/prioridades` | Obtener el orden estricto de reposición. |
| `/analisis/producto/{codigo_producto}` | Consultar producto, necesidad de reposición, déficit y proveedores; 404 si no existe. |
| `/analisis/datos-faltantes` | Identificar cada campo incompleto por tabla y claves del registro. |

El filtro de solicitudes acepta `pendiente`, `aprobada`, `rechazada` y `completada`; otros valores producen 422. Ejemplo: `/solicitudes?estado=pendiente`.

Las listas devuelven `[]` si no hay resultados. La consulta de proveedores también devuelve `[]` para un código inexistente. Los errores de PostgreSQL producen 503 con un mensaje genérico sin credenciales ni SQL.

## Reglas y formato

Reposición incluye exclusivamente `stock_actual < stock_minimo`, excluye mínimos null y calcula `deficit = stock_minimo - stock_actual`.

Prioridades ordena **déficit DESC, stock actual ASC, código de producto ASC**, aplicando cada desempate solo cuando empata el criterio anterior. No usa ninguna otra heurística. Los códigos usan la intercalación PostgreSQL `C` para un orden estable y sensible a mayúsculas.

En el análisis consolidado, `producto` contiene los datos del producto y `proveedores_disponibles` las asociaciones del mismo código. Si el mínimo es null, `necesita_reposicion` y `deficit` son null. Si el stock alcanza o supera el mínimo, `necesita_reposicion` es false y `deficit` es null. El déficit solo tiene un valor entero positivo cuando se necesita reposición.

Los valores SQL NULL se conservan como JSON null. Los precios no nulos se serializan como **cadenas decimales exactas** para evitar pérdida de precisión; por ejemplo `"12.50"`. Las fechas usan `YYYY-MM-DD`.

Datos faltantes devuelve una entrada por campo ausente: `tabla`, `codigo_producto`, `codigo_proveedor` (null para productos) y `campo`. Detecta `stock_minimo`, `precio_unitario` y `plazo_entrega_dias`; no rellena valores. Si una asociación tiene dos campos ausentes, produce dos entradas.

Catálogo y reposición se ordenan por código de producto; solicitudes por código de solicitud; proveedores por código de proveedor; datos faltantes por tabla, producto, proveedor y campo. Todas las consultas se basan en PostgreSQL. Cada petición utiliza una transacción `REPEATABLE READ` de solo lectura, manteniendo una instantánea consistente durante análisis con varias consultas. No se modifica el esquema. Un usuario PostgreSQL con permisos SELECT es recomendable como protección adicional.

## Pruebas

Con el entorno virtual activado y `.env` configurado:

```bash
pytest
```

Son pruebas de integración con PostgreSQL real y HTTPX a través de TestClient. Esperan que la base contenga exactamente los datos controlados de `tests_data/expected_cases.json`, copiados del proyecto de datos existente. No cargan fixtures en la base, no insertan ni eliminan datos y no cambian el esquema. Una diferencia con esos datos hace fallar las comparaciones deliberadamente. No apuntar a otra base esperando que los tests la preparen.

Se verifican catálogo, 404, reposición, los dos desempates de prioridades, estados, proveedores y NULL, análisis consolidado, campos faltantes, métodos de escritura rechazados, OpenAPI y `/docs`. También se verifica que PostgreSQL rechace un UPDATE con `WHERE false` (sin filas afectadas) dentro de la transacción de solo lectura.

## Organización

`app/database.py` gestiona conexiones; `app/schemas.py` define contratos Pydantic; `app/routers/` define endpoints; `app/services/compras_service.py` contiene SQL y reglas deterministas. No se necesita ORM ni `models.py`, porque se usa psycopg directamente. El script preexistente `seed_data.py` es una utilidad separada de carga: la API y los tests no lo importan ni ejecutan.

## YAML para watsonx Orchestrate y preparación de Railway

`openapi.yaml` contiene los nueve endpoints en OpenAPI 3.0.3, conforme al requisito publicado del ADK de watsonx Orchestrate. Se exportó desde el contrato de FastAPI adaptando los tipos null a `nullable: true`. `/openapi.json` sigue generándose automáticamente en OpenAPI 3.1.0; no es un archivo guardado en el proyecto. Si cambian los endpoints o schemas, actualizar también el YAML.

Antes de importar `openapi.yaml`, reemplazar su única URL en `servers` (`http://127.0.0.1:8000`) por la URL HTTPS real de la API desplegada. Watson remoto no puede acceder al localhost de tu equipo. La importación en Watson todavía no ha sido probada.

Para Railway, configurar las cinco variables `POSTGRES_*` en el servicio y usar el comando de inicio:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

La base debe ser accesible desde Railway y contener las tablas y los datos existentes. Una base que funciona únicamente en tu equipo no se traslada al subir el código: hace falta alojarla o migrarla por separado. Generar el dominio público HTTPS del servicio y verificar `/docs`, `/openapi.json` y los endpoints antes de importar el YAML. Estas instrucciones no ejecutan ningún despliegue.
