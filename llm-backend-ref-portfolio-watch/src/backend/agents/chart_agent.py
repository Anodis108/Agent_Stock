"""ChartAgent — Tự động phân tích chuỗi dữ liệu giá và vẽ biểu đồ tài chính Matplotlib/Seaborn.

Chức năng:
1. Tiếp nhận chuỗi dữ liệu giá từ PriceAgent (OHLCV lịch sử 10-30 phiên).
2. Vẽ biểu đồ nến / đường giá lịch sử kèm đường trung bình (SMA 5, SMA 10).
3. Vẽ biểu đồ so sánh % tăng trưởng giữa 2-3 mã cổ phiếu.
4. Lưu ảnh PNG tĩnh tại resources/data/charts/ và trả về URL + Base64.
"""

from __future__ import annotations

import base64
import io
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence
from uuid import uuid4

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from backend.domain.ports import PriceBar


def get_charts_dir() -> Path:
    """Xác định đường dẫn thư mục lưu ảnh biểu đồ."""
    env_dir = os.environ.get("CHARTS_DIR")
    if env_dir:
        p = Path(env_dir)
    else:
        root = Path(__file__).resolve().parents[3]
        p = root / "resources" / "data" / "charts"
    p.mkdir(parents=True, exist_ok=True)
    return p


@dataclass(slots=True)
class ChartResult:
    """Kết quả sinh biểu đồ từ ChartAgent."""

    success: bool
    chart_type: str = "price_history"  # "price_history" | "comparison" | "candlestick"
    file_path: str | None = None
    file_name: str | None = None
    url: str | None = None
    base64_data: str | None = None
    error: str | None = None
    symbols: list[str] | None = None


def _normalize_bar(b: PriceBar | dict[str, Any]) -> dict[str, Any]:
    """Chuẩn hóa PriceBar hoặc dict thành dict đồng nhất."""
    if isinstance(b, dict):
        return {
            "date": str(b.get("date") or b.get("trade_date") or ""),
            "close": float(b.get("close", 0)),
            "open": float(b.get("open_price") or b.get("open") or b.get("close", 0)),
            "high": float(b.get("high") or b.get("close", 0)),
            "low": float(b.get("low") or b.get("close", 0)),
            "volume": float(b.get("volume") or 0),
        }
    return {
        "date": str(b.date),
        "close": float(b.close),
        "open": float(b.open_price if b.open_price is not None else b.close),
        "high": float(b.high if b.high is not None else b.close),
        "low": float(b.low if b.low is not None else b.close),
        "volume": float(b.volume or 0),
    }


def _parse_date(d_str: str) -> datetime:
    """Chuyển chuỗi ngày sang datetime."""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(d_str.strip(), fmt)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(d_str.strip())
    except Exception:
        return datetime.now()


