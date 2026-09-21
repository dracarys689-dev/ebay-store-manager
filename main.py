import os
import hashlib

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

app = FastAPI()

VERIFICATION_TOKEN = os.environ["EBAY_VERIFICATION_TOKEN"]
PUBLIC_BASE_URL = os.environ["PUBLIC_BASE_URL"].rstrip("/")

ENDPOINT = f"{PUBLIC_BASE_URL}/ebay/account-deletion"


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "eBay Store Manager API"
    }


@app.get("/ebay/account-deletion")
def verify_ebay_endpoint(
    challenge_code: str = Query(..., alias="challenge_code")
):
    raw = (
        challenge_code
        + VERIFICATION_TOKEN
        + ENDPOINT
    )

    challenge_response = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()

    return JSONResponse(
        content={
            "challengeResponse": challenge_response
        },
        status_code=200
    )


@app.post("/ebay/account-deletion")
async def receive_account_deletion(request: Request):
    payload = await request.json()

    # Pour l'instant, on accuse simplement réception.
    # Plus tard, on ajoutera ici la suppression réelle
    # des données utilisateur correspondantes.
    print(payload)

    return JSONResponse(
        content={"received": True},
        status_code=200
    )
