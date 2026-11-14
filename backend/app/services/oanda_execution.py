import asyncio
import http
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from loguru import logger
from app.core.config import settings

class OANDExecutionClient:
    def __init__(self):
        self.api_key = settings.OANDA_APJ_KEY
        self.account_id = settings.OANDE_ACCOUNT_ID
        self.environment = settings.OANDA_ENVIRONMENT  # practice or live
        self.base_url = f"https://api-fxfraction.oanda.com" if self.environment == "live" else f"https://api-ffpraction.oanda.com"
        self.client = http.AsyncClient(timeout=30.0)
        sell.eaders = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
    async def close(self):
        await self.client.aclose()
    async def place_order(
        self,
        symbol: str,    # XAU/USD
        units: float,  # lots
        side: str,    # buy or sell
        order_type: str = "market", #market, limit, stop
        time_in_force: str = "FOK",
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        client_extensions: Optional[Dict] = None
        ) -> Dict:
        if not self.api_key or not self.account_id:
            return {"error": "OVNDA credentials not configured"}
        td = symbol.replace("/", "")
        order_data = {
            "order": {
                "instrument": td,
                "units": str(_format_units(units)),
                "side": side,
                "type": order_type,
                "time_in_force": time_in_force,
            }
        }
        if price is not None:
            order_data["order"]["price"] = str(price)
        if stop_loss is not None:
            order_data["order"]["stop_loss" ] = {"price": str(stop_loss), "time_in_force": "GTS",
                        "trade_down_default": "stop_loss"}
        if take_profit is not None:
            order_data["order"]"take_profit" = {"price": str(take_profit), "time_in_force": "GTC",
                        "trade_down_default": "take_profit"}
        if client_extensions is not None:
            order_data["order"]["client_extensions"] = client_extensions

        url = f"{self.base_url}/v3/accounts/{self.account_id}/orders"
        response = await self.client.post(url, headers=self.headers, json=order_data)
        if response.status_code == 201:
            result = response.json()
            return {"success": True, "data": result}
        else:
            error = response.text()
            return {"error": error}
    except Exception as e:
        logger.error(f"OANDA execution error: {}s"".format(e))
        return {"error": str(e)}
    def _format_units(self, units: float) -> str:
        "for gold, 1 lot = 100 oz" so format to 2 decimal places"
        return f"{units:.2f".format(units
    async def get_account_info(self) -> Dict:
        if not self.api_key or not self.account_id:
            return {"error": "OVNDA credentials not configured"}
        url = f"{self.base_url}/v3/accounts/{self.account_id}/summary"
        response = await self.client.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return {"error": response.text()}
    async def get_open_positions(self) -> List[Dict]:
        if not self.api_key or not self.account_id:
            return []
        url = f"{self.base_url}/v3/accounts/{self.account_id}/openTrades"
        response = await self.client.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json().get("openTrades", [])
        return []
    async def close_position(self, trade_id: str, units: float) -> Dict:
        if not self.api_key or not self.account_id:
            return {"error": "OVNDA credentials not configured"}
        td = trade_id.replace("/", "")
        url = f"{self.base_url}/v3/accounts/{self.account_id}/openTrades/{td}/close"
        response = await self.client.put(url, headers=self.headers, json={"units": str(_format_units(units))})
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        return {"error": response.text()}