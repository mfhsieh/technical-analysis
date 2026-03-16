"""
Technical Analysis (TA) 圖表繪製模組：負責利用 Bokeh 繪製 K 線圖及各式技術指標圖表。
"""

# pylint: disable=too-many-lines
import re
from flask import current_app
import numpy as np
import pandas as pd
from bokeh.plotting import figure as BokehFigure
from bokeh.models import LinearAxis, ColumnDataSource, Range, Range1d, Legend, CustomJS, DataRenderer, GlyphRenderer, LegendItem, GridPlot, RangeSlider
from bokeh.models.tools import HoverTool, CrosshairTool, WheelZoomTool, PanTool
from bokeh.models.formatters import TickFormatter, NumeralTickFormatter
from bokeh.layouts import gridplot
from bokeh.palettes import Category10


##
# 常數定義
##


# 通用常數

EPSILON = 0.0001  # 避免因小數誤差產生 X 軸調整的無限循環

# PLOT_WIDTH = 800  # 圖表寬度  # 改成 sizing_mode="stretch_width"，不再需要
PLOT_HEIGHT = 288  # K 線圖高度
PLOT_HEIGHT_MIN = 96  # 其它圖表高度

XRANGE_DEFAULT = 60  # X 軸預設顯示資料量
XRANGE_MIN = 30  # X 軸最小顯示資料量
XRANGE_MAX = 240  # X 軸最大顯示資料量

XAXIS_FONT_SIZE = "8pt"  # X 軸標籤字體大小
XAXIS_FONT_STYLE = "normal"  # X 軸標籤字體樣式

YRANGE_PADDING = 0.05  # Y 軸範圍兩端添加額外空間的比例

YAXIS_MIN_TICKS = 3  # Y 軸最小刻度數
YAXIS_FONT_SIZE = XAXIS_FONT_SIZE  # Y 軸標籤字體大小，與 X 軸相同
YAXIS_FONT_STYLE = XAXIS_FONT_STYLE  # Y 軸標籤字體樣式，與 X 軸相同
YAXIS_TITLE_FONT_SIZE = "10pt"  # Y 軸標題字體大小
YAXIS_TITLE_FONT_STYLE = "bold"  # Y 軸標題字體樣式

COLOR_INC = "#F23645"  # 上漲顏色
COLOR_DEC = "#089981"  # 下跌顏色
COLOR_DARK = "#404040"  # 深色
COLOR_SET = Category10  # Bokeh 預設的 Category10 調色盤，用在 MA、CDP、DMI

LINE_WIDTH = 1  # 線條寬度
LINE_ALPHA = 1  # 線條不透明度
LINE_WIDTH_MUTED = 1  # 線條靜音時的寬度
LINE_ALPHA_MUTED = 0.1  # 線條靜音時的不透明度
AREA_ALPHA_MUTED = 0.1  # 填充區域靜音時的不透明度

VBAR_WIDTH = 0.60  # 垂直柱狀圖寬度

LEGEND_FONT_SIZE = YAXIS_TITLE_FONT_SIZE  # 圖例字體大小，與 Y 軸標題相同
LEGEND_FONT_STYLE = YAXIS_TITLE_FONT_STYLE  # 圖例字體樣式，與 Y 軸標題相同
LEGEND_POSITION = (-4, -8)  # 圖例位置 (x, y) 相對於繪圖區域的角落
LEGEND_ORIENTATION = "horizontal"  # 圖例排列方向
LEGEND_BACKGROUND_ALPHA = 0  # 圖例背景不透明度
LEGEND_BORDER_ALPHA = 0  # 圖例邊線不透明度

HOVER_MODE = "vline"  # HoverTool: mode
HOVER_ATTACHMENT = "horizontal"  # HoverTool: attachment

CROSSHAIR_WIDTH = 1  # CrosshairTool: line_width
CROSSHAIR_ALPHA = 0.5  # CrosshairTool: line_alpha

# Candlestick
CANDLESTICK_YAXIS_LABEL = "K Chart"  # K 線圖 Y 軸標籤
# CANDLESTICK_TITLE_FONT_SIZE = "12pt"  # K 線圖標題字體大小  # title 移到 html 頁面，不再需要
CANDLESTICK_YAXIS_FORMAT = "#,##0"  # K 線圖 Y 軸數值格式
CANDLESTICK_TOOLTIPS = [  # K 線圖 HoverTool 提示資訊
    ["開盤", "open", "#,##0.00"],
    ["最高", "high", "#,##0.00"],
    ["最低", "low", "#,##0.00"],
    ["收盤", "close", "#,##0.00"],
    ["成交", "volume", "0.00a"],
    ["漲跌", "Change", "+#,##0.00"],
    ["MA5", "MA5", "#,##0.00"],
    ["MA20", "MA20", "#,##0.00"],
    ["MA60", "MA60", "#,##0.00"],
]

# Volume
VOLUME_YAXIS_LABEL = "Volume"  # Volume 圖 Y 軸標籤
VOLUME_YAXIS_FORMAT = "0a"  # Volume 圖 Y 軸數值格式
VOLUME_TOOLTIPS = [  # Volume 圖 HoverTool 提示資訊
    ["成交", "volume", "0.00a"],
]

# KDJ
KDJ_YAXIS_LABEL = "KD, J"  # KDJ 圖 Y 軸標籤
KDJ_COLOR = [COLOR_INC, COLOR_DEC, COLOR_DARK]  # K, D, J 線的顏色
KDJ_TOOLTIPS = [  # KDJ 圖 HoverTool 提示資訊
    ["K", "K", "0.00"],
    ["D", "D", "0.00"],
    ["J", "J", "0.00"],
]

# MACD
MACD_YAXIS_LABEL = "MACD"  # MACD 圖 Y 軸標籤
MACD_COLOR = [COLOR_INC, COLOR_DEC]  # DIF, MACD 線的顏色
MACD_TOOLTIPS = [  # MACD 圖 HoverTool 提示資訊
    ["DIF", "DIF", "0.00"],
    ["MACD", "MACD", "0.00"],
    ["OSC", "OSC", "+0.00"],
]

# RSI
RSI_YAXIS_LABEL = "RSI"  # RSI 圖 Y 軸標籤
RSI_COLOR = [COLOR_INC, COLOR_DEC]  # RSI5, RSI10 線的顏色
RSI_TOOLTIPS = [  # RSI 圖 HoverTool 提示資訊
    ["RSI5", "RSI5", "0.00"],
    ["RSI10", "RSI10", "0.00"],
]

# BIAS
BIAS_YAXIS_LABEL = "BIAS"  # BIAS 圖 Y 軸標籤
BIAS_COLOR = [COLOR_INC, COLOR_DEC]  # BIAS10, BIAS20 線的顏色
BIAS_TOOLTIPS = [  # BIAS 圖 HoverTool 提示資訊
    ["BIAS10", "BIAS10", "0.00"],
    ["BIAS20", "BIAS20", "0.00"],
    ["B10-B20", "B10-B20", "+0.00"],
]

# Williams %R
WILLR_YAXIS_LABEL = "Williams"  # Williams %R 圖 Y 軸標籤
WILLR_COLOR = [COLOR_DARK]  # Williams %R 線的顏色
WILLR_TOOLTIPS = [  # Williams %R 圖 HoverTool 提示資訊
    ["WILLR", "WILLR", "0.00"],
]

# BBI
BBI_YAXIS_LABEL = "BBI"  # BBI 圖 Y 軸標籤
BBI_YAXIS_FORMAT = "#,##0"  # BBI 圖 Y 軸數值格式
BBI_TOOLTIPS = [  # BBI 圖 HoverTool 提示資訊
    ["M3", "M3", "#,##0.00"],
    ["BS", "BS", "#,##0.00"],
    ["M3-BS", "M3-BS", "+#,##0.00"],
]

