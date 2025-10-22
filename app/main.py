from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import logging
from dotenv import load_dotenv

# Load .env early so config reads values
load_dotenv()

from .routers import webhook, auth

app = FastAPI(title="AgentBot Minimal Secure Template")

# mount webapp static files
app.mount("/webapp", StaticFiles(directory="webapp"), name="webapp")

# include routers
app.include_router(webhook.router)
app.include_router(auth.router)

@app.get("/")
async def root():
    return RedirectResponse(url="/webapp")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.on_event("startup")
def startup_event():
    logging.info("Starting AgentBot minimal template")