"""
CDP Client - Control Chrome via Chrome DevTools Protocol
Uses remote debugging port 9222
"""
import json
import time
import urllib.request
import websocket

class CDPClient:
    def __init__(self, port=9222):
        self.port = port
        self.ws = None
        self._msg_id = 0
        self._results = {}
    
    def _get_debug_url(self, url_filter=None):
        """Get WebSocket debugger URL for a tab"""
        resp = urllib.request.urlopen(f'http://127.0.0.1:{self.port}/json', timeout=5)
        pages = json.loads(resp.read())
        for p in pages:
            if p.get('type') == 'page':
                if url_filter is None or url_filter in p.get('url', ''):
                    return p['webSocketDebuggerUrl']
        # Return first page if no filter match
        for p in pages:
            if p.get('type') == 'page':
                return p['webSocketDebuggerUrl']
        return None
    
    def new_tab(self, url="about:blank"):
        """Open a new tab and return its debug URL"""
        data = json.dumps({"url": url}).encode()
        req = urllib.request.Request(
            f'http://127.0.0.1:{self.port}/json/new?{url}',
            data=data,
            method='PUT'
        )
        resp = urllib.request.urlopen(req, timeout=5)
        page = json.loads(resp.read())
        return page['webSocketDebuggerUrl']
    
    def connect(self, ws_url=None, url_filter=None):
        """Connect to a tab via WebSocket"""
        if ws_url is None:
            ws_url = self._get_debug_url(url_filter)
        if ws_url is None:
            raise Exception("No tab found")
        self.ws = websocket.create_connection(ws_url, timeout=10)
        self._msg_id = 0
        self._results = {}
        return self
    
    def send(self, method, params=None):
        """Send a CDP command and return result"""
        self._msg_id += 1
        msg = {
            "id": self._msg_id,
            "method": method,
            "params": params or {}
        }
        self.ws.send(json.dumps(msg))
        
        # Read response
        while True:
            resp_raw = self.ws.recv()
            resp = json.loads(resp_raw)
            if resp.get("id") == self._msg_id:
                if "error" in resp:
                    raise Exception(f"CDP Error: {resp['error']}")
                return resp.get("result", {})
            # Store event results
            if "method" in resp:
                self._results[resp["method"]] = resp.get("params", {})
    
    def navigate(self, url):
        """Navigate to URL"""
        return self.send("Page.navigate", {"url": url})
    
    def evaluate(self, expression, await_promise=False):
        """Evaluate JavaScript"""
        return self.send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": await_promise
        })
    
    def get_page_text(self):
        """Get page body text"""
        result = self.evaluate("document.body.innerText")
        return result.get("result", {}).get("value", "")
    
    def get_page_html(self):
        """Get page HTML"""
        result = self.evaluate("document.documentElement.outerHTML")
        return result.get("result", {}).get("value", "")
    
    def get_title(self):
        result = self.evaluate("document.title")
        return result.get("result", {}).get("value", "")
    
    def wait_for_load(self, timeout=10):
        """Wait for page to load"""
        start = time.time()
        while time.time() - start < timeout:
            state = self.evaluate("document.readyState")
            val = state.get("result", {}).get("value", "")
            if val == "complete":
                return True
            time.sleep(0.5)
        return False
    
    def click(self, selector):
        """Click an element"""
        return self.evaluate(f"""
            (function() {{
                var el = document.querySelector('{selector}');
                if (el) {{ el.click(); return true; }}
                return false;
            }})()
        """)
    
    def type_text(self, selector, text):
        """Type text into an input"""
        return self.evaluate(f"""
            (function() {{
                var el = document.querySelector('{selector}');
                if (!el) return false;
                el.focus();
                el.value = '{text}';
                el.dispatchEvent(new Event('input', {{bubbles: true}}));
                el.dispatchEvent(new Event('change', {{bubbles: true}}));
                return true;
            }})()
        """)
    
    def close(self):
        if self.ws:
            self.ws.close()

if __name__ == "__main__":
    cdp = CDPClient()
    cdp.connect()
    title = cdp.get_title()
    print("Title:", title)
    text = cdp.get_page_text()[:500]
    print("Text preview:", text)
    cdp.close()
