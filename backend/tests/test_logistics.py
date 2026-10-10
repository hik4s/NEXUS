from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def register(client: TestClient, suffix: str):
    response = client.post('/api/v1/auth/register', json={
        'company_name': f'Logistics Company {suffix}',
        'company_slug': f'logistics-company-{suffix}',
        'full_name': 'Logistics Admin',
        'email': f'admin-{suffix}@example.com',
        'password': 'StrongPass123!',
    })
    assert response.status_code == 201, response.text
    return response.json()


def create_product(client, headers, company_id, sku):
    response = client.post(f'/api/v1/companies/{company_id}/products', headers=headers, json={
        'name': f'Product {sku}', 'sku': sku, 'price': '100.00', 'cost': '50.00'
    })
    assert response.status_code == 201, response.text
    return response.json()


def create_confirmed_order(client, headers, company_id, product_id, warehouse_id):
    customer = client.post('/api/v1/crm/customers', headers=headers, json={'name': 'Delivery Customer', 'email': f'customer-{uuid4().hex[:8]}@example.com'})
    assert customer.status_code == 201
    order = client.post('/api/v1/sales/orders', headers=headers, json={'customer_id': customer.json()['id'], 'items': [{'product_id': product_id, 'quantity': 1}]})
    assert order.status_code == 201, order.text
    confirm = client.patch(f"/api/v1/sales/orders/{order.json()['id']}/status", headers=headers, json={'status': 'confirmed', 'warehouse_id': warehouse_id})
    assert confirm.status_code == 200, confirm.text
    return confirm.json()


def test_delivery_lifecycle_with_driver_vehicle_and_tracking():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        headers = {'Authorization': f"Bearer {owner['access_token']}"}
        company_id = owner['user']['company_id']
        product = create_product(client, headers, company_id, f'SKU-{suffix}')
        warehouse = client.post('/api/v1/inventory/warehouses', headers=headers, json={'name': 'Dispatch', 'code': f'DSP-{suffix}'})
        assert warehouse.status_code == 201
        receipt = client.post('/api/v1/inventory/movements', headers=headers, json={'warehouse_id': warehouse.json()['id'], 'product_id': product['id'], 'movement_type': 'receipt', 'quantity': 5})
        assert receipt.status_code == 201
        order = create_confirmed_order(client, headers, company_id, product['id'], warehouse.json()['id'])

        driver = client.post('/api/v1/logistics/drivers', headers=headers, json={'full_name': 'João Motorista', 'license_number': f'CNH-{suffix}', 'phone': '11999999999'})
        assert driver.status_code == 201, driver.text
        vehicle = client.post('/api/v1/logistics/vehicles', headers=headers, json={'plate': f'ABC{suffix[:4].upper()}', 'vehicle_type': 'van'})
        assert vehicle.status_code == 201, vehicle.text
        delivery = client.post('/api/v1/logistics/deliveries', headers=headers, json={'sales_order_id': order['id'], 'recipient_name': 'Maria', 'recipient_phone': '11988888888', 'street': 'Rua A', 'number': '100', 'neighborhood': 'Centro', 'city': 'Presidente Prudente', 'state': 'SP'})
        assert delivery.status_code == 201, delivery.text
        delivery_id = delivery.json()['id']
        assert delivery.json()['status'] == 'pending'

        assigned = client.patch(f'/api/v1/logistics/deliveries/{delivery_id}/assign', headers=headers, json={'driver_id': driver.json()['id'], 'vehicle_id': vehicle.json()['id']})
        assert assigned.status_code == 200, assigned.text
        assert assigned.json()['status'] == 'assigned'

        dispatched = client.patch(f'/api/v1/logistics/deliveries/{delivery_id}/status', headers=headers, json={'status': 'in_transit', 'description': 'Saiu para entrega', 'latitude': '-22.120000', 'longitude': '-51.390000'})
        assert dispatched.status_code == 200, dispatched.text
        assert dispatched.json()['status'] == 'in_transit'

        delivered = client.patch(f'/api/v1/logistics/deliveries/{delivery_id}/status', headers=headers, json={'status': 'delivered', 'proof_type': 'signature', 'proof_reference': 'signed-by-maria', 'description': 'Recebido pelo cliente'})
        assert delivered.status_code == 200, delivered.text
        assert delivered.json()['status'] == 'delivered'

        tracking = client.get(f'/api/v1/logistics/deliveries/{delivery_id}/tracking', headers=headers)
        assert tracking.status_code == 200
        assert [event['status'] for event in tracking.json()] == ['pending', 'assigned', 'in_transit', 'delivered']


