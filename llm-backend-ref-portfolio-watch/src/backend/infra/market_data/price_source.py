"""PriceSource thật — vnstock Quote.history (OHLCV theo ngày) kèm smart cache & validation."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
import re
import threading
import time

from backend.domain.ports import PriceBar, PriceQuote

logger = logging.getLogger(__name__)

# Mã chứng khoán VN: 3 chữ cái (cổ phiếu thông thường) hoặc 3-10 ký tự chữ/số (chứng quyền, quỹ ETF như E1VFVN30)
_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{3,10}$")

# Baseline prices in thousands of VND used for realistic synthetic fallbacks if API is offline
DEFAULT_BASE_PRICES: dict[str, float] = {
    "FPT": 66.0,  # Đồng bộ thị giá thực tế (~65.x - 66.x), loại bỏ mốc 135.0 cũ
    "VNM": 61.0,
    "HPG": 21.0,
    "VHM": 66.0,
    "VIC": 45.0,
    "TCB": 33.0,
    "MBB": 20.0,
    "SSI": 21.0,
    "MWG": 73.0,
    "VCB": 58.0,
}

# Module-level shared cache ensuring Single Source of Truth between Swarm PriceAgent and MarketService
_SHARED_QUOTE_CACHE: dict[str, tuple[float, PriceQuote]] = {}
_SHARED_HISTORY_CACHE: dict[tuple[str, int], tuple[float, list[PriceBar]]] = {}
_SHARED_CACHE_STATS: dict[str, int] = {"hits": 0, "misses": 0}
_SHARED_CACHE_LOCK = threading.Lock()


class VnstockPriceSource:
    """Lấy giá đóng cửa mới nhất + phiên trước qua vnstock kèm cơ chế cache thông minh và validation."""

    def __init__(
        self,
        source: str = "VCI",
        lookback_days: int = 14,
        quote_factory=None,
        cache_ttl_seconds: float = 300.0,
        fallback_on_error: bool = False,
        use_shared_cache: bool | None = None,
    ):
        self.source = source
        self.lookback_days = lookback_days
        self._quote_factory = quote_factory
        self.cache_ttl_seconds = cache_ttl_seconds
        self.fallback_on_error = fallback_on_error

        # In-memory TTL caches — mặc định dùng chung trừ khi truyền quote_factory riêng (mock test)
        if use_shared_cache is None:
            use_shared_cache = (quote_factory is None)

        if use_shared_cache:
            self._quote_cache = _SHARED_QUOTE_CACHE
            self._history_cache = _SHARED_HISTORY_CACHE
            self._cache_stats = _SHARED_CACHE_STATS
            self._lock = _SHARED_CACHE_LOCK
        else:
            self._quote_cache = {}
            self._history_cache = {}
            self._cache_stats = {"hits": 0, "misses": 0}
            self._lock = threading.Lock()

    @staticmethod
    def validate_symbol(symbol: str | None) -> tuple[str, str | None]:
        """Kiểm tra tính hợp lệ của mã cổ phiếu.

        Trả về: (symbol_chuan_hoa, error_message_or_None)
        """
        sym = (symbol or "").strip().upper()
        if not sym:
            return "", "Mã cổ phiếu không được để trống"
        if not _SYMBOL_PATTERN.fullmatch(sym):
            return sym, f"Mã cổ phiếu '{sym}' không đúng định dạng (phải gồm 3 chữ cái hoặc ký hiệu hợp lệ, ví dụ: FPT, VNM, HPG)"
        return sym, None

    def clear_cache(self) -> None:
        """Xóa toàn bộ bộ nhớ đệm cache."""
        with self._lock:
            self._quote_cache.clear()
            self._history_cache.clear()
            self._cache_stats = {"hits": 0, "misses": 0}

    def cache_stats(self) -> dict[str, int]:
        """Thống kê số lượt hits và misses của cache."""
        with self._lock:
            return dict(self._cache_stats)

    def fetch_latest_close(self, symbol: str) -> PriceQuote:
        sym, val_err = self.validate_symbol(symbol)
        if val_err:
            return PriceQuote(symbol=sym, latest_close=None, error=val_err)

        now = time.time()
        with self._lock:
            if sym in self._quote_cache:
                ts, cached_quote = self._quote_cache[sym]
                if (now - ts) < self.cache_ttl_seconds:
                    self._cache_stats["hits"] += 1
                    return cached_quote
            self._cache_stats["misses"] += 1

        try:
            Quote = self._quote_factory
            if Quote is None:
                from vnstock import Quote
            quote = Quote(symbol=sym, source=self.source)
            end = datetime.now().date()
            start = end - timedelta(days=max(self.lookback_days, 5))
            df = quote.history(
                start=start.isoformat(),
                end=end.isoformat(),
                interval="1D",
            )
        except (Exception, SystemExit) as exc:
            if self.fallback_on_error and sym in DEFAULT_BASE_PRICES:
                base = DEFAULT_BASE_PRICES[sym]
                prev = round(base * 0.99, 2)
                fallback_quote = PriceQuote(symbol=sym, latest_close=base, prev_close=prev, error=None)
                with self._lock:
                    self._quote_cache[sym] = (now, fallback_quote)
                return fallback_quote
            exc_str = str(exc).lower()
            if any(k in exc_str for k in ("429", "too many requests", "rate limit", "ratelimit")):
                err_msg = f"Nguồn dữ liệu tạm thời chạm giới hạn truy vấn (rate limit) khi lấy mã '{sym}'. Vui lòng thử lại sau ít phút."
            elif any(k in exc_str for k in ("timeout", "timed out", "connection", "connect")):
                err_msg = f"Không thể kết nối đến nguồn dữ liệu giá cho mã '{sym}'. Vui lòng kiểm tra kết nối mạng."
            else:
                err_msg = f"Không tìm thấy dữ liệu giá cho mã '{sym}' hoặc mã không tồn tại trên thị trường."
            return PriceQuote(
                symbol=sym,
                latest_close=None,
                error=err_msg,
            )

        if df is None or getattr(df, "empty", True):
            if self.fallback_on_error and sym in DEFAULT_BASE_PRICES:
                base = DEFAULT_BASE_PRICES[sym]
                prev = round(base * 0.99, 2)
                fallback_quote = PriceQuote(symbol=sym, latest_close=base, prev_close=prev, error=None)
                with self._lock:
                    self._quote_cache[sym] = (now, fallback_quote)
                return fallback_quote
            return PriceQuote(
                symbol=sym,
                latest_close=None,
                error=f"Không tìm thấy dữ liệu giá cho mã '{sym}'. Vui lòng kiểm tra lại mã cổ phiếu.",
            )

        try:
            work = df.copy()
            work.columns = [str(c).strip().lower() for c in work.columns]
            if "close" not in work.columns:
                return PriceQuote(
                    symbol=sym,
                    latest_close=None,
                    error=f"Dữ liệu nguồn của mã '{sym}' thiếu thông tin giá đóng cửa.",
                )
            if "time" in work.columns:
                work = work.sort_values("time")
            closes = work["close"].dropna().tolist()
        except Exception as exc:  # noqa: BLE001
            return PriceQuote(
                symbol=sym,
                latest_close=None,
                error=f"Lỗi khi xử lý dữ liệu giá cho mã '{sym}': {exc}",
            )

        if not closes:
            return PriceQuote(
                symbol=sym,
                latest_close=None,
                error=f"Không có phiên giao dịch nào có giá đóng cửa cho mã '{sym}'.",
            )

        latest = float(closes[-1])
        prev = float(closes[-2]) if len(closes) >= 2 else None
        res = PriceQuote(
            symbol=sym,
            latest_close=latest,
            prev_close=prev,
            error=None,
        )

        with self._lock:
            self._quote_cache[sym] = (now, res)

        return res

    def fetch_history(self, symbol: str, days: int = 30) -> list[PriceBar]:
        """Lấy chuỗi lịch sử giá OHLCV qua vnstock cho ChartAgent và EvalAgent kèm cache."""
        sym, val_err = self.validate_symbol(symbol)
        if val_err:
            return []

        now = time.time()
        key = (sym, days)
        with self._lock:
            if key in self._history_cache:
                ts, cached_bars = self._history_cache[key]
                if (now - ts) < self.cache_ttl_seconds:
                    self._cache_stats["hits"] += 1
                    return list(cached_bars)
            self._cache_stats["misses"] += 1

        try:
            Quote = self._quote_factory
            if Quote is None:
                from vnstock import Quote
            quote = Quote(symbol=sym, source=self.source)
            end = datetime.now().date()
            start = end - timedelta(days=max(days, 5))
            df = quote.history(
                start=start.isoformat(),
                end=end.isoformat(),
                interval="1D",
            )
        except (Exception, SystemExit):
            return []

        if df is None or getattr(df, "empty", True):
            return []

        try:
            work = df.copy()
            work.columns = [str(c).strip().lower() for c in work.columns]
            if "close" not in work.columns:
                return []
            if "time" in work.columns:
                work = work.sort_values("time")
            bars: list[PriceBar] = []
            for _, row in work.iterrows():
                d_val = row.get("time") or row.get("date") or ""
                d_str = str(d_val).split("T")[0].split(" ")[0]
                if not d_str:
                    continue
                c_val = float(row["close"])
                o_val = float(row["open"]) if "open" in row and row["open"] is not None else c_val
                h_val = float(row["high"]) if "high" in row and row["high"] is not None else c_val
                l_val = float(row["low"]) if "low" in row and row["low"] is not None else c_val
                v_val = float(row["volume"]) if "volume" in row and row["volume"] is not None else 0.0
                bars.append(PriceBar(date=d_str, close=c_val, open_price=o_val, high=h_val, low=l_val, volume=v_val))

            if bars:
                with self._lock:
                    self._history_cache[key] = (now, bars)

            return bars
        except Exception:
            return []

