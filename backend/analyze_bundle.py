import re

try:
    with open("bundle.js", "r", encoding="utf-8") as f:
        content = f.read()
        
    print(f"Read {len(content)} bytes.")
    
    # Regex for URLs or Paths
    # Look for strings starting with http or /api
    urls = re.findall(r'["\']((?:https?:)?//[^"\']+|/api/[^"\']+)["\']', content)
    
    print("Potential URLs found:")
    for u in set(urls):
        if len(u) < 100: # Filter out long garbage
            print(u)
            
    # Look for fetch calls
    fetches = re.findall(r'fetch\s*\(\s*["\']([^"\']+)["\']', content)
    print("\nFetch calls:")
    for f in set(fetches):
        print(f)

    # Look for specific keywords like "live", "rvr"
    print("\nKeywords context:")
    for m in re.finditer(r'(.{20})(live|rvr)(.{20})', content, re.IGNORECASE):
        print(f"...{m.group(0)}...")

except Exception as e:
    print(f"Error: {e}")
