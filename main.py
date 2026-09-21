import os
import hashlib
import base64
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse

app = FastAPI()

# -----------------------------
# Existing account-deletion config
# -----------------------------

VERIFICATION_TOKEN = os.environ["EBAY_VERIFICATION_TOKEN"]
PUBLIC_BASE_URL = os.environ["PUBLIC_BASE_URL"].rstrip("/")

ACCOUNT_DELETION_ENDPOINT = (
    f"{PUBLIC_BASE_URL}/ebay/account-deletion"
)

# -----------------------------
# eBay Production OAuth config
# -----------------------------

EBAY_CLIENT_ID = os.environ["EBAY_CLIENT_ID"]
EBAY_CLIENT_SECRET = os.environ["EBAY_CLIENT_SECRET"]
EBAY_RUNAME = os.environ["EBAY_RUNAME"]
EBAY_SCOPES = os.environ["EBAY_SCOPES"]

EBAY_AUTHORIZE_URL = "https://auth.ebay.com/oauth2/authorize"
EBAY_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"

# Simple temporary CSRF state for first setup.
# Later we can replace this with persistent/session storage.
OAUTH_STATE = secrets.token_urlsafe(32)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "eBay Store Manager API"
    }


# -------------------------------------------------
# eBay account deletion notification verification
# -------------------------------------------------

@app.get("/ebay/account-deletion")
def verify_ebay_endpoint(
    challenge_code: str = Query(..., alias="challenge_code")
):
    raw = (
        challenge_code
        + VERIFICATION_TOKEN
        + ACCOUNT_DELETION_ENDPOINT
    )

    challenge_response = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()

    return JSONResponse(
        content={"challengeResponse": challenge_response},
        status_code=200
    )


@app.post("/ebay/account-deletion")
async def receive_account_deletion(request: Request):
    payload = await request.json()
    print(payload)

    return JSONResponse(
        content={"received": True},
        status_code=200
    )


# -------------------------------------------------
# eBay Production OAuth
# -------------------------------------------------

@app.get("/ebay/oauth/start")
def ebay_oauth_start():
    params = {
        "client_id": EBAY_CLIENT_ID,
        "redirect_uri": EBAY_RUNAME,
        "response_type": "code",
        "scope": EBAY_SCOPES,
        "state": OAUTH_STATE,
        "prompt": "login"
    }

    return RedirectResponse(
        f"{EBAY_AUTHORIZE_URL}?{urlencode(params)}"
    )


@app.get("/ebay/oauth/callback")
async def ebay_oauth_callback(
    code: str = Query(...),
    state: str | None = Query(default=None)
):
    if state and state != OAUTH_STATE:
        return JSONResponse(
            {"error": "Invalid OAuth state"},
            status_code=400
        )

    credentials = f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}"
    basic_auth = base64.b64encode(
        credentials.encode()
    ).decode()

    headers = {
        "Authorization": f"Basic {basic_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": EBAY_RUNAME
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            EBAY_TOKEN_URL,
            headers=headers,
            data=data
        )

    if response.status_code != 200:
        return JSONResponse(
            {
                "error": "Token exchange failed",
                "status_code": response.status_code,
                "details": response.text
            },
            status_code=500
        )

    tokens = response.json()

    # Temporary setup page.
    # Copy the refresh token locally, then store it as a Render secret.
    refresh_token = tokens.get("refresh_token")

    return HTMLResponse(
        f"""
        <html>
        <body>
            <h1>eBay OAuth successful</h1>
            <p>Your eBay account has authorized the application.</p>

            <p><strong>Refresh token:</strong></p>
            <textarea rows="8" cols="100">{refresh_token}</textarea>

            <p>
            Copy this token now and store it securely in Render.
            Do not share it with ChatGPT or anyone else.
            </p>
        </body>
        </html>
        """
    )


@app.get("/ebay/oauth/declined")
def ebay_oauth_declined():
    return HTMLResponse(
        """
        <html>
        <body>
            <h1>eBay authorization declined</h1>
            <p>No access was granted.</p>
        </body>
        </html>
        """
    )
