import React from 'react';
import {
    BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area,
    ScatterChart, Scatter, ZAxis, FunnelChart, Funnel, LabelList, Treemap
} from 'recharts';
import { Table, ArrowUpRight, ArrowDownRight, MoreHorizontal } from 'lucide-react';

const COLORS = ['#00B7C3', '#008272', '#E66C37', '#B146C2', '#E044A7', '#118DFF'];

// Custom Treemap Content for Power BI look
const TreemapContent = (props) => {
    const { x, y, width, height, index, name, value, isDark } = props;

    // Hide text if box is too small
    if (width < 50 || height < 35) return (
        <g>
            <rect
                x={x}
                y={y}
                width={width}
                height={height}
                style={{
                    fill: COLORS[index % COLORS.length],
                    stroke: '#fff',
                    strokeWidth: 2,
                    strokeOpacity: 1,
                }}
            />
        </g>
    );

    const fontSize = Math.min(width / 8, 12);
    const displayValue = typeof value === 'number' ?
        (value >= 1000000 ? `${(value / 1000000).toFixed(1)}M` :
            value >= 1000 ? `${(value / 1000).toFixed(1)}K` : value.toLocaleString())
        : value;

    return (
        <g>
            <rect
                x={x}
                y={y}
                width={width}
                height={height}
                style={{
                    fill: COLORS[index % COLORS.length],
                    stroke: '#fff',
                    strokeWidth: 2,
                    strokeOpacity: 1,
                }}
            />
            <text
                x={x + width / 2}
                y={y + height / 2 - 6}
                textAnchor="middle"
                fill="#fff"
                fontSize={fontSize}
                fontFamily="Segoe UI"
                fontWeight="bold"
                style={{ pointerEvents: 'none' }}
            >
                {String(name).length > 10 ? String(name).substring(0, 8) + '..' : name}
            </text>
            <text
                x={x + width / 2}
                y={y + height / 2 + 8}
                textAnchor="middle"
                fill="#fff"
                fontSize={fontSize - 2}
                fontFamily="Segoe UI"
                fillOpacity={0.9}
                style={{ pointerEvents: 'none' }}
            >
                {displayValue}
            </text>
        </g>
    );
};