# CDP
CDP_YAXIS_LABEL = "CDP"  # CDP 圖 Y 軸標籤
CDP_YAXIS_FORMAT = "#,##0"  # CDP 圖 Y 軸數值格式
CDP_TOOLTIPS = [  # CDP 圖 HoverTool 提示資訊
    ["AH", "AH", "#,##0.00"],
    ["NH", "NH", "#,##0.00"],
    ["CDP", "CDP", "#,##0.00"],
    ["NL", "NL", "#,##0.00"],
    ["AL", "AL", "#,##0.00"],
]

# DMI
DMI_YAXIS_LABEL = "DMI"  # DMI 圖 Y 軸標籤
DMI_LEGEND_DICT = {"PLUS_DI": "+DI", "MINUS_DI": "-DI"}  # DMI 圖例名稱對應
DMI_TOOLTIPS = [  # DMI 圖 HoverTool 提示資訊
    ["+DI", "PLUS_DI", "0.00"],
    ["-DI", "MINUS_DI", "0.00"],
    ["ADX", "ADX", "0.00"],
    ["ADXR", "ADXR", "0.00"],
]

# BBands
BBANDS_YAXIS_LABEL = "BBands"  # BBands 圖 Y 軸標籤
BBANDS_AREA_LABEL = "Band"  # BBands 圖 Y 軸標籤
# BBANDS_LEGEND_DICT = {"BBL": "下軌", "BBM": "中軌", "BBU": "上軌"}  # BBands 圖例名稱對應
BBANDS_YAXIS_FORMAT = "#,##0"  # BBands 圖 Y 軸數值格式
BBANDS_AREA_COLOR = COLOR_SET[3][1]  # 填充上下軌之間的區域，使用中軌的顏色
BBANDS_AREA_FILL_ALPHA = 0.2  # 填充上下軌之間區域的透明度
BBANDS_TOOLTIPS = [
    ["上軌", "BBU", "#,##0.00"],
    ["中軌", "BBM", "#,##0.00"],
    ["下軌", "BBL", "#,##0.00"],
]

# OBV
OBV_YAXIS_LABEL = "OBV"  # OBV 圖 Y 軸標籤
OBV_YAXIS_FORMAT = "0a"  # OBV 圖 Y 軸數值格式
OBV_COLOR = [COLOR_DARK]  # OBV 線的顏色
OBV_TOOLTIPS = [  # OBV 圖 HoverTool 提示資訊
    ["OBV", "OBV", "0.00a"],
]

# CCI
CCI_YAXIS_LABEL = "CCI"  # CCI 圖 Y 軸標籤
CCI_COLOR = [COLOR_DARK]  # CCI 線的顏色
CCI_TOOLTIPS = [  # CCI 圖 HoverTool 提示資訊
    ["CCI", "CCI", "0.00"],
]


##
# 通用函式
##


def _init_xrange(
    src: ColumnDataSource,
    ticks: int = XRANGE_DEFAULT,
) -> tuple[float, float]:
    """初始化 X 軸的顯示範圍。

    以 10 筆資料顯示第 5 至 9 筆為例，其足標為 4 到 8；為容納顯示長條圖的空間，x 軸的範圍從 3.5 到 8.5。

    Args:
        src (ColumnDataSource): Bokeh 的資料來源。
        ticks (int, optional): 初始預設顯示的資料點數量。預設為 XRANGE_DEFAULT。

    Returns:
        tuple[float, float]: X 軸的起始和結束值。
    """
    length = len(src.data["index"])
    ticks = max(XRANGE_MIN, min(XRANGE_MAX, ticks, length))
    x_end = length - 0.5
    x_start = max(x_end - ticks, -0.5)
    return x_start, x_end


def _init_yrange(
    src: ColumnDataSource,
    x_start: float,
    x_end: float,
    keys_low: list[str] | None = None,
    keys_high: list[str] | None = None,
    padding: float = YRANGE_PADDING,
) -> tuple[float, float]:
    """初始化 Y 軸的顯示範圍。

    Y 軸顯示範圍的計算邏輯與 _gen_js_range 產生的 javascript 相同。

    Args:
        src (ColumnDataSource): Bokeh 的資料來源。
        x_start (float): X 軸的起始值。
        x_end (float): X 軸的結束值。
        keys_low (list[str], optional): 用於計算 Y 軸下限的資料欄位列表。預設為 None。
        keys_high (list[str], optional): 用於計算 Y 軸上限的資料欄位列表。預設為 None。
        padding (float, optional): 在 Y 軸範圍兩端添加額外空間的比例 (預設為 YRANGE_PADDING)。

    Returns:
        tuple[float, float]: Y 軸的起始和結束值。
    """
    delta = 0.001  # 避免因 round 產生預期外的結果，例如：x_end 為 4.5 時，x_end_idx 應為 4。
    x_start_idx = max(0, round(x_start + delta))
    x_end_idx = min(len(src.data["index"]) - 1, round(x_end - delta))

    y_bottoms = []
    y_tops = []
    keys_all = set(keys_low if keys_low else []) | set(keys_high if keys_high else [])  # 取不重複項目進行迴圈
    for key in keys_all:
        if key in src.data:  # type: ignore
            sliced = np.array([x for x in src.data[key][x_start_idx : x_end_idx + 1] if x is not None])  # type: ignore
            sliced = sliced[np.isfinite(sliced)] if sliced.size > 0 else np.array([])
            if sliced.size > 0:
                y_bottoms.append(np.min(sliced))
                y_tops.append(np.max(sliced))

    y_bottom = (min(y_bottoms) if y_bottoms else -1) if keys_low else 0  # 沒有下限，則下限為 0；全是空值，則下限 -1
    y_top = (max(y_tops) if y_tops else 1) if keys_high else 0  # 沒有上限，則上限為 0；全是空值，則上限 +1

    y_bottom = y_bottom - (y_top - y_bottom) * (padding if keys_low else 0)
    y_top = y_top + (y_top - y_bottom) * (padding if keys_high else 0)

    if abs(y_bottom - y_top) < 1e-9:  # 考量上下限一樣的極端狀況 (可能不會發生)，人為加大範圍
        if keys_low:
            y_bottom -= 1
        if keys_high:
            y_top += 1

    return y_bottom, y_top


def _js_on_range_change(
    fig: BokehFigure,
    src: ColumnDataSource,
    js_code: str,
    slider: RangeSlider | None = None,
) -> None:
    """為 X 軸的範圍變化添加 JavaScript 回呼函式。

    Args:
        fig (bokeh.plotting.figure): 要添加回呼函式的 Bokeh 圖表。
        src (ColumnDataSource): Bokeh 的資料來源。
        js_code (str): 要執行的 JavaScript 程式碼字串。
    """
    length = len(src.data["index"])
    callback = CustomJS(
        args={
            "X_MIN": -0.5,  # -0.5 的原因詳 _init_xrange 的說明
            "X_MAX": length - 0.5,  # -0.5 的原因詳 _init_xrange 的說明
            "XRANGE_MIN": min(length, XRANGE_MIN),  # 先限制 XRANGE_MIN，在 js_code 中不會再檢查
            "XRANGE_MAX": min(length, XRANGE_MAX),  # 先限制 XRANGE_MAX，在 js_code 中不會再檢查
            "EPSILON": EPSILON,  # 避免因小數誤差產生 X 軸調整的無限循環
            "YRANGE_PADDING": YRANGE_PADDING,
            "x_range": fig.x_range,
            "y_range": fig.y_range,
            "src": src,
            "slider": slider,
        },
        code=js_code,
    )
    fig.x_range.js_on_change("start", callback)
    fig.x_range.js_on_change("end", callback)


