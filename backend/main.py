from fastapi import FastAPI

app = FastAPI(title="Pathshala AI")

@app.on_event("startup")
def startup_event() -> None:
    # Placeholder for startup tasks
    pass

@app.get("/health")
def health_check():
    return {"status": "healthy"}