const ChartItem = ({ chart, theme }) => {
    const { type, title, data, dataKey, xAxis } = chart;
    const isDark = theme === 'dark';

    const CommonTooltip = () => (
        <Tooltip
            contentStyle={{
                borderRadius: '0px',
                border: isDark ? '1px solid #334155' : '1px solid #EDEBE9',
                boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                padding: '12px',
                backgroundColor: isDark ? '#1e293b' : '#fff',
                color: isDark ? '#f1f5f9' : '#323130',
                fontFamily: '"Segoe UI", sans-serif'
            }}
            itemStyle={{ fontSize: '11px', fontWeight: 'bold' }}
            cursor={{ fill: isDark ? '#334155' : '#F3F2F1', opacity: 0.4 }}
        />
    );

    const axisColor = isDark ? '#94a3b8' : '#605E5C';
    const gridColor = isDark ? '#1e293b' : '#EDEBE9';
    const fontFamily = '"Segoe UI", sans-serif';

    const renderChart = () => {
        if (!data || data.length === 0) return (
            <div className="flex items-center justify-center h-full text-xs text-gray-400">No data available</div>
        );

        switch (type) {
            case 'area':
                return (
                    <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                        <defs>
                            <linearGradient id="colorArea" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#00B7C3" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#00B7C3" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="0" vertical={false} stroke={gridColor} />
                        <XAxis
                            dataKey={xAxis}
                            tick={{ fontSize: 10, fill: axisColor, fontWeight: 600, fontFamily }}
                            tickFormatter={(val) => val === 'index' ? '' : (String(val).length > 20 ? String(val).substring(0, 17) + '...' : val)}
                            tickLine={false}
                            axisLine={false}
                            interval="preserveStartEnd"
                        />
                        <YAxis tick={{ fontSize: 10, fill: axisColor, fontWeight: 600, fontFamily }} tickLine={false} axisLine={false} />
                        <CommonTooltip />
                        <Area type="monotone" dataKey={dataKey} stroke="#00B7C3" fillOpacity={1} fill="url(#colorArea)" strokeWidth={2} />
                    </AreaChart>
                );
            case 'line':
                return (
                    <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="0" vertical={false} stroke={gridColor} />
                        <XAxis
                            dataKey={xAxis}
                            tick={{ fontSize: 10, fill: axisColor, fontWeight: 600, fontFamily }}
                            tickFormatter={(val) => val === 'index' ? '' : val}
                            tickLine={false}
                            axisLine={false}
                        />
                        <YAxis tick={{ fontSize: 10, fill: axisColor, fontWeight: 600, fontFamily }} tickLine={false} axisLine={false} />
                        <CommonTooltip />
                        <Line type="monotone" dataKey={dataKey} stroke="#00B7C3" strokeWidth={3} dot={false} activeDot={{ r: 6, fill: '#00B7C3' }} />
                    </LineChart>
                );
            case 'pie':
            case 'donut':
                return (
                    <PieChart margin={{ top: 0, bottom: 0 }}>
                        <Pie
                            data={data}
                            cx="50%"
                            cy="50%"
                            innerRadius={type === 'pie' ? 0 : 55}
                            outerRadius={80}
                            paddingAngle={2}
                            dataKey={dataKey}
                            labelLine={false}
                            label={({ cx, cy, midAngle, innerRadius, outerRadius, percent, index, name, value }) => {
                                const RADIAN = Math.PI / 180;
                                const radius = outerRadius + 25;
                                const x = cx + radius * Math.cos(-midAngle * RADIAN);
                                const y = cy + radius * Math.sin(-midAngle * RADIAN);

                                const formattedVal = value >= 1000000 ? `$${(value / 1000000).toFixed(1)}M` :
                                    value >= 1000 ? `$${(value / 1000).toFixed(1)}K` : `$${value.toFixed(0)}`;

                                return (
                                    <text
                                        x={x}
                                        y={y}
                                        fill={isDark ? "#cbd5e1" : "#323130"}
                                        textAnchor={x > cx ? 'start' : 'end'}
                                        dominantBaseline="central"
                                        fontSize="9"
                                        fontWeight="700"
                                        fontFamily={fontFamily}
                                    >
                                        {`${name} ${formattedVal}`}
                                    </text>
                                );
                            }}
                        >
                            {data.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} stroke={isDark ? '#1e293b' : '#fff'} strokeWidth={2} />
                            ))}
                        </Pie>
                        <CommonTooltip />
                        <Legend
                            layout="vertical"
                            align="right"
                            verticalAlign="middle"
                            iconType="circle"
                            formatter={(value) => <span style={{ color: axisColor, fontSize: '10px', fontWeight: 600, fontFamily }}>{String(value).substring(0, 10)}</span>}
                        />
                    </PieChart>
                );
            case 'bar':
                const isHorizontal = chart.layout === 'vertical';
                return (
                    <BarChart
                        layout={isHorizontal ? 'vertical' : 'horizontal'}
                        data={data}
                        margin={{ top: 10, right: 30, left: isHorizontal ? 0 : 0, bottom: 0 }}
                    >
                        <CartesianGrid strokeDasharray="0" vertical={!isHorizontal} horizontal={isHorizontal} stroke={gridColor} />
                        {isHorizontal ? (
                            <>
                                <XAxis type="number" domain={[0, 'auto']} hide />
                                <YAxis
                                    dataKey={xAxis}
                                    type="category"
                                    width={140}
                                    tick={{ fontSize: 11, fill: axisColor, fontWeight: 600, fontFamily }}
                                    tickLine={false}
                                    axisLine={false}
                                    interval={0}
                                />
                            </>
                        ) : (
                            <>
                                <XAxis
                                    dataKey={xAxis}
                                    tick={{ fontSize: 9, fill: axisColor, fontWeight: 600, fontFamily }}
                                    tickFormatter={(val) => String(val).length > 8 ? String(val).substring(0, 7) + '...' : val}
                                    interval={0}
                                    angle={-45}
                                    textAnchor="end"
                                    height={60}
                                    tickLine={false}
                                    axisLine={false}
                                />
                                <YAxis tick={{ fontSize: 10, fill: axisColor, fontWeight: 600, fontFamily }} tickLine={false} axisLine={false} />
                            </>
                        )}
                        <CommonTooltip />
                        <Bar dataKey={dataKey} fill="#00B7C3" radius={0}>
                            {data.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                        </Bar>
                    </BarChart>
                );

            case 'gauge':
                const score = parseFloat(data[0]?.[dataKey] || 0);
                const target = parseFloat(data[0]?.target || 100);

                // Simple percentage for visualization
                const percent = Math.min(100, Math.max(0, (score / target) * 100));

                const gaugeData = [
                    { name: 'value', value: percent },
                    { name: 'rest', value: 100 - percent }
                ];

                const formatGaugeVal = (val) => {
                    if (val >= 1_000_000_000) return (val / 1_000_000_000).toFixed(1) + 'B';
                    if (val >= 1_000_000) return (val / 1_000_000).toFixed(1) + 'M';
                    if (val >= 1_000) return (val / 1_000).toFixed(1) + 'K';
                    return val.toLocaleString();
                };

                return (
                    <div className="flex flex-col items-center justify-center h-full relative p-4">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart margin={{ top: 0, bottom: 0 }}>
                                <Pie
                                    data={gaugeData}
                                    cx="50%"
                                    cy="60%"
                                    startAngle={180}
                                    endAngle={0}
                                    innerRadius={70}
                                    outerRadius={90}
                                    paddingAngle={2}
                                    dataKey="value"
                                    stroke="none"
                                >
                                    <Cell fill={score >= target ? '#107C10' : '#00B7C3'} />
                                    <Cell fill={isDark ? '#334155' : '#E1DFDD'} />
                                </Pie>
                            </PieChart>
                        </ResponsiveContainer>
                        <div className="absolute top-[55%] left-1/2 -translate-x-1/2 text-center w-full pointer-events-none">
                            <span className={`text-4xl font-bold tracking-tighter ${isDark ? 'text-white' : 'text-[#323130]'}`}>
                                {formatGaugeVal(score)}
                            </span>
                            <div className="flex flex-col items-center justify-center mt-0">
                                <span className={`text-[10px] uppercase font-bold tracking-widest ${isDark ? 'text-slate-400' : 'text-[#605E5C]'}`}>
                                    Target
                                </span>
                                <span className={`text-sm font-semibold ${isDark ? 'text-slate-300' : 'text-[#323130]'}`}>
                                    {formatGaugeVal(target)}
                                </span>
                            </div>
                        </div>
                    </div>
                );
            case 'scatter':
                return (
                    <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                        <XAxis type="number" dataKey={xAxis} name={xAxis} tick={{ fontSize: 10, fill: axisColor, fontFamily }} tickLine={false} axisLine={false} />
                        <YAxis type="number" dataKey={dataKey} name={dataKey} tick={{ fontSize: 10, fill: axisColor, fontFamily }} tickLine={false} axisLine={false} />
                        <ZAxis type="number" range={[50, 200]} />
                        <CommonTooltip />
                        <Scatter name={title} data={data} fill="#118DFF">
                            {data.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} fillOpacity={0.8} />
                            ))}
                        </Scatter>
                    </ScatterChart>
                );
            case 'table':
                return (
                    <div className="h-full overflow-hidden flex flex-col">
                        <div className={`overflow-y-auto flex-1 border ${isDark ? 'border-slate-800' : 'border-[#EDEBE9]'}`}>
                            <table className="w-full text-left text-xs border-collapse">
                                <thead className={`sticky top-0 z-10 ${isDark ? 'bg-slate-800' : 'bg-[#F3F2F1]'}`}>
                                    <tr>
                                        <th className="px-3 py-2 font-bold uppercase tracking-tight text-[#605E5C]">{xAxis}</th>
                                        <th className="px-3 py-2 font-bold uppercase tracking-tight text-[#605E5C]">{dataKey}</th>
                                        <th className="px-3 py-2 font-bold uppercase tracking-tight text-[#605E5C]">Trend</th>
                                    </tr>
                                </thead>
                                <tbody className={`divide-y ${isDark ? 'divide-slate-800' : 'divide-[#F3F2F1]'}`}>
                                    {data.slice(0, 15).map((row, i) => (
                                        <tr key={i} className={`group ${isDark ? 'hover:bg-slate-800' : 'hover:bg-[#F3F2F1]'}`}>
                                            <td className="px-3 py-2 font-medium truncate max-w-[120px]">{row[xAxis]}</td>
                                            <td className={`px-3 py-2 font-bold ${isDark ? 'text-indigo-400' : 'text-[#118DFF]'}`}>
                                                {typeof row[dataKey] === 'number' ? row[dataKey].toLocaleString() : row[dataKey]}
                                            </td>
                                            <td className="px-3 py-2">
                                                {Math.random() > 0.5
                                                    ? <ArrowUpRight size={12} className="text-[#107C10]" />
                                                    : <ArrowDownRight size={12} className="text-red-600" />
                                                }
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                );
            default:
                return (
                    <div className="flex flex-col items-center justify-center h-full text-gray-400">
                        <span>Unsupported Chart Type</span>
                    </div>
                );
        }
    };

    return (
        <div className={`p-5 transition-all h-[400px] flex flex-col border shadow-sm ${isDark
            ? 'bg-slate-900 border-slate-800'
            : 'bg-white border-[#EDEBE9] hover:shadow-md'
            }`}>
            <div className="flex items-center justify-between mb-4 shrink-0">
                <div className="flex items-center gap-2 overflow-hidden">
                    <h3 className={`text-sm font-bold truncate tracking-tight ${isDark ? 'text-slate-100' : 'text-[#323130]'}`} style={{ fontFamily }} title={title}>{title}</h3>
                </div>
                <div className="flex items-center gap-2">
                    <button className={`p-1 rounded-sm ${isDark ? 'text-slate-600 hover:text-slate-400' : 'text-[#A19F9D] hover:text-[#323130]'}`}>
                        <MoreHorizontal size={14} />
                    </button>
                </div>
            </div>
            <div className="flex-1 min-h-0 w-full overflow-hidden">
                <ResponsiveContainer width="100%" height="100%">
                    {renderChart()}
                </ResponsiveContainer>
            </div>
        </div>
    );
};

const ChartGrid = ({ charts, theme }) => {
    const isDark = theme === 'dark';
    if (!charts || charts.length === 0) {
        return (
            <div className={`flex flex-col items-center justify-center h-[500px] border-2 border-dashed p-12 transition-colors ${isDark ? 'bg-slate-900/50 border-slate-800 text-slate-500' : 'bg-white border-[#EDEBE9] text-[#A19F9D]'
                }`}>
                <h3 className={`text-xl font-bold mb-2 ${isDark ? 'text-slate-200' : 'text-[#323130]'}`}>Explore Your Data</h3>
                <p className="text-sm">Power BI styled visualizations will appear here.</p>
            </div>
        )
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pb-16">
            {charts.map((chart) => (
                <ChartItem key={chart.id} chart={chart} theme={theme} />
            ))}
        </div>
    );
};

export default ChartGrid;
