from fastapi import FastAPI

app = FastAPI()

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/test-import")
def test_import():
    import sys
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, root)
    try:
        from database import execute
        rs = execute("SELECT COUNT(*) FROM companies")
        return {"count": rs.rows[0][0]}
    except Exception as e:
        return {"error": str(e), "root": root, "files": os.listdir(root)}