def _gen_js_range(
    keys_low: list[str] | None = None,
    keys_high: list[str] | None = None,
) -> str:
    """生成用於調整 Y 軸範圍的 JavaScript 程式碼。根據當前 X 軸計算並更新 Y 軸的顯示範圍。

    Y 軸顯示範圍的計算邏輯與 _init_yrange 相同。

    Args:
        keys_low (list[str], optional): 包含用於計算 Y 軸下限的資料欄位名稱列表。預設為 None。
        keys_high (list[str], optional): 包含用於計算 Y 軸上限的資料欄位名稱列表。預設為 None。

    Returns:
        str: JavaScript程式碼字串。
    """
    str_low = '["' + '", "'.join(keys_low) + '"]' if keys_low else "[]"
    str_high = '["' + '", "'.join(keys_high) + '"]' if keys_high else "[]"
    js_code = f"""
// 先處理 X 軸的範圍
const epsilon = EPSILON;  // 避免因小數誤差的循環
const adjusted = adjusted_x_range(x_range.start, x_range.end, X_MIN, X_MAX, XRANGE_MIN, XRANGE_MAX);

const start = adjusted[0];
const end = adjusted[1];

if (slider && (!is_within_epsilon(slider.value[0], start, epsilon) || !is_within_epsilon(slider.value[1], end, epsilon))) {{
    slider.value = [start, end];
}}

if (!is_within_epsilon(x_range.start, start, epsilon) || !is_within_epsilon(x_range.end, end, epsilon)) {{
    x_range.setv({{ start: start, end: end }});
}}

// 再處理 Y 軸的範圍
const delta = 0.001
const start_idx = Math.max(0, Math.round(start + delta));
const end_idx = Math.min(src.data['index'].length - 1, Math.round(end - delta));

const keys_low = {str_low};
const keys_high = {str_high};

let y_bottom = Infinity;
let y_top = -Infinity;
const keys_all = keys_low.concat(keys_high);
for (const key of [...new Set(keys_all)]) {{
    if (key in src.data) {{
        const slice = src.data[key].slice(start_idx, end_idx + 1).filter(x => Number.isFinite(x));
        if (slice.length) {{
            y_bottom = Math.min(y_bottom, Math.min(...slice));
            y_top = Math.max(y_top, Math.max(...slice));
        }}
    }}
}}

y_bottom = keys_low.length ? y_bottom : 0;
y_top = keys_high.length ? y_top : 0;

if (!Number.isFinite(y_bottom)) y_bottom = -1;
if (!Number.isFinite(y_top)) y_top = 1;

y_bottom = y_bottom - (y_top - y_bottom) * (keys_low.length ? YRANGE_PADDING : 0);
y_top = y_top + (y_top - y_bottom) * (keys_high.length ? YRANGE_PADDING : 0);

if (Math.abs(y_bottom - y_top) < 1e-9) {{
    if (keys_low.length) y_bottom = y_bottom - 1;
    if (keys_high.length) y_top = y_top + 1;
}}

y_range.setv({{ start: y_bottom, end: y_top }});
"""
    return js_code


def _config_xaxis(
    fig: BokehFigure,
    show_labels: bool,
    date_list: list[str],
) -> None:
    """配置 X 軸。

    Args:
        fig (bokeh.plotting.figure): 要配置 X 軸的 Bokeh 圖表。
        show_labels (bool): 是否顯示 X 軸標籤。
        date_list (list[str]): X 軸的日期標籤列表。
    """
    fig.axis.major_label_text_font_size = XAXIS_FONT_SIZE
    fig.axis.major_label_text_font_style = XAXIS_FONT_STYLE

    if show_labels:
        fig.xaxis.major_label_overrides = dict(enumerate(date_list))
    else:
        fig.xaxis.major_label_overrides = dict.fromkeys(range(len(date_list)), "")


def _config_yaxis(
    fig: BokehFigure,
    label: str,
    formatter: TickFormatter | None = None,
    desired_num_ticks: int = YAXIS_MIN_TICKS,
) -> None:
    """配置 Y 軸。右側是 major label，左側是 axis label。

    Args:
        fig (bokeh.plotting.figure): 要配置 Y 軸的 Bokeh 圖表。
        label (str): Y 軸的標籤。
        formatter (bokeh.models.formatters.TickFormatter, optional): Y 軸的數值格式器。預設為 None。
        desired_num_ticks (int, optional): 期望的 Y 軸刻度數量。預設為 YAXIS_MIN_TICKS。
    """
    # 右側是 major label
    fig.yaxis[0].major_label_text_font_size = YAXIS_FONT_SIZE
    fig.yaxis[0].major_label_text_font_style = YAXIS_FONT_STYLE

    if formatter:
        fig.yaxis[0].formatter = formatter

    if desired_num_ticks:
        fig.yaxis[0].ticker.desired_num_ticks = desired_num_ticks  # type: ignore

    # 左側是 axis label
    fig.extra_y_ranges = {"extra_y": fig.y_range}  # 指定名稱為 extra_y
    extra_y = LinearAxis(y_range_name="extra_y")

    extra_y.major_label_text_font_size = "0pt"  # 不要顯示
    extra_y.major_label_text_color = None  # 不要顯示

    extra_y.axis_label = label
    extra_y.axis_label_text_font_size = YAXIS_TITLE_FONT_SIZE
    extra_y.axis_label_text_font_style = YAXIS_TITLE_FONT_STYLE

    if desired_num_ticks:
        extra_y.ticker.desired_num_ticks = desired_num_ticks

    fig.add_layout(extra_y, "left")  # 把 extra_y 放到左側


def _config_legend(
    fig: BokehFigure,
    legend_list: list[LegendItem],
) -> None:
    """配置圖例。

    Args:
        fig (bokeh.plotting.figure): 要配置圖例的 Bokeh 圖表。
        legend_list (list[LegendItem]): 圖例項目的列表。
    """
    fig.add_layout(
        Legend(
            items=legend_list,
            location=LEGEND_POSITION,
            orientation=LEGEND_ORIENTATION,
            label_text_font_size=LEGEND_FONT_SIZE,
            label_text_font_style=LEGEND_FONT_STYLE,
            background_fill_alpha=LEGEND_BACKGROUND_ALPHA,
            border_line_alpha=LEGEND_BORDER_ALPHA,
            click_policy="mute",
        )
    )


def _config_hover(
    fig: BokehFigure,
    tooltips: str,
    renderer_list: list[DataRenderer],
) -> HoverTool:
    """配置 HoverTool 工具。

    Args:
        fig (bokeh.plotting.figure): 要配置 HoverTool 的 Bokeh 圖表。
        tooltips (str): HoverTool 的提示資訊。
        renderer_list (list[DataRenderer]): 觸發 HoverTool 的渲染器列表。

    Returns:
        HoverTool: 所配置的 HoverTool 工具。
    """
    tool = HoverTool(
        tooltips=tooltips,
        renderers=renderer_list,
        mode=HOVER_MODE,
        attachment=HOVER_ATTACHMENT,
        point_policy="follow_mouse",  # "snap_to_data",
        line_policy="nearest",
    )
    fig.add_tools(tool)
    return tool


def _gen_tooltips(tooltips: list[list[str]]) -> str:
    """生成 HoverTool 的 HTML 格式提示資訊。

    Args:
        tooltips (list[list[str]]): 包含提示資訊欄位名稱和格式的列表。

    Returns:
        str: HTML 格式的提示資訊字串。
    """
    html = []

    html.append('<div style="font-size: 12pt; font-weight: bold; text-align: center;">')
    html.append("@Date")
    html.append("</div>")

    html.append('<div style="display: table; font-size: 10pt;">')
    for arr in tooltips:
        html.append('<div style="display: table-row;">')
        html.append('<div style="display: table-cell; text-align: right;">')
        html.append(f"{arr[0]}")
        html.append(":&nbsp;</div>")  # table-cell
        html.append('<div style="display: table-cell; text-align: right;">&nbsp;')
        if len(arr) == 3:
            html.append(f"@{{{arr[1]}}}{{{arr[2]}}}")
        else:
            html.append(f"@{{{arr[1]}}}")
        html.append("</div>")  # table-cell
        html.append("</div>")  # table-row
    html.append("</div>")  # table

    return "\n".join(html)


