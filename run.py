"""
Runner script for:
"A Cloud-Based Multimodal Biometric Attendance Framework with Cryptographic Wage Auditing"
Starts the FastAPI local server with Uvicorn on http://127.0.0.1:8000
"""

import sys
import webbrowser
import uvicorn

def main():
    host = "127.0.0.1"
    port = 8000
    url = f"http://{host}:{port}"

    print("=" * 72)
    print("   MULTIMODAL BIOMETRIC ATTENDANCE & CRYPTOGRAPHIC WAGE AUDIT")
    print("   Research Prototype Testbed Server")
    print("=" * 72)
    print(f"[*] Starting local server at: {url}")
    print(f"[*] Interactive UI:           {url}/")
    print(f"[*] OpenAPI Swagger Docs:     {url}/docs")
    print("[*] Press Ctrl+C to terminate.")
    print("=" * 72)

    # Automatically open default browser after a brief moment
    try:
        import threading
        import time
        def open_browser():
            time.sleep(1.2)
            webbrowser.open(url)
        threading.Thread(target=open_browser, daemon=True).start()
    except Exception:
        pass

    uvicorn.run("app.main:app", host=host, port=port, reload=True)

if __name__ == "__main__":
    main()
