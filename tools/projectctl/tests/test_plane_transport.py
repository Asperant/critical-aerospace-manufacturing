from concurrent.futures import ThreadPoolExecutor
from email.utils import formatdate
import json
from threading import Lock
import time

import httpx
import pytest

from projectctl.plane import PlaneConfig, PlaneError, load_config
from projectctl.plane_transport import PlaneStream, rate_headers


def config(interval=1.25):
    return PlaneConfig("http://plane.test", "secret", "test", "beb6dbea-4931-4ce9-b761-a4957c4b33be",
                       request_interval_seconds=interval)


def stream(handler):
    return PlaneStream(config(), httpx.MockTransport(handler))


def test_one_paced_stream_across_clients_and_read_write(monkeypatch):
    import projectctl.plane_transport as transport
    sent = []
    def handler(req):
        sent.append((req.method, transport.monotonic()))
        return httpx.Response(200, json={})
    first, second = stream(handler), stream(handler)
    try:
        first.request("GET", "read/")
        second.request("POST", "create/", json={"name": "test"})
        first.request("GET", "read/")
        assert sent == [("GET", 0), ("POST", 1.25), ("GET", 2.5)]
    finally:
        first.close(); second.close()


@pytest.mark.parametrize("headers,delay", [({"Retry-After": "7"},7),
                                          ({"Retry-After": formatdate(1007, usegmt=True)},7),
                                          ({"X-RateLimit-Reset": "1008"},8),
                                          ({"Retry-After": "invalid"},2), ({},2)])
def test_get_429_waits_for_headers_or_bounded_backoff(headers, delay):
    import projectctl.plane_transport as transport
    sent = []
    def handler(req):
        sent.append(transport.monotonic())
        return httpx.Response(429 if len(sent)==1 else 200, headers=headers if len(sent)==1 else {}, json={})
    client = stream(handler)
    try:
        assert client.request("GET", "read/").status_code == 200
        assert sent == [0, delay]
        assert client.events[0]["rate_limit"]["delay_seconds"] == delay
    finally:
        client.close()


def test_exhaustion_is_five_requests_with_increasing_waits():
    import projectctl.plane_transport as transport
    sent = []
    def handler(req):
        sent.append(transport.monotonic())
        return httpx.Response(429)
    client = stream(handler)
    try:
        with pytest.raises(PlaneError, match="5 attempts"):
            client.request("GET", "read/")
        assert sent == [0,2,6,14,30]
        assert len(client.events) == 5
    finally:
        client.close()


def test_remaining_zero_defers_the_next_read_even_after_success():
    import projectctl.plane_transport as transport
    sent = []
    def handler(req):
        sent.append(transport.monotonic())
        return httpx.Response(200, headers={"X-RateLimit-Remaining":"0", "X-RateLimit-Reset":"1010"}, json={})
    client = stream(handler)
    try:
        client.request("GET", "read/"); client.request("GET", "read/")
        assert sent == [0,10]
    finally:
        client.close()


def test_plain_post_is_not_blindly_retried():
    calls=[]
    def handler(req):
        calls.append(req)
        return httpx.Response(429, headers={"Retry-After":"9"})
    client=stream(handler)
    try:
        assert client.request("POST", "create/", json={}).status_code==429
        assert len(calls)==1
    finally:
        client.close()


def test_requests_never_overlap_even_across_clients_and_threads():
    active, maximum = 0, 0
    lock=Lock()
    def handler(req):
        nonlocal active, maximum
        with lock:
            active += 1; maximum=max(maximum,active)
        time.sleep(.005)  # Actual small overlap opportunity; pacing itself uses the fake clock.
        with lock:
            active -= 1
        return httpx.Response(200,json={})
    clients=[stream(handler),stream(handler)]
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures=[pool.submit(clients[i%2].request,"GET","read/") for i in range(8)]
            assert all(f.result().status_code==200 for f in futures)
        assert maximum==1
    finally:
        for client in clients: client.close()


def test_optional_interval_is_literal_validated_configuration():
    env={"PLANE_BASE_URL":"http://plane.test","PLANE_API_KEY":"secret","PLANE_WORKSPACE_SLUG":"test",
         "PLANE_PROJECT_ID":"beb6dbea-4931-4ce9-b761-a4957c4b33be","PLANE_REQUEST_INTERVAL_SECONDS":"2"}
    assert load_config(None,env).request_interval_seconds==2
    for interval in [0,1.24,float("nan"),float("inf")]:
        with pytest.raises(PlaneError): config(interval)
    assert rate_headers({"Retry-After":"nan", "X-RateLimit-Reset":"invalid"})["delay_seconds"]==2