def _config_wheel_zoom(
    fig: BokehFigure,
) -> WheelZoomTool:
    """配置 WheelZoomTool 工具。

    Args:
        fig (bokeh.plotting.figure): 要配置 HoverTool 的 Bokeh 圖表。

    Returns:
        WheelZoomTool: 所配置的 WheelZoomTool 工具。
    """
    tool = WheelZoomTool(
        dimensions="width",
        maintain_focus=True,
    )
    fig.add_tools(tool)
    fig.toolbar.active_scroll = tool
    return tool


def _config_pan(
    fig: BokehFigure,
) -> PanTool:
    """配置 PanTool 工具。

    Args:
        fig (bokeh.plotting.figure): 要配置 PanTool 的 Bokeh 圖表。

    Returns:
        PanTool: 所配置的 PanTool 工具。
    """
    tool = PanTool(
        dimensions="width",
    )
    fig.add_tools(tool)
    return tool


def _config_crosshair(
    fig: BokehFigure,
) -> CrosshairTool:
    """配置 CrosshairTool 工具。

    Args:
        fig (bokeh.plotting.figure): 要配置 CrosshairTool 的 Bokeh 圖表。

    Returns:
        CrosshairTool: 所配置的 CrosshairTool 工具。
    """
    tool = CrosshairTool(
        dimensions="both",
        line_color=COLOR_DARK,
        line_width=CROSSHAIR_WIDTH,
        line_alpha=CROSSHAIR_ALPHA,
    )
    fig.add_tools(tool)
    return tool


def _config_tools(
    fig: BokehFigure,
    tooltips_setting: list[list[str]],
    renderer_list: list[DataRenderer],
) -> None:
    """配置 HoverTool, WheelZoomTool, PanTool, CrosshairTool 工具。

    Args:
        fig (bokeh.plotting.figure): 要配置 CrosshairTool 的 Bokeh 圖表。
        tooltips_setting (list[list[str]]): HoverTool 提示資訊的設定。
        renderer_list (list[DataRenderer]): 觸發 HoverTool 的渲染器列表。
    """
    _config_pan(fig)
    _config_wheel_zoom(fig)
    _config_hover(fig, _gen_tooltips(tooltips_setting), renderer_list)
    _config_crosshair(fig)


def _draw_lines(
    fig: BokehFigure,
    src: ColumnDataSource,
    keys: list[str],
    colors: list[str],
    legend_dict: dict[str, str] | None = None,
) -> tuple[list[GlyphRenderer], list[LegendItem]]:
    """在圖表上繪製多條線。

    Args:
        fig (bokeh.plotting.figure): 要繪製線條的 Bokeh 圖表。
        src (ColumnDataSource): Bokeh 的資料來源。
        keys (list[str]): 要繪製的資料欄位列表。
        colors (list[str]): 對應於每條線的顏色列表。
        legend_dict (dict[str, str], optional): 用於自訂圖例文字的字典，鍵為資料欄位名稱，值為圖例標籤。預設為 None。

    Returns:
        tuple[list[GlyphRenderer], list[LegendItem]]: 繪製的線條渲染器列表和圖例項目列表。
    """
    lines = []
    legends = []
    for key, color in zip(keys, colors):
        if key not in src.data:  # type: ignore
            current_app.logger.warning("%s, _draw_lines(...), src 資料不含鍵值: %s", __name__, key)
            continue

        line = fig.line(
            x="index",
            y=key,
            color=color,
            source=src,
            line_width=LINE_WIDTH,
            alpha=LINE_ALPHA,
            muted_line_width=LINE_WIDTH_MUTED,  # type: ignore
            muted_alpha=LINE_ALPHA_MUTED,
        )
        lines.append(line)

        label = legend_dict[key] if legend_dict and key in legend_dict else key
        legends.append(LegendItem(label=label, renderers=[line]))  # type: ignore

    return lines, legends


##
# 技術指標圖表函式
##


def candlestick_chart(
    df: pd.DataFrame,
    height: int = PLOT_HEIGHT,
    show_xaxis_labels: bool = True,
    show_range_slider: bool = False,
) -> tuple[BokehFigure, RangeSlider | None]:
    """繪製 K 線圖。

    註：仿照 Yahoo! 股市的規則，收盤價等於開盤價時標綠色。

    Args:
        df (pd.DataFrame): 包含 K 線圖資料的 DataFrame，需包含 'index', 'Date', 'open', 'high', 'low', 'close', 'volume', 'Change' 等欄位。
        height (int, optional): 圖表高度。預設為 PLOT_HEIGHT。
        show_xaxis_labels (bool, optional): 是否顯示 X 軸標籤。預設為 True。

    Returns:
        tuple[BokehFigure, RangeSlider]: Bokeh 圖表及相應的 RangeSlider 滑動條。
    """
    current_app.logger.info("%s, candlestick_chart(...), 繪製 K 線圖...", __name__)

    # 準備資料
    keys_ma = [k for k in df.keys() if re.search(r"MA\d+", k)]  # 找出所有移動平均線的欄位
    keys = ["high", "low"] + keys_ma  # 所有判斷 Y 軸範圍所需的欄位

    df_copy = df[["index", "Date"] + ["open", "close", "volume", "Change"] + keys].copy()
    df_copy["Color"] = COLOR_INC
    df_copy.loc[df_copy["close"] <= df_copy["open"], "Color"] = COLOR_DEC
    src = ColumnDataSource(df_copy)

    x_start, x_end = _init_xrange(src)  # 初始化 X 軸範圍
    y_start, y_end = _init_yrange(src, x_start, x_end, keys, keys)  # 初始化 Y 軸範圍

    # 建立圖表
    fig = BokehFigure(
        # title=title,
        # width=width,
        sizing_mode="stretch_width",
        height=height,
        x_range=Range1d(start=x_start, end=x_end),  # bounds, min_interval, max_interval 改由 _gen_js_range 控制
        y_range=Range1d(start=y_start, end=y_end),
        tools=["xzoom_in,xzoom_out,reset,save"],
        toolbar_location=None,
        y_axis_location="right",
        output_backend="webgl",
        # min_border_ 要與 slider 的 margin (..., 44, ..., 28)) 對應。
        # 並且與 index.html 中的 .left-scroll-handle 及 .right-scroll-handle 的 width 對應。
        min_border_left=28,
        min_border_right=44,
    )

    # 繪製 K 線
    fig.segment(x0="index", y0="high", x1="index", y1="low", color="Color", source=src)
    vbar = fig.vbar(x="index", width=VBAR_WIDTH, top="close", bottom="open", fill_color="Color", line_color="Color", source=src)

    # 繪製移動平均線
    _, legends = _draw_lines(fig, src, keys_ma, COLOR_SET[len(keys_ma)])

    # 配置圖表
    # fig.title.text_font_size = CANDLESTICK_TITLE_FONT_SIZE
    _config_legend(fig, legends)  # 配置圖例
    _config_xaxis(fig, show_xaxis_labels, list(src.data["Date"]))  # 配置 X 軸
    _config_yaxis(fig, CANDLESTICK_YAXIS_LABEL, NumeralTickFormatter(format=CANDLESTICK_YAXIS_FORMAT))  # 配置 Y 軸
    _config_tools(fig, CANDLESTICK_TOOLTIPS, [vbar])

    if not show_range_slider:
        _js_on_range_change(fig, src, _gen_js_range(keys, keys))  # 添加 JavaScript 回調以調整 Y 軸範圍
        return fig, None  # 不需要 RangeSlider

    # 如果需要 RangeSlider
    length = len(src.data["index"])

    slider = RangeSlider(
        # title="選擇顯示範圍",
        start=-0.5,  # 總範圍開始
        end=length - 0.5,  # 總範圍結束
        value=(x_start, x_end),  # 初始範圍，與主圖一致
        step=1,  # 步長設為1，每個數據點
        # bar_color="gray", # 可選樣式
        show_value=False,  # 通常不需要顯示滑塊的數值
        sizing_mode="stretch_width",
        # margin 要與 fig 的 min_border_left (28) 及 min_border_right (44) 對應。
        # 並且與 index.html 中的 .left-scroll-handle 及 .right-scroll-handle 的 width 對應。
        margin=(0, 44 + 8, 16, 28 + 8),
    )

    _js_on_range_change(fig, src, _gen_js_range(keys, keys), slider)  # 添加 JavaScript 回調以調整 Y 軸範圍

    slider_callback = CustomJS(
        args={
            "X_MIN": -0.5,  # -0.5 的原因詳 _init_xrange 的說明
            "X_MAX": length - 0.5,  # -0.5 的原因詳 _init_xrange 的說明
            "XRANGE_MIN": min(length, XRANGE_MIN),  # 先限制 XRANGE_MIN，在 js_code 中不會再檢查
            "XRANGE_MAX": min(length, XRANGE_MAX),  # 先限制 XRANGE_MAX，在 js_code 中不會再檢查
            "EPSILON": EPSILON,  # 避免因小數誤差產生 X 軸調整的無限循環
            "x_range": fig.x_range,
        },
        code="""
const epsilon = EPSILON;
const adjusted = adjusted_x_range(cb_obj.value[0], cb_obj.value[1], X_MIN, X_MAX, XRANGE_MIN, XRANGE_MAX);

if (!is_within_epsilon(cb_obj.value[0], adjusted[0], epsilon) || !is_within_epsilon(cb_obj.value[1], adjusted[1], epsilon)) {
    cb_obj.value = adjusted;
}

if (!is_within_epsilon(x_range.start, adjusted[0], epsilon) || !is_within_epsilon(x_range.end, adjusted[1], epsilon)) {
    x_range.setv({ start: adjusted[0], end: adjusted[1] });
}

// x_range.change.emit(); // Bokeh 3.x 通常會自動觸發
""",
    )
    # slider.js_on_change("value_throttled", slider_callback)  # 只在拖動結束時觸發，避免過於頻繁更新
    slider.js_on_change("value", slider_callback)

    return fig, slider


