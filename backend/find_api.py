import re

fname = "bundle.js"
print(f"Analyzing {fname}...")

try:
    with open(fname, "r", encoding="utf-8", errors="ignore") as f:
        data = f.read()

    # Pattern 1: Any string starting with /api/
    p1 = re.compile(r'["\'](/api/[^"\']+)["\']')
    matches_p1 = p1.findall(data)
    
    # Pattern 2: fetch call
    p2 = re.compile(r'fetch\s*\(\s*["\']([^"\']+)["\']')
    matches_p2 = p2.findall(data)

    # Pattern 3: Full HTTP URLs
    p3 = re.compile(r'["\'](http://rvrcamd[^"\']+)["\']')
    matches_p3 = p3.findall(data)
    
    print("--- Matches ---")
    all_matches = set(matches_p1 + matches_p2 + matches_p3)
    for m in all_matches:
        print(f"FOUND: {m}")
        
    if not all_matches:
        print("No API patterns found.")

except FileNotFoundError:
    print("bundle.js not found.")
