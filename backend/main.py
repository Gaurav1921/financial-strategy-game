from fastapi import FastAPI

app = FastAPI(title="Consortium API")


@app.get("/health")
def health():
    return {"status": "ok"}
