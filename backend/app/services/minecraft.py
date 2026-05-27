from typing import Optional
import httpx
from app.config import settings

# Microsoft OAuth endpoints
MS_AUTH_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize"
MS_TOKEN_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"

# Xbox Live
XBL_AUTH_URL = "https://user.auth.xboxlive.com/user/authenticate"
XSTS_AUTH_URL = "https://xsts.auth.xboxlive.com/xsts/authorize"

# Minecraft
MC_LOGIN_URL = "https://api.minecraftservices.com/authentication/login"
MC_ENTITLEMENTS_URL = "https://api.minecraftservices.com/entitlements/mcstore"
MC_PROFILE_URL = "https://api.minecraftservices.com/minecraft/profile"


def get_ms_auth_url(state: str) -> str:
    return (
        f"{MS_AUTH_URL}"
        f"?client_id={settings.MICROSOFT_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={settings.MICROSOFT_REDIRECT_URI}"
        f"&scope=XboxLive.signin offline_access"
        f"&state={state}"
    )


class MinecraftAuthResult:
    def __init__(
        self,
        uuid: Optional[str] = None,
        username: Optional[str] = None,
        owns_java: bool = False,
        error: Optional[str] = None,
    ):
        self.uuid = uuid
        self.username = username
        self.owns_java = owns_java
        self.error = error


async def exchange_code(code: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Exchange authorization code for access_token and refresh_token. Returns (access_token, refresh_token, error)."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            MS_TOKEN_URL,
            data={
                "client_id": settings.MICROSOFT_CLIENT_ID,
                "client_secret": settings.MICROSOFT_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
            },
        )
        if resp.status_code != 200:
            return None, None, f"Token exchange failed: {resp.text}"
        data = resp.json()
        return data.get("access_token"), data.get("refresh_token"), None


async def authenticate_minecraft(ms_access_token: str) -> MinecraftAuthResult:
    """Full Xbox Live → XSTS → Minecraft auth chain."""
    async with httpx.AsyncClient() as client:
        # Step 1: XBL auth
        xbl_resp = await client.post(
            XBL_AUTH_URL,
            json={
                "Properties": {
                    "AuthMethod": "RPS",
                    "SiteName": "user.auth.xboxlive.com",
                    "RpsTicket": f"d={ms_access_token}",
                },
                "RelyingParty": "http://auth.xboxlive.com",
                "TokenType": "JWT",
            },
        )
        if xbl_resp.status_code != 200:
            return MinecraftAuthResult(error=f"XBL auth failed: {xbl_resp.status_code}")
        xbl_data = xbl_resp.json()
        xbl_token = xbl_data.get("Token")

        # Step 2: XSTS auth
        xsts_resp = await client.post(
            XSTS_AUTH_URL,
            json={
                "Properties": {
                    "SandboxId": "RETAIL",
                    "UserTokens": [xbl_token],
                },
                "RelyingParty": "rp://api.minecraftservices.com/",
                "TokenType": "JWT",
            },
        )
        if xsts_resp.status_code != 200:
            return MinecraftAuthResult(
                error=f"XSTS auth failed: {xsts_resp.status_code}"
            )
        xsts_data = xsts_resp.json()
        xsts_token = xsts_data.get("Token")
        xuid = xsts_data.get("DisplayClaims", {}).get("xui", [{}])[0].get("xid", None)

        # Step 3: Minecraft login
        mc_resp = await client.post(
            MC_LOGIN_URL,
            json={"identityToken": f"XBL3.0 x={xuid};{xsts_token}"},
        )
        if mc_resp.status_code != 200:
            return MinecraftAuthResult(
                error=f"MC login failed: {mc_resp.status_code}"
            )
        mc_data = mc_resp.json()
        mc_token = mc_data.get("access_token")

        # Step 4: Check entitlements
        ent_resp = await client.get(
            MC_ENTITLEMENTS_URL,
            headers={"Authorization": f"Bearer {mc_token}"},
        )
        owns_java = False
        if ent_resp.status_code == 200:
            ent_data = ent_resp.json()
            for item in ent_data.get("items", []):
                if item.get("name") == "game_minecraft":
                    owns_java = True
                    break

        # Step 5: Get profile
        profile_resp = await client.get(
            MC_PROFILE_URL,
            headers={"Authorization": f"Bearer {mc_token}"},
        )
        uuid = None
        username = None
        if profile_resp.status_code == 200:
            profile_data = profile_resp.json()
            uuid = profile_data.get("id")
            username = profile_data.get("name")

        return MinecraftAuthResult(
            uuid=uuid, username=username, owns_java=owns_java,
        )
