import httpx
import certifi
import ssl

print(f"python-httpx version: {httpx.__version__}")
print(f"certifi version: {certifi.__version__}")
print(f"certifi ca bundle path: {certifi.where()}")
print(f"Default SSL context cafile: {ssl.get_default_verify_paths().cafile}")

target_url_google = "https://www.google.com"
target_url_anthropic = (
    "https://api.anthropic.com/v1/messages"  # Expect 405 if successful
)

print(f"\n--- Testing {target_url_google} (default HTTP version) ---")
try:
    with httpx.Client() as client:
        response = client.get(target_url_google, timeout=15.0)
        print(f"Status Code: {response.status_code}")
        print(f"HTTP Version: {response.http_version}")
        # print(f"Response Headers: {response.headers}")
    print(f"SUCCESS: httpx GET to {target_url_google} was successful.")
except httpx.RequestError as exc:
    print(f"ERROR: httpx GET to {target_url_google} failed: {exc}")
    # print(f"Request details: {exc.request}")
except Exception as e:
    print(f"UNEXPECTED ERROR with {target_url_google}: {e}")


print(f"\n--- Testing {target_url_anthropic} with HTTP/1.1 ---")
try:
    # http2=False forces HTTP/1.1
    with httpx.Client(http2=False) as client:
        # Add a dummy header that the Anthropic API might expect, even for a GET
        headers = {
            "x-api-key": "dummy-key-not-used-for-auth-on-get",
            "anthropic-version": "2023-06-01",
        }
        response = client.get(target_url_anthropic, headers=headers, timeout=15.0)
        print(f"Status Code: {response.status_code}")
        print(f"HTTP Version: {response.http_version}")
        # print(f"Response Headers: {response.headers}")
        # print(f"Response Content: {response.text}")
    print(f"SUCCESS: httpx GET to {target_url_anthropic} (forcing HTTP/1.1) completed.")
    if response.status_code == 405:
        print("Received expected 405 Method Not Allowed, which is good for this test.")
except httpx.RequestError as exc:
    print(
        f"ERROR: httpx GET to {target_url_anthropic} (forcing HTTP/1.1) failed: {exc}"
    )
    # print(f"Request details: {exc.request}")
except Exception as e:
    print(f"UNEXPECTED ERROR with {target_url_anthropic} (forcing HTTP/1.1): {e}")

print(f"\n--- Testing {target_url_anthropic} with HTTP/2 (default) ---")
try:
    # http2=True is default, but being explicit
    with httpx.Client(http2=True) as client:
        headers = {
            "x-api-key": "dummy-key-not-used-for-auth-on-get",
            "anthropic-version": "2023-06-01",
        }
        response = client.get(target_url_anthropic, headers=headers, timeout=15.0)
        print(f"Status Code: {response.status_code}")
        print(f"HTTP Version: {response.http_version}")
        # print(f"Response Headers: {response.headers}")
        # print(f"Response Content: {response.text}")
    print(f"SUCCESS: httpx GET to {target_url_anthropic} (HTTP/2 default) completed.")
    if response.status_code == 405:
        print("Received expected 405 Method Not Allowed, which is good for this test.")
except httpx.RequestError as exc:
    print(f"ERROR: httpx GET to {target_url_anthropic} (HTTP/2 default) failed: {exc}")
    # print(f"Request details: {exc.request}")
except Exception as e:
    print(f"\nUNEXPECTED ERROR: {e}")
