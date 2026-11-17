import React from 'react';

export default function ScoreGauge({ label, score, size = 180 }) {
  const percentage = score !== undefined && score !== null ? Math.round(score * 100) : null;

  // Status Colors: Green (low), Amber (moderate), Red (high risk)
  let strokeColor = '#10b981';
  let textColor = '#059669';
  if (percentage >= 70) {
    strokeColor = '#ef4444';
    textColor = '#dc2626';
  } else if (percentage >= 30) {
    strokeColor = '#f59e0b';
    textColor = '#d97706';
  }

  const strokeWidth = 14;
  const viewBoxWidth = 200;
  const viewBoxHeight = 120;
  const cx = 100;
  const cy = 105;
  const radius = 75;
  const circumference = Math.PI * radius; // 235.62
  const strokeDashoffset = percentage !== null
    ? circumference - (percentage / 100) * circumference
    : circumference;

  const startX = cx - radius;
  const startY = cy;
  const endX = cx + radius;
  const endY = cy;

  // Upward rainbow arch from left (0%) to right (100%)
  const arcPath = `M ${startX} ${startY} A ${radius} ${radius} 0 0 1 ${endX} ${endY}`;

  return (
    <div className="flex flex-col items-center justify-center my-1 select-none">
      <div style={{ width: size, maxWidth: '100%' }}>
        <svg
          viewBox={`0 0 ${viewBoxWidth} ${viewBoxHeight}`}
          className="w-full h-auto overflow-visible"
        >
          {/* Background Track Arc */}
          <path
            d={arcPath}
            fill="none"
            stroke="#e2e8f0"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />

          {/* Active Value Progress Arc */}
          {percentage !== null && (
            <path
              d={arcPath}
              fill="none"
              stroke={strokeColor}
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              style={{
                transition: 'stroke-dashoffset 1s cubic-bezier(0.16, 1, 0.3, 1), stroke 0.4s ease',
              }}
            />
          )}

          {/* Centered Score Inside Arch */}
          <text
            x={cx}
            y={cy - 12}
            textAnchor="middle"
            fill={percentage !== null ? textColor : '#94a3b8'}
            style={{
              fontSize: '28px',
              fontWeight: '800',
              fontFamily: 'inherit',
            }}
          >
            {percentage !== null ? percentage : 'N/A'}
            <tspan
              dx="2"
              dy="-1"
              style={{
                fontSize: '15px',
                fontWeight: '600',
                fill: '#94a3b8',
              }}
            >
              /100
            </tspan>
          </text>
        </svg>
      </div>

      {/* Label with clean, non-overlapping spacing */}
      {label && (
        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mt-3 text-center">
          {label}
        </div>
      )}
    </div>
  );
}