def volume_chart(
    df: pd.DataFrame,
    linked_x_range: Range,
    height: int = PLOT_HEIGHT_MIN,
    show_xaxis_labels: bool = True,
) -> BokehFigure:
    """繪製 Volume 指標圖。

    註：仿照 Yahoo! 股市的規則，收盤價與昨日收盤價比較來區分顏色。當收盤價與昨日收盤價相等時標灰色。

    Args:
        df (pd.DataFrame): 包含 Volume 指標資料的 DataFrame，需包含 'index', 'Date', 'volume', 'close' 等欄位。
        linked_x_range (bokeh.models.Range1d): 共享的 X 軸範圍。
        height (int, optional): 圖表高度。預設為 PLOT_HEIGHT_MIN。
        show_xaxis_labels (bool, optional): 是否顯示 X 軸標籤。預設為 True。

    Returns:
        bokeh.plotting.figure: Bokeh 圖表。
    """
    current_app.logger.info("%s, volume_chart(...), 繪製 Volume 指標圖...", __name__)

    # 準備資料
    keys = ["volume"]

    df_copy = df[["index", "Date"] + ["close"] + keys].copy()
    df_copy["Color"] = COLOR_DARK
    df_copy.loc[df_copy["close"] > df_copy["close"].shift(), "Color"] = COLOR_INC
    df_copy.loc[df_copy["close"] < df_copy["close"].shift(), "Color"] = COLOR_DEC
    src = ColumnDataSource(df_copy)

    y_start, y_end = _init_yrange(src, linked_x_range.start, linked_x_range.end, None, keys)  # type: ignore

    # 建立圖表
    fig = BokehFigure(
        # width=width,
        sizing_mode="stretch_width",
        height=height,
        x_range=linked_x_range,
        y_range=Range1d(start=y_start, end=y_end),
        tools=[],
        toolbar_location=None,
        y_axis_location="right",
        output_backend="webgl",
    )

    # 繪製 Volume 長條圖
    vbar = fig.vbar(x="index", width=VBAR_WIDTH, top="volume", bottom=0, fill_color="Color", line_color="Color", source=src)

    # 配置圖表
    _config_xaxis(fig, show_xaxis_labels, list(src.data["Date"]))
    _config_yaxis(fig, VOLUME_YAXIS_LABEL, NumeralTickFormatter(format=VOLUME_YAXIS_FORMAT))
    _js_on_range_change(fig, src, _gen_js_range(None, keys))
    _config_tools(fig, VOLUME_TOOLTIPS, [vbar])

    return fig


def kdj_chart(
    df: pd.DataFrame,
    linked_x_range: Range,
    height: int = PLOT_HEIGHT_MIN,
    show_xaxis_labels: bool = True,
) -> BokehFigure:
    """繪製 KDJ 指標圖。

    Args:
        df (pd.DataFrame): 包含 KDJ 指標資料的 DataFrame，需包含 'index', 'Date', 'K', 'D', 'J' 等欄位。
        linked_x_range (bokeh.models.Range1d): 共享的 X 軸範圍。
        height (int, optional): 圖表高度。預設為 PLOT_HEIGHT_MIN。
        show_xaxis_labels (bool, optional): 是否顯示 X 軸標籤。預設為 True。

    Returns:
        bokeh.plotting.figure: Bokeh 圖表物件。
    """
    current_app.logger.info("%s, kdj_chart(...), 繪製 KDJ 指標圖...", __name__)

    # 準備資料
    keys = ["K", "D", "J"]
    src = ColumnDataSource(df[["index", "Date"] + keys])
    y_start, y_end = _init_yrange(src, linked_x_range.start, linked_x_range.end, keys, keys)  # type: ignore

    # 創建圖表
    fig = BokehFigure(
        # width=width,
        sizing_mode="stretch_width",
        height=height,
        x_range=linked_x_range,
        y_range=Range1d(start=y_start, end=y_end),
        tools=[],
        toolbar_location=None,
        y_axis_location="right",
        output_backend="webgl",
    )

    # 繪製 K, D, J 線
    lines, legends = _draw_lines(fig, src, keys, KDJ_COLOR)

    # 配置圖表
    _config_legend(fig, legends)
    _config_xaxis(fig, show_xaxis_labels, list(src.data["Date"]))
    _config_yaxis(fig, KDJ_YAXIS_LABEL)
    _js_on_range_change(fig, src, _gen_js_range(keys, keys))
    _config_tools(fig, KDJ_TOOLTIPS, [lines[0]])

    return fig