def _save_and_encode_fig(fig: plt.Figure, chart_id: str, output_dir: Path | None = None) -> tuple[str, str, str, str]:
    """Lưu figure ra đĩa PNG và trả về (file_path, file_name, url, base64_uri)."""
    charts_dir = output_dir or get_charts_dir()
    file_name = f"chart_{chart_id}.png"
    file_path = str(charts_dir / file_name)

    # 1. Lưu ra file PNG tĩnh
    fig.savefig(file_path, dpi=120, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")

    # 2. Sinh chuỗi Base64
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    buf.seek(0)
    b64_str = base64.b64encode(buf.read()).decode("utf-8")
    base64_uri = f"data:image/png;base64,{b64_str}"

    url = f"/charts/{file_name}"
    return file_path, file_name, url, base64_uri


def plot_price_history(
    symbol: str,
    bars: Sequence[PriceBar | dict[str, Any]],
    *,
    output_dir: str | Path | None = None,
    sma_periods: list[int] = (5, 10),
    style: str = "line",
    title: str | None = None,
) -> ChartResult:
    """Vẽ biểu đồ lịch sử giá cho 1 mã cổ phiếu (Line hoặc Candlestick + SMA + Volume)."""
    sym = (symbol or "").strip().upper()
    if not sym:
        return ChartResult(success=False, error="Symbol không được để trống")
    if not bars:
        return ChartResult(success=False, error=f"Không có dữ liệu giá lịch sử cho mã {sym}", symbols=[sym])

    # Sắp xếp theo ngày tăng dần
    normalized = [_normalize_bar(b) for b in bars]
    normalized.sort(key=lambda x: x["date"])

    if len(normalized) < 2:
        return ChartResult(success=False, error=f"Dữ liệu lịch sử của {sym} quá ít (< 2 phiên) để vẽ biểu đồ", symbols=[sym])

    dates = [_parse_date(b["date"]) for b in normalized]
    closes = [b["close"] for b in normalized]
    volumes = [b["volume"] for b in normalized]
    has_volume = any(v > 0 for v in volumes)

    # Khởi tạo Figure và Subplots
    out_path = Path(output_dir) if output_dir else None
    chart_id = f"{sym}_{uuid4().hex[:8]}"

    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, (ax1, ax2) = plt.subplots(
        2, 1,
        figsize=(10, 6.2),
        gridspec_kw={"height_ratios": [3.5, 1] if has_volume else [1, 0.001]},
        facecolor="#ffffff",
    )
    if not has_volume:
        ax2.set_visible(False)

    try:
        # 1. Vẽ đường giá Close chính
        ax1.plot(dates, closes, label=f"{sym} Đóng cửa", color="#0b6e4f", linewidth=2.2, zorder=3)
        ax1.scatter(dates[-1], closes[-1], color="#0b6e4f", s=40, zorder=4)

        # 2. Vẽ Candlestick nếu style="candle"
        if style == "candle":
            for i, b in enumerate(normalized):
                d = dates[i]
                op, cl, hi, lo = b["open"], b["close"], b["high"], b["low"]
                is_up = cl >= op
                color = "#10b981" if is_up else "#ef4444"
                # Râu nến
                ax1.vlines(d, lo, hi, color=color, linewidth=1.2, zorder=2)
                # Thân nến
                body_low = min(op, cl)
                body_height = max(abs(cl - op), (max(closes) - min(closes)) * 0.005)
                ax1.bar(d, body_height, bottom=body_low, width=0.6, color=color, alpha=0.9, zorder=3)

        # 3. Tính và vẽ các đường Simple Moving Average (SMA)
        colors_sma = ["#f59e0b", "#8b5cf6", "#ec4899"]
        for idx, period in enumerate(sma_periods):
            if len(closes) >= period:
                sma_vals = []
                for i in range(len(closes)):
                    if i < period - 1:
                        sma_vals.append(None)
                    else:
                        window = closes[i - period + 1 : i + 1]
                        sma_vals.append(sum(window) / period)
                valid_dates = [dates[i] for i, v in enumerate(sma_vals) if v is not None]
                valid_sma = [v for v in sma_vals if v is not None]
                c = colors_sma[idx % len(colors_sma)]
                ax1.plot(valid_dates, valid_sma, label=f"SMA {period}", color=c, linestyle="--", linewidth=1.4, alpha=0.85)

        # 4. Vẽ Volume Bar Chart ở subplot dưới
        if has_volume:
            vol_colors = [
                "#10b981" if normalized[i]["close"] >= normalized[i]["open"] else "#ef4444"
                for i in range(len(normalized))
            ]
            ax2.bar(dates, volumes, color=vol_colors, width=0.6, alpha=0.6)
            ax2.set_ylabel("Khối lượng", fontsize=9, color="#64748b")
            ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x/1e6:.1f}M" if x >= 1e6 else f"{x/1e3:.0f}K"))
            ax2.grid(True, linestyle=":", alpha=0.5)

        # Định dạng Trục & Nhãn
        chart_title = title or f"Biểu đồ diễn biến giá cổ phiếu {sym}"
        latest_str = f"{closes[-1]:,.0f} VND" if closes[-1] > 1000 else f"{closes[-1]:,.2f}"
        pct_change = ((closes[-1] - closes[0]) / closes[0]) * 100
        change_sign = "+" if pct_change >= 0 else ""
        subtitle = f"Giá hiện tại: {latest_str} ({change_sign}{pct_change:.2f}% trong {len(closes)} phiên)"

        ax1.set_title(f"{chart_title}\n{subtitle}", fontsize=12, fontweight="bold", color="#1e293b", pad=12)
        ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:,.0f}"))
        ax1.set_ylabel("Giá (VND)", fontsize=10, fontweight="600", color="#475569")
        ax1.legend(loc="upper left", frameon=True, facecolor="#ffffff", framealpha=0.9, fontsize=9)
        ax1.grid(True, linestyle="--", alpha=0.6)

        # Trục thời gian
        target_ax = ax2 if has_volume else ax1
        target_ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
        target_ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=10))
        plt.setp(target_ax.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=9)

        plt.tight_layout()
        file_path, file_name, url, base64_uri = _save_and_encode_fig(fig, chart_id, out_path)

        return ChartResult(
            success=True,
            chart_type="candlestick" if style == "candle" else "price_history",
            file_path=file_path,
            file_name=file_name,
            url=url,
            base64_data=base64_uri,
            symbols=[sym],
        )
    except Exception as exc:
        return ChartResult(success=False, error=f"Lỗi render biểu đồ {sym}: {exc}", symbols=[sym])
    finally:
        plt.close(fig)


