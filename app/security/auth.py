import secrets

from fastapi import Header, HTTPException, Request, status


async def verify_token(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    """P0 auth: a single development bearer token.

    P1 will replace this with JWT while keeping the same dependency boundary.
    """

    settings = request.app.state.settings
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
        )

    token = authorization.removeprefix("Bearer ").strip()
    if not secrets.compare_digest(
        token.encode("utf-8"),
        settings.dev_token.encode("utf-8"),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token",
        )