def test_route_enforces_driver_vehicle_and_warehouse_consistency():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        headers = {'Authorization': f"Bearer {owner['access_token']}"}
        company_id = owner['user']['company_id']
        product = create_product(client, headers, company_id, f'SKU-{suffix}')
        warehouse = client.post('/api/v1/inventory/warehouses', headers=headers, json={'name': 'Dispatch', 'code': f'DSP-{suffix}'}).json()
        client.post('/api/v1/inventory/movements', headers=headers, json={'warehouse_id': warehouse['id'], 'product_id': product['id'], 'movement_type': 'receipt', 'quantity': 3})
        order = create_confirmed_order(client, headers, company_id, product['id'], warehouse['id'])
        driver = client.post('/api/v1/logistics/drivers', headers=headers, json={'full_name': 'João', 'license_number': f'CNH-{suffix}'}).json()
        vehicle = client.post('/api/v1/logistics/vehicles', headers=headers, json={'plate': f'XYZ{suffix[:4].upper()}' }).json()
        delivery = client.post('/api/v1/logistics/deliveries', headers=headers, json={'sales_order_id': order['id'], 'recipient_name': 'Cliente', 'street': 'Rua B', 'number': '5', 'city': 'Presidente Prudente', 'state': 'SP'}).json()
        route = client.post('/api/v1/logistics/routes', headers=headers, json={'warehouse_id': warehouse['id'], 'driver_id': driver['id'], 'vehicle_id': vehicle['id'], 'route_date': '2026-10-01'})
        assert route.status_code == 201, route.text
        stop = client.post(f"/api/v1/logistics/routes/{route.json()['id']}/stops", headers=headers, json={'delivery_id': delivery['id'], 'sequence': 1})
        assert stop.status_code == 201, stop.text
        duplicate = client.post(f"/api/v1/logistics/routes/{route.json()['id']}/stops", headers=headers, json={'delivery_id': delivery['id'], 'sequence': 2})
        assert duplicate.status_code == 409


def test_logistics_is_tenant_scoped():
    with TestClient(app) as client:
        one = register(client, uuid4().hex[:8])
        two = register(client, uuid4().hex[:8])
        one_headers = {'Authorization': f"Bearer {one['access_token']}"}
        two_headers = {'Authorization': f"Bearer {two['access_token']}"}
        company_id = one['user']['company_id']
        product = create_product(client, one_headers, company_id, f'SKU-{uuid4().hex[:8]}')
        warehouse_response = client.post('/api/v1/inventory/warehouses', headers=one_headers, json={'name': f'W-{uuid4().hex[:8]}', 'code': f'W-{uuid4().hex[:8]}' })
        assert warehouse_response.status_code == 201, warehouse_response.text
        warehouse = warehouse_response.json()
        receipt = client.post('/api/v1/inventory/movements', headers=one_headers, json={'warehouse_id': warehouse['id'], 'product_id': product['id'], 'movement_type': 'receipt', 'quantity': 2})
        assert receipt.status_code == 201, receipt.text
        order = create_confirmed_order(client, one_headers, company_id, product['id'], warehouse['id'])
        delivery = client.post('/api/v1/logistics/deliveries', headers=one_headers, json={'sales_order_id': order['id'], 'recipient_name': 'Cliente', 'street': 'Rua C', 'number': '10', 'city': 'PP', 'state': 'SP'}).json()
        foreign = client.get(f"/api/v1/logistics/deliveries/{delivery['id']}", headers=two_headers)
        assert foreign.status_code == 404