def plot_comparison(
    symbols_history: dict[str, Sequence[PriceBar | dict[str, Any]]],
    *,
    output_dir: str | Path | None = None,
    title: str | None = None,
) -> ChartResult:
    """Vẽ biểu đồ so sánh % tăng trưởng giữa 2-3 mã cổ phiếu."""
    valid_symbols = [s.strip().upper() for s, data in symbols_history.items() if data and len(data) >= 2]
    if len(valid_symbols) < 2:
        return ChartResult(
            success=False,
            chart_type="comparison",
            error="Cần ít nhất 2 mã cổ phiếu có tối thiểu 2 phiên dữ liệu để vẽ biểu đồ so sánh",
            symbols=list(symbols_history.keys()),
        )

    out_path = Path(output_dir) if output_dir else None
    chart_id = f"cmp_{'_'.join(valid_symbols[:3])}_{uuid4().hex[:8]}"

    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, ax = plt.subplots(figsize=(10, 5.5), facecolor="#ffffff")

    palette = ["#0b6e4f", "#2563eb", "#ea580c", "#8b5cf6", "#06b6d4"]

    try:
        min_date = None
        max_date = None

        for idx, sym in enumerate(valid_symbols):
            raw_bars = symbols_history[sym]
            norm_bars = [_normalize_bar(b) for b in raw_bars]
            norm_bars.sort(key=lambda x: x["date"])

            base_price = norm_bars[0]["close"]
            if base_price <= 0:
                continue

            dates = [_parse_date(b["date"]) for b in norm_bars]
            returns_pct = [((b["close"] - base_price) / base_price) * 100 for b in norm_bars]

            if min_date is None or dates[0] < min_date:
                min_date = dates[0]
            if max_date is None or dates[-1] > max_date:
                max_date = dates[-1]

            color = palette[idx % len(palette)]
            final_ret = returns_pct[-1]
            sign = "+" if final_ret >= 0 else ""
            label = f"{sym} ({sign}{final_ret:.1f}%)"

            ax.plot(dates, returns_pct, label=label, color=color, linewidth=2.2)
            ax.scatter(dates[-1], final_ret, color=color, s=36)

        # Baseline 0%
        ax.axhline(0, color="#94a3b8", linestyle="--", linewidth=1.2, alpha=0.8)

        cmp_title = title or f"So sánh hiệu suất tương đối: {' vs '.join(valid_symbols)}"
        ax.set_title(f"{cmp_title}\n(Tỷ suất lợi nhuận chuẩn hóa % từ mốc ban đầu)", fontsize=12, fontweight="bold", color="#1e293b", pad=12)
        ax.set_ylabel("% Tăng trưởng", fontsize=10, fontweight="600", color="#475569")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:+.1f}%"))
        ax.legend(loc="upper left", frameon=True, facecolor="#ffffff", framealpha=0.9, fontsize=9)
        ax.grid(True, linestyle="--", alpha=0.6)

        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=10))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=9)

        plt.tight_layout()
        file_path, file_name, url, base64_uri = _save_and_encode_fig(fig, chart_id, out_path)

        return ChartResult(
            success=True,
            chart_type="comparison",
            file_path=file_path,
            file_name=file_name,
            url=url,
            base64_data=base64_uri,
            symbols=valid_symbols,
        )
    except Exception as exc:
        return ChartResult(success=False, chart_type="comparison", error=f"Lỗi so sánh biểu đồ: {exc}", symbols=valid_symbols)
    finally:
        plt.close(fig)


def run_chart_agent(
    symbols: str | list[str],
    price_data: Sequence[PriceBar | dict[str, Any]] | dict[str, Sequence[PriceBar | dict[str, Any]]],
    *,
    chart_type: str = "auto",
    style: str = "line",
    output_dir: str | Path | None = None,
    title: str | None = None,
) -> ChartResult:
    """Entry point chính cho ChartAgent tương thích LangGraph swarm.

    - Nếu `symbols` là 1 chuỗi mã hoặc price_data là danh sách -> Gọi `plot_price_history`.
    - Nếu `symbols` là nhiều mã (hoặc price_data là dict) -> Gọi `plot_comparison`.
    """
    if isinstance(symbols, str) and "," in symbols:
        symbols_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    elif isinstance(symbols, list):
        symbols_list = [s.strip().upper() for s in symbols if s.strip()]
    else:
        symbols_list = [str(symbols).strip().upper()]

    if len(symbols_list) > 1 and isinstance(price_data, dict):
        return plot_comparison(price_data, output_dir=output_dir, title=title)
    if isinstance(price_data, dict) and len(price_data) > 1:
        return plot_comparison(price_data, output_dir=output_dir, title=title)

    # Đơn mã
    target_sym = symbols_list[0] if symbols_list else "UNKNOWN"
    if isinstance(price_data, dict):
        bars = price_data.get(target_sym) or next(iter(price_data.values()), [])
    else:
        bars = price_data

    return plot_price_history(target_sym, bars, output_dir=output_dir, style=style, title=title)