def macd_chart(
    df: pd.DataFrame,
    linked_x_range: Range,
    height: int = PLOT_HEIGHT_MIN,
    show_xaxis_labels: bool = True,
) -> BokehFigure:
    """繪製 MACD 指標圖。

    Args:
        df (pd.DataFrame): 包含 KDJ 指標資料的 DataFrame，需包含 'index', 'Date', 'K', 'D', 'J' 等欄位。
        linked_x_range (bokeh.models.Range1d): 共享的 X 軸範圍。
        height (int, optional): 圖表高度。預設為 PLOT_HEIGHT_MIN。
        show_xaxis_labels (bool, optional): 是否顯示 X 軸標籤。預設為 True。

    Returns:
        bokeh.plotting.figure: Bokeh 圖表物件。
    """
    current_app.logger.info("%s, macd_chart(...), 繪製 MACD 指標圖...", __name__)

    # 準備資料
    keys = ["DIF", "MACD", "OSC"]

    df_copy = df[["index", "Date"] + keys].copy()
    df_copy["Color"] = COLOR_INC
    df_copy.loc[df_copy["OSC"] < 0, "Color"] = COLOR_DEC
    src = ColumnDataSource(df_copy)

    y_start, y_end = _init_yrange(src, linked_x_range.start, linked_x_range.end, keys, keys)  # type: ignore

    # 創建圖表
    fig = BokehFigure(
        # width=width,
        sizing_mode="stretch_width",
        height=height,
        x_range=linked_x_range,
        y_range=Range1d(start=y_start, end=y_end),
        tools=[],
        toolbar_location=None,
        y_axis_location="right",
        output_backend="webgl",
    )

    # 繪製 OSC 長條圖和 DIF、MACD 線
    vbar = fig.vbar(x="index", width=VBAR_WIDTH, top="OSC", bottom=0, fill_color="Color", line_color="Color", source=src)
    _, legends = _draw_lines(fig, src, ["DIF", "MACD"], MACD_COLOR)

    # 配置圖表
    _config_legend(fig, legends)
    _config_xaxis(fig, show_xaxis_labels, list(src.data["Date"]))
    _config_yaxis(fig, MACD_YAXIS_LABEL)
    _js_on_range_change(fig, src, _gen_js_range(keys, keys))
    _config_tools(fig, MACD_TOOLTIPS, [vbar])

    return fig


def rsi_chart(
    df: pd.DataFrame,
    linked_x_range: Range,
    height: int = PLOT_HEIGHT_MIN,
    show_xaxis_labels: bool = True,
) -> BokehFigure:
    """繪製 RSI 指標圖。

    Args:
        df (pd.DataFrame): 包含 RSI 指標資料的 DataFrame，需包含 'index', 'Date', 'RSI5', 'RSI10' 等欄位。
        linked_x_range (bokeh.models.Range1d): 共享的 X 軸範圍。
        height (int, optional): 圖表高度。預設為 PLOT_HEIGHT_MIN。
        show_xaxis_labels (bool, optional): 是否顯示 X 軸標籤。預設為 True。

    Returns:
        bokeh.plotting.figure: Bokeh 圖表物件。
    """
    current_app.logger.info("%s, rsi_chart(...), 繪製 RSI 指標圖...", __name__)

    # 準備資料
    keys = ["RSI5", "RSI10"]
    src = ColumnDataSource(df[["index", "Date"] + keys])
    y_start, y_end = _init_yrange(src, linked_x_range.start, linked_x_range.end, keys, keys)  # type: ignore

    # 創建圖表
    fig = BokehFigure(
        # width=width,
        sizing_mode="stretch_width",
        height=height,
        x_range=linked_x_range,
        y_range=Range1d(start=y_start, end=y_end),
        tools=[],
        toolbar_location=None,
        y_axis_location="right",
        output_backend="webgl",
    )

    # 繪製 RSI 線
    lines, legends = _draw_lines(fig, src, keys, RSI_COLOR)

    # 配置圖表
    _config_legend(fig, legends)
    _config_xaxis(fig, show_xaxis_labels, list(src.data["Date"]))
    _config_yaxis(fig, RSI_YAXIS_LABEL)
    _js_on_range_change(fig, src, _gen_js_range(keys, keys))
    _config_tools(fig, RSI_TOOLTIPS, [lines[0]])

    return fig


def bias_chart(
    df: pd.DataFrame,
    linked_x_range: Range,
    height: int = PLOT_HEIGHT_MIN,
    show_xaxis_labels: bool = True,
) -> BokehFigure:
    """繪製 BIAS 指標圖。

    Args:
        df (pd.DataFrame): 包含 BIAS 指標資料的 DataFrame，需包含 'index', 'Date', 'BIAS10', 'BIAS20', 'B10-B20' 等欄位。
        linked_x_range (bokeh.models.Range1d): 共享的 X 軸範圍。
        height (int, optional): 圖表高度。預設為 PLOT_HEIGHT_MIN。
        show_xaxis_labels (bool, optional): 是否顯示 X 軸標籤。預設為 True。

    Returns:
        bokeh.plotting.figure: Bokeh 圖表物件。
    """
    current_app.logger.info("%s, bias_chart(...), 繪製 BIAS 指標圖...", __name__)

    # 準備資料
    keys = ["BIAS10", "BIAS20", "B10-B20"]

    df_copy = df[["index", "Date"] + keys].copy()
    df_copy["Color"] = COLOR_INC
    df_copy.loc[df_copy["B10-B20"] < 0, "Color"] = COLOR_DEC
    src = ColumnDataSource(df_copy)

    y_start, y_end = _init_yrange(src, linked_x_range.start, linked_x_range.end, keys, keys)  # type: ignore

    # 創建圖表
    fig = BokehFigure(
        # width=width,
        sizing_mode="stretch_width",
        height=height,
        x_range=linked_x_range,
        y_range=Range1d(start=y_start, end=y_end),
        tools=[],
        toolbar_location=None,
        y_axis_location="right",
        output_backend="webgl",
    )

    # 繪製 B10-B20 長條圖和 BIAS10、BIAS20 線
    vbar = fig.vbar(x="index", width=VBAR_WIDTH, top="B10-B20", bottom=0, fill_color="Color", line_color="Color", source=src)
    _, legends = _draw_lines(fig, src, ["BIAS10", "BIAS20"], BIAS_COLOR)

    # 配置圖表
    _config_legend(fig, legends)
    _config_xaxis(fig, show_xaxis_labels, list(src.data["Date"]))
    _config_yaxis(fig, BIAS_YAXIS_LABEL)
    _js_on_range_change(fig, src, _gen_js_range(keys, keys))
    _config_tools(fig, BIAS_TOOLTIPS, [vbar])

    return fig


def willr_chart(
    df: pd.DataFrame,
    linked_x_range: Range,
    height: int = PLOT_HEIGHT_MIN,
    show_xaxis_labels: bool = True,
) -> BokehFigure:
    """繪製 Williams %R 指標圖。

    Args:
        df (pd.DataFrame): 包含 Williams %R 指標資料的 DataFrame，需包含 'index', 'Date', 'WILLR' 等欄位。
        linked_x_range (bokeh.models.Range1d): 共享的 X 軸範圍。
        height (int, optional): 圖表高度。預設為 PLOT_HEIGHT_MIN。
        show_xaxis_labels (bool, optional): 是否顯示 X 軸標籤。預設為 True。

    Returns:
        bokeh.plotting.figure: Bokeh 圖表物件。
    """
    current_app.logger.info("%s, willr_chart(...), 繪製 Williams %%R 指標圖...", __name__)

    # 準備資料
    keys = ["WILLR"]
    src = ColumnDataSource(df[["index", "Date"] + keys])
    y_start, y_end = _init_yrange(src, linked_x_range.start, linked_x_range.end, keys, keys)  # type: ignore

    # 創建圖表
    fig = BokehFigure(
        # width=width,
        sizing_mode="stretch_width",
        height=height,
        x_range=linked_x_range,
        y_range=Range1d(start=y_start, end=y_end),
        tools=[],
        toolbar_location=None,
        y_axis_location="right",
        output_backend="webgl",
    )

    # 繪製 Williams %R 線
    lines, legends = _draw_lines(fig, src, keys, WILLR_COLOR)

    # 配置圖表
    _config_legend(fig, legends)
    _config_xaxis(fig, show_xaxis_labels, list(src.data["Date"]))
    _config_yaxis(fig, WILLR_YAXIS_LABEL)
    _js_on_range_change(fig, src, _gen_js_range(keys, keys))
    _config_tools(fig, WILLR_TOOLTIPS, [lines[0]])

    return fig


