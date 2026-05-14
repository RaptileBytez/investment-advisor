/**
 * ChartView — TradingView lightweight-charts wrapper.
 *
 * Renders an OHLCV history series. Defaults to candlesticks; pass
 * `type="line"` for a single-close line chart. Resizes on container
 * width changes via ResizeObserver. Tears down the chart on unmount.
 */

import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type LineData,
  type UTCTimestamp,
} from "lightweight-charts";

import type { HistoryBar } from "@/api/client";

interface ChartViewProps {
  bars: HistoryBar[];
  type?: "candlestick" | "line";
  height?: number;
  className?: string;
}

export function ChartView({ bars, type = "candlestick", height = 360, className }: ChartViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick" | "Line"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "rgba(120,120,120,0.9)",
      },
      grid: {
        vertLines: { color: "rgba(120,120,120,0.08)" },
        horzLines: { color: "rgba(120,120,120,0.08)" },
      },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false, secondsVisible: false },
      crosshair: { mode: 0 },
      autoSize: true,
    });
    chartRef.current = chart;
    seriesRef.current =
      type === "line"
        ? chart.addLineSeries({ priceLineVisible: false, lineWidth: 2 })
        : chart.addCandlestickSeries();

    const observer = new ResizeObserver(() => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [type, height]);

  useEffect(() => {
    if (!seriesRef.current) return;
    if (type === "line") {
      const data: LineData[] = bars.map((b) => ({
        time: (Date.parse(b.date) / 1000) as UTCTimestamp,
        value: b.close,
      }));
      (seriesRef.current as ISeriesApi<"Line">).setData(data);
    } else {
      const data: CandlestickData[] = bars.map((b) => ({
        time: (Date.parse(b.date) / 1000) as UTCTimestamp,
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      }));
      (seriesRef.current as ISeriesApi<"Candlestick">).setData(data);
    }
    chartRef.current?.timeScale().fitContent();
  }, [bars, type]);

  return (
    <div
      ref={containerRef}
      className={className}
      style={{ width: "100%", height }}
      role="img"
      aria-label="Price chart"
    />
  );
}
