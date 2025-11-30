from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from datetime import datetime

from app.scrapers.hillsborough.scraper import get_recent_cash_buyers
from app.config import API_KEY

app = FastAPI(
    title="Foreclosure Scraper API",
    description="Investor buyer scraping API",
    version="1.0.0"
)

# -------------------------------------------
# HEALTH CHECK
# -------------------------------------------
@app.get("/")
def root():
    return {"status": "ok", "service": "Hillsborough Buyer Scraper"}


# -------------------------------------------
# BACKGROUND TASK WRAPPER
# -------------------------------------------
def run_scraper_task(max_pages, days_back, result_container):
    """Runs the heavy scraper in background and stores result."""
    try:
        investors = get_recent_cash_buyers(
            max_pages=max_pages,
            days_back=days_back
        )
        result_container["data"] = investors
    except Exception as e:
        result_container["error"] = str(e)


# -------------------------------------------
# MAIN SCRAPER ENDPOINT
# -------------------------------------------
@app.get("/investors/hillsborough")
async def investors_hillsborough(
    background_tasks: BackgroundTasks,
    key: str = Query(None, alias="key"),
    max_pages: int = 450,
    days_back: int = 180
):
    """
    Example:
    /investors/hillsborough?key=YOUR_KEY&max_pages=450&days_back=180
    """

    # Authenticate API key
    if key != API_KEY:
        return JSONResponse(
            status_code=403,
            content={"error": "Invalid API key"}
        )

    # Container for background results
    result = {}

    # Add background task
    background_tasks.add_task(
        run_scraper_task,
        max_pages,
        days_back,
        result
    )

    # Immediately return (prevents Railway timeouts)
    return {
        "status": "running",
        "message": "Scraper started",
        "timestamp": datetime.utcnow().isoformat(),
        "note": "Check logs to see full execution output."
    }


# -------------------------------------------
# SYNCHRONOUS VERSION (optional)
# For debugging only – not recommended for Railway
# -------------------------------------------
@app.get("/investors/hillsborough/run_sync")
def investors_hillsborough_sync(
    key: str = Query(None, alias="key"),
    max_pages: int = 450,
    days_back: int = 180
):
    if key != API_KEY:
        return JSONResponse(
            status_code=403,
            content={"error": "Invalid API key"}
        )

    investors = get_recent_cash_buyers(
        max_pages=max_pages,
        days_back=days_back
    )

    return {"count": len(investors), "investors": investors}