def bbi_chart(
    df: pd.DataFrame,
    linked_x_range: Range,
    height: int = PLOT_HEIGHT_MIN,
    show_xaxis_labels: bool = True,
) -> BokehFigure:
    """繪製 BBI 指標圖。

    Args:
        df (pd.DataFrame): 包含 BBI 指標資料的 DataFrame，需包含 'index', 'Date', 'M3', 'BS', 'M3-BS' 等欄位。
        linked_x_range (bokeh.models.Range1d): 共享的 X 軸範圍。
        height (int, optional): 圖表高度。預設為 PLOT_HEIGHT_MIN。
        show_xaxis_labels (bool, optional): 是否顯示 X 軸標籤。預設為 True。

    Returns:
        bokeh.plotting.figure: Bokeh 圖表物件。
    """
    current_app.logger.info("%s, bbi_chart(...), 繪製 BBI 指標圖...", __name__)

    # 準備資料
    keys = ["M3-BS"]

    df_copy = df[["index", "Date"] + ["M3", "BS"] + keys].copy()
    df_copy["Color"] = COLOR_INC
    df_copy.loc[df_copy["M3-BS"] < 0, "Color"] = COLOR_DEC
    src = ColumnDataSource(df_copy)

    y_start, y_end = _init_yrange(src, linked_x_range.start, linked_x_range.end, keys, keys)  # type: ignore

    # 創建圖表
    fig = BokehFigure(
        # width=width,
        sizing_mode="stretch_width",
        height=height,
        x_range=linked_x_range,
        y_range=Range1d(start=y_start, end=y_end),
        tools=[],
        toolbar_location=None,
        y_axis_location="right",
        output_backend="webgl",
    )

    # 繪製 M3-BS 長條圖
    vbar = fig.vbar(x="index", width=VBAR_WIDTH, top="M3-BS", bottom=0, fill_color="Color", line_color="Color", source=src)

    # 配置圖表
    _config_xaxis(fig, show_xaxis_labels, list(src.data["Date"]))
    _config_yaxis(fig, BBI_YAXIS_LABEL, NumeralTickFormatter(format=BBI_YAXIS_FORMAT))
    _js_on_range_change(fig, src, _gen_js_range(keys, keys))
    _config_tools(fig, BBI_TOOLTIPS, [vbar])

    return fig


def cdp_chart(
    df: pd.DataFrame,
    linked_x_range: Range,
    height: int = PLOT_HEIGHT_MIN,
    show_xaxis_labels: bool = True,
) -> BokehFigure:
    """繪製 CDP 指標圖。

    Args:
        df (pd.DataFrame): 包含 CDP 指標資料的 DataFrame，需包含 'index', 'Date', 'AH', 'NH', 'CDP', 'NL', 'AL' 等欄位。
        linked_x_range (bokeh.models.Range1d): 共享的 X 軸範圍。
        height (int, optional): 圖表高度。預設為 PLOT_HEIGHT_MIN。
        show_xaxis_labels (bool, optional): 是否顯示 X 軸標籤。預設為 True。

    Returns:
        bokeh.plotting.figure: Bokeh 圖表物件。
    """
    current_app.logger.info("%s, cdp_chart(...), 繪製 CDP 指標圖...", __name__)

    # 準備資料
    keys = ["AH", "NH", "CDP", "NL", "AL"]
    src = ColumnDataSource(df[["index", "Date"] + keys])
    y_start, y_end = _init_yrange(src, linked_x_range.start, linked_x_range.end, keys, keys)  # type: ignore

    # 創建圖表
    fig = BokehFigure(
        # width=width,
        sizing_mode="stretch_width",
        height=height,
        x_range=linked_x_range,
        y_range=Range1d(start=y_start, end=y_end),
        tools=[],
        toolbar_location=None,
        y_axis_location="right",
        output_backend="webgl",
    )

    # 繪製 CDP 線
    lines, legends = _draw_lines(fig, src, keys, COLOR_SET[5])

    # 配置圖表
    _config_legend(fig, legends)
    _config_xaxis(fig, show_xaxis_labels, list(src.data["Date"]))
    _config_yaxis(fig, CDP_YAXIS_LABEL, NumeralTickFormatter(format=CDP_YAXIS_FORMAT))
    _js_on_range_change(fig, src, _gen_js_range(keys, keys))
    _config_tools(fig, CDP_TOOLTIPS, [lines[0]])

    return fig


def dmi_chart(
    df: pd.DataFrame,
    linked_x_range: Range,
    height: int = PLOT_HEIGHT_MIN,
    show_xaxis_labels: bool = True,
) -> BokehFigure:
    """繪製 DMI 指標圖。

    Args:
        df (pd.DataFrame): 包含 DMI 指標資料的 DataFrame，需包含 'index', 'Date', 'PLUS_DI', 'MINUS_DI', 'ADX', 'ADXR' 等欄位。
        linked_x_range (bokeh.models.Range1d): 共享的 X 軸範圍。
        height (int, optional): 圖表高度。預設為 PLOT_HEIGHT_MIN。
        show_xaxis_labels (bool, optional): 是否顯示 X 軸標籤。預設為 True。

    Returns:
        bokeh.plotting.figure: Bokeh 圖表物件。
    """
    current_app.logger.info("%s, dmi_chart(...), 繪製 DMI 指標圖...", __name__)

    # 準備資料
    keys = ["PLUS_DI", "MINUS_DI", "ADX", "ADXR"]
    src = ColumnDataSource(df[["index", "Date"] + keys])
    y_start, y_end = _init_yrange(src, linked_x_range.start, linked_x_range.end, keys, keys)  # type: ignore

    # 創建圖表
    fig = BokehFigure(
        # width=width,
        sizing_mode="stretch_width",
        height=height,
        x_range=linked_x_range,
        y_range=Range1d(start=y_start, end=y_end),
        tools=[],
        toolbar_location=None,
        y_axis_location="right",
        output_backend="webgl",
    )

    # 繪製 CDP 線
    lines, legends = _draw_lines(fig, src, keys, COLOR_SET[4], legend_dict=DMI_LEGEND_DICT)

    # 配置圖表
    _config_legend(fig, legends)
    _config_xaxis(fig, show_xaxis_labels, list(src.data["Date"]))
    _config_yaxis(fig, DMI_YAXIS_LABEL)
    _js_on_range_change(fig, src, _gen_js_range(keys, keys))
    _config_tools(fig, DMI_TOOLTIPS, [lines[0]])

    return fig


def bbands_chart(
    df: pd.DataFrame,
    linked_x_range: Range,
    height: int = PLOT_HEIGHT_MIN,
    show_xaxis_labels: bool = True,
) -> BokehFigure:
    """繪製 BBands 指標圖。

    Args:
        df (pd.DataFrame): 包含 BBands 指標資料的 DataFrame，需包含 'index', 'Date', 'BBL', 'BBM', 'BBU' 等欄位。
        linked_x_range (bokeh.models.Range1d): 共享的 X 軸範圍。
        height (int, optional): 圖表高度。預設為 PLOT_HEIGHT_MIN。
        show_xaxis_labels (bool, optional): 是否顯示 X 軸標籤。預設為 True。

    Returns:
        bokeh.plotting.figure: Bokeh 圖表物件。
    """
    current_app.logger.info("%s, bbands_chart(...), 繪製 BBands 指標圖...", __name__)

    # 準備資料
    keys = ["BBL", "BBM", "BBU"]
    src = ColumnDataSource(df[["index", "Date"] + keys])
    y_start, y_end = _init_yrange(src, linked_x_range.start, linked_x_range.end, keys, keys)  # type: ignore

    fig = BokehFigure(
        # width=width,
        sizing_mode="stretch_width",
        height=height,
        x_range=linked_x_range,
        y_range=Range1d(start=y_start, end=y_end),
        tools=[],
        toolbar_location=None,
        y_axis_location="right",
        output_backend="webgl",
    )

    # 繪製上中下軌
    lines, legends = _draw_lines(fig, src, keys, COLOR_SET[3])  # , legend_dict=BBANDS_LEGEND_DICT)

    # 填充上下軌之間的區域
    area = fig.varea(
        x="index",
        y1="BBL",
        y2="BBU",
        source=src,
        color=BBANDS_AREA_COLOR,
        fill_alpha=BBANDS_AREA_FILL_ALPHA,
        muted_alpha=AREA_ALPHA_MUTED,
    )
    area_legend = LegendItem(label=BBANDS_AREA_LABEL, renderers=[area])  # type: ignore

    _config_legend(fig, legends + [area_legend])
    _config_xaxis(fig, show_xaxis_labels, list(src.data["Date"]))
    _config_yaxis(fig, BBANDS_YAXIS_LABEL, NumeralTickFormatter(format=BBANDS_YAXIS_FORMAT))
    _js_on_range_change(fig, src, _gen_js_range(keys, keys))
    _config_tools(fig, BBANDS_TOOLTIPS, [lines[1]])

    return fig


def obv_chart(
    df: pd.DataFrame,
    linked_x_range: Range,
    height: int = PLOT_HEIGHT_MIN,
    show_xaxis_labels: bool = True,
) -> BokehFigure:
    """繪製 OBV 指標圖。

    Args:
        df (pd.DataFrame): 包含 OBV 指標資料的 DataFrame，需包含 'index', 'Date', 'OBV' 等欄位。
        linked_x_range (bokeh.models.Range1d): 共享的 X 軸範圍。
        height (int, optional): 圖表高度。預設為 PLOT_HEIGHT_MIN。
        show_xaxis_labels (bool, optional): 是否顯示 X 軸標籤。預設為 True。

    Returns:
        bokeh.plotting.figure: Bokeh 圖表物件。
    """
    current_app.logger.info("%s, obv_chart(...), 繪製 OBV 指標圖...", __name__)

    # 準備資料
    keys = ["OBV"]
    src = ColumnDataSource(df[["index", "Date"] + keys])
    y_start, y_end = _init_yrange(src, linked_x_range.start, linked_x_range.end, keys, keys)  # type: ignore

    # 創建圖表
    fig = BokehFigure(
        # width=width,
        sizing_mode="stretch_width",
        height=height,
        x_range=linked_x_range,
        y_range=Range1d(start=y_start, end=y_end),
        tools=[],
        toolbar_location=None,
        y_axis_location="right",
        output_backend="webgl",
    )

    # 繪製 OBV 線
    lines, legends = _draw_lines(fig, src, keys, OBV_COLOR)

    # 配置圖表
    _config_legend(fig, legends)
    _config_xaxis(fig, show_xaxis_labels, list(src.data["Date"]))
    _config_yaxis(fig, OBV_YAXIS_LABEL, NumeralTickFormatter(format=OBV_YAXIS_FORMAT))
    _js_on_range_change(fig, src, _gen_js_range(keys, keys))
    _config_tools(fig, OBV_TOOLTIPS, [lines[0]])

    return fig


def cci_chart(
    df: pd.DataFrame,
    linked_x_range: Range,
    height: int = PLOT_HEIGHT_MIN,
    show_xaxis_labels: bool = True,
) -> BokehFigure:
    """繪製 CCI 指標圖。

    Args:
        df (pd.DataFrame): 包含 OBV 指標資料的 DataFrame，需包含 'index', 'Date', 'OBV' 等欄位。
        linked_x_range (bokeh.models.Range1d): 共享的 X 軸範圍。
        height (int, optional): 圖表高度。預設為 PLOT_HEIGHT_MIN。
        show_xaxis_labels (bool, optional): 是否顯示 X 軸標籤。預設為 True。

    Returns:
        bokeh.plotting.figure: Bokeh 圖表物件。
    """
    current_app.logger.info("%s, cci_chart(...), 繪製 CCI 指標圖...", __name__)

    # 準備資料
    keys = ["CCI"]
    src = ColumnDataSource(df[["index", "Date"] + keys])
    y_start, y_end = _init_yrange(src, linked_x_range.start, linked_x_range.end, keys, keys)  # type: ignore

    # 創建圖表
    fig = BokehFigure(
        # width=width,
        sizing_mode="stretch_width",
        height=height,
        x_range=linked_x_range,
        y_range=Range1d(start=y_start, end=y_end),
        tools=[],
        toolbar_location=None,
        y_axis_location="right",
        output_backend="webgl",
    )

    # 繪製 CCI 線
    lines, legends = _draw_lines(fig, src, keys, CCI_COLOR)

    # 配置圖表
    _config_legend(fig, legends)
    _config_xaxis(fig, show_xaxis_labels, list(src.data["Date"]))
    _config_yaxis(fig, CCI_YAXIS_LABEL)
    _js_on_range_change(fig, src, _gen_js_range(keys, keys))
    _config_tools(fig, CCI_TOOLTIPS, [lines[0]])

    return fig


def draw(df: pd.DataFrame, indicators: list[str]) -> GridPlot | None:
    """繪製所有圖表

    Args:
        df (pd.DataFrame): 股票資料的 DataFrame。
        indicators (list[str]): 要求顯示的指標。

    Returns:
        GridPlot | None: 包含所有圖表的 Bokeh gridplot 佈局，如果繪製失敗則返回 None。
    """
    current_app.logger.info("%s, draw(df, %s), 開始繪製圖表...", __name__, indicators)

    charts = []
    try:
        fig, slider = candlestick_chart(df, show_xaxis_labels=True, show_range_slider=True)
        if not isinstance(fig, BokehFigure) or not isinstance(slider, RangeSlider):
            raise ValueError("K 線圖繪製失敗")

        # fig_with_slider = column(fig, slider, sizing_mode="stretch_width")
        # charts.append([fig_with_slider])
        charts.append([fig])
        charts.append([slider])

        chart_funcs = [
            ("Volume 指標圖", volume_chart),
            ("KDJ 指標圖", kdj_chart),
            ("MACD 指標圖", macd_chart),
            ("RSI 指標圖", rsi_chart),
            ("BIAS 指標圖", bias_chart),
            ("Williams %R 指標圖", willr_chart),
            ("BBI 指標圖", bbi_chart),
            ("CDP 指標圖", cdp_chart),
            ("DMI 指標圖", dmi_chart),
            ("BBands 指標圖", bbands_chart),
            ("OBV 指標圖", obv_chart),
            ("CCI 指標圖", cci_chart),
        ]

        linked_x_range = fig.x_range
        for name, func in chart_funcs:
            indicator = func.__name__.replace("_chart", "")
            if indicator not in indicators:
                continue

            show_x = indicator == indicators[-1]
            height = PLOT_HEIGHT_MIN + 16 if show_x else PLOT_HEIGHT_MIN

            fig = func(df, linked_x_range, height, show_xaxis_labels=show_x)
            if not isinstance(fig, BokehFigure):
                raise ValueError(f"{name}繪製失敗")

            charts.append([fig])

        layout = gridplot(
            charts,
            sizing_mode="stretch_width",
            toolbar_location="above",
            merge_tools=True,
        )

        current_app.logger.info("%s, draw(df, %s), 繪製圖表完成", __name__, indicators)
        return layout

    except Exception as e:  # pylint: disable=broad-exception-caught
        current_app.logger.error("%s, draw(df, %s), 預期外錯誤: %s", __name__, indicators, e, exc_info=True)
        return None


if __name__ == "__main__":
    pass
