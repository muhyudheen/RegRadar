from fastapi import FastAPI

app = FastAPI(
    title="Regradar API",
    description="API for Regradar, a tool for monitoring and analyzing code changes.",
    version="0.1.0"
)

@app.get("/")
def root():
    return {
        "service": "RegRadar API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'Regradar API'}