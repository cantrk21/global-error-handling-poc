import logging

import pytest
from fastapi.testclient import TestClient

from app.main import app

# False: 500 yanıtını inceleyelim; True olsaydı TestClient exception'ı yeniden atardı.
client = TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize("method,path,body,status,code", [
    ("GET", "/products/999", None, 404, "PRODUCT_NOT_FOUND"),
    ("POST", "/orders/preview", {"product_id": 1, "quantity": 4}, 409, "INSUFFICIENT_STOCK"),
    ("POST", "/orders/preview", {"product_id": 999, "quantity": 1}, 404, "PRODUCT_NOT_FOUND"),
    ("POST", "/orders/preview", {"product_id": 1, "quantity": 0}, 422, "VALIDATION_ERROR"),
    ("GET", "/products/abc", None, 422, "VALIDATION_ERROR"),
    ("GET", "/missing", None, 404, "HTTP_404"),
    ("POST", "/products/1", None, 405, "HTTP_405"),
    ("GET", "/demo/unauthorized", None, 401, "HTTP_401"),
    ("GET", "/demo/crash", None, 500, "INTERNAL_ERROR"),
])
def test_error_contract(method, path, body, status, code):
    response = client.request(method, path, json=body)
    assert response.status_code == status
    error = response.json()["error"]
    assert set(error) == {"code", "message", "details", "request_id"}
    assert error["code"] == code
    assert error["request_id"] == response.headers["x-request-id"]
    assert len(error["request_id"]) == 32


def test_success_and_unchanged_stock():
    for _ in range(2):
        assert client.post("/orders/preview", json={"product_id": 1, "quantity": 3}).status_code == 200
    assert client.get("/products/1").json()["stock"] == 3


def test_http_headers_survive():
    assert client.get("/demo/unauthorized").headers["www-authenticate"] == "Bearer"
    assert "GET" in client.post("/products/1").headers["allow"]


def test_internal_details_only_in_server_logs(caplog):
    with caplog.at_level(logging.ERROR, logger="poc.errors"):
        response = client.get("/demo/crash")
    assert "DEMO_INTERNAL_DETAIL" not in response.text
    assert "RuntimeError" not in response.text
    assert "DEMO_INTERNAL_DETAIL" in caplog.text
    assert response.json()["error"]["request_id"] in caplog.text


def test_validation_does_not_echo_input():
    response = client.post("/orders/preview", json={"product_id": 1, "quantity": "secret-value"})
    assert response.status_code == 422
    assert "secret-value" not in response.text
    assert response.json()["error"]["details"][0]["field"] == "body.quantity"


def test_malformed_json():
    response = client.post("/orders/preview", content="{", headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_request_ids_are_unique_and_server_generated():
    first = client.get("/products/1", headers={"X-Request-ID": "untrusted"})
    second = client.get("/products/1")
    assert first.headers["x-request-id"] != "untrusted"
    assert first.headers["x-request-id"] != second.headers["x-request-id"]
