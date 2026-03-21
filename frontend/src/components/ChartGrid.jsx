import {
    BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area,
    ScatterChart, Scatter, ZAxis
} from 'recharts';
import { Table, ArrowUpRight, ArrowDownRight, MoreHorizontal } from 'lucide-react';

const COLORS = ['#4F46E5', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

const ChartItem = ({ chart, theme }) => {
    const { type, title, subtitle, data, dataKey, xAxis } = chart;
    const isDark = theme === 'dark';
    // Map histogram to bar for rendering
    const renderType = type === 'histogram' ? 'bar' : type;

    const CommonTooltip = () => (
        <Tooltip
            contentStyle={{
                borderRadius: '16px',
                border: 'none',
                boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1)',
                padding: '16px',
                backgroundColor: isDark ? '#1e293b' : '#fff',
                color: isDark ? '#f1f5f9' : '#1f2937'
            }}
            itemStyle={{ fontSize: '12px', fontWeight: 'bold' }}
            cursor={{ fill: isDark ? '#334155' : '#F3F4F6', opacity: 0.4 }}
        />
    );

    const axisColor = isDark ? '#475569' : '#94a3b8';
    const gridColor = isDark ? '#1e293b' : '#f1f5f9';

    const renderChart = () => {
        switch (renderType) {
            case 'bar':
                return (
                    <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="0" vertical={false} stroke={gridColor} />
                        <XAxis
                            dataKey={xAxis}
                            tick={{ fontSize: 10, fill: axisColor, fontWeight: 700 }}
                            tickFormatter={(val) => val.length > 15 ? val.substring(0, 12) + '...' : val}
                            interval={0}
                            angle={-25}
                            textAnchor="end"
                            height={60}
                            tickLine={false}
                            axisLine={false}
                        />
                        <YAxis tick={{ fontSize: 10, fill: axisColor, fontWeight: 700 }} tickLine={false} axisLine={false} />
                        <CommonTooltip />
                        <Bar dataKey={dataKey} fill="#4F46E5" radius={[8, 8, 0, 0]} maxBarSize={40}>
                            {data.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                        </Bar>
                    </BarChart>
                );
            case 'line':
                return (
                    <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridColor} />
                        <XAxis
                            dataKey={xAxis}
                            tick={{ fontSize: 10, fill: axisColor, fontWeight: 700 }}
                            tickFormatter={(val) => String(val).length > 20 ? String(val).substring(0, 17) + '...' : val}
                            tickLine={false}
                            axisLine={false}
                        />
                        <YAxis tick={{ fontSize: 10, fill: axisColor, fontWeight: 700 }} tickLine={false} axisLine={false} />
                        <CommonTooltip />
                        <Line type="monotone" dataKey={dataKey} stroke="#6366f1" strokeWidth={4} dot={{ r: 4, strokeWidth: 2, fill: isDark ? '#1e293b' : '#fff' }} activeDot={{ r: 6, strokeWidth: 0 }} />
                    </LineChart>
                );
            case 'area':
                return (
                    <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                        <defs>
                            <linearGradient id="colorArea" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridColor} />
                        <XAxis
                            dataKey={xAxis}
                            tick={{ fontSize: 10, fill: axisColor, fontWeight: 700 }}
                            tickFormatter={(val) => val === 'index' ? '' : (String(val).length > 20 ? String(val).substring(0, 17) + '...' : val)}
                            tickLine={false}
                            axisLine={false}
                        />
                        <YAxis tick={{ fontSize: 10, fill: axisColor, fontWeight: 700 }} tickLine={false} axisLine={false} />
                        <CommonTooltip />
                        <Area type="monotone" dataKey={dataKey} stroke="#6366f1" fillOpacity={1} fill="url(#colorArea)" strokeWidth={3} />
                    </AreaChart>
                );
            case 'pie':
                return (
                    <PieChart margin={{ top: 0, right: 0, left: 0, bottom: 20 }}>
                        <Pie
                            data={data}
                            cx="50%"
                            cy="50%"
                            innerRadius={70}
                            outerRadius={100}
                            paddingAngle={5}
                            dataKey={dataKey}
                            nameKey={xAxis}
                            stroke="none"
                        >
                            {data.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                        </Pie>
                        <CommonTooltip />
                        <Legend
                            verticalAlign="bottom"
                            align="center"
                            iconType="circle"
                            iconSize={8}
                            wrapperStyle={{
                                paddingTop: '20px',
                                bottom: 0,
                                left: 0,
                                width: '100%',
                                fontSize: '10px'
                            }}
                            formatter={(value) => {
                                const maxLength = 25;
                                const displayValue = value.length > maxLength
                                    ? value.substring(0, maxLength) + '...'
                                    : value;
                                return (
                                    <span className={`font-black uppercase tracking-tight ml-1 ${isDark ? 'text-slate-500' : 'text-gray-400'}`} title={value}>
                                        {displayValue}
                                    </span>
                                );
                            }}
                        />
                    </PieChart>
                );
            case 'scatter':
                return (
                    <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                        <XAxis type="number" dataKey={xAxis} name={xAxis} tick={{ fontSize: 10, fill: axisColor }} tickLine={false} axisLine={false} />
                        <YAxis type="number" dataKey={dataKey} name={dataKey} tick={{ fontSize: 10, fill: axisColor }} tickLine={false} axisLine={false} />
                        <ZAxis type="number" range={[60, 400]} />
                        <CommonTooltip />
                        <Scatter name={title} data={data} fill="#6366f1">
                            {data.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} fillOpacity={0.6} />
                            ))}
                        </Scatter>
                    </ScatterChart>
                );
            case 'table':
                return (
                    <div className="h-full overflow-hidden flex flex-col">
                        <div className={`overflow-y-auto flex-1 rounded-2xl border ${isDark ? 'border-slate-800' : 'border-gray-100'}`}>
                            <table className="w-full text-left text-sm">
                                <thead className={`sticky top-0 z-10 ${isDark ? 'bg-slate-800' : 'bg-gray-50'}`}>
                                    <tr>
                                        <th className="px-4 py-3 font-black text-[10px] uppercase tracking-wider">{xAxis}</th>
                                        <th className="px-4 py-3 font-black text-[10px] uppercase tracking-wider">{dataKey}</th>
                                        <th className="px-4 py-3 font-black text-[10px] uppercase tracking-wider">Trend</th>
                                    </tr>
                                </thead>
                                <tbody className={`divide-y ${isDark ? 'divide-slate-800' : 'divide-gray-50'}`}>
                                    {data.slice(0, 10).map((row, i) => (
                                        <tr key={i} className={`group ${isDark ? 'hover:bg-slate-800/50' : 'hover:bg-blue-50/50'}`}>
                                            <td className="px-4 py-3 font-bold truncate max-w-[120px]">{row[xAxis]}</td>
                                            <td className={`px-4 py-3 font-mono font-bold ${isDark ? 'text-indigo-400' : 'text-blue-600'}`}>
                                                {typeof row[dataKey] === 'number' ? row[dataKey].toLocaleString() : row[dataKey]}
                                            </td>
                                            <td className="px-4 py-3">
                                                {Math.random() > 0.5
                                                    ? <ArrowUpRight size={14} className="text-emerald-500" />
                                                    : <ArrowDownRight size={14} className="text-red-500" />
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
                        <span className="text-3xl mb-2">❓</span>
                        <span>Unsupported Chart Type</span>
                    </div>
                );
        }
    };

    return (
        <div className={`p-6 rounded-[32px] transition-all duration-500 h-[450px] flex flex-col group border shadow-xl ${isDark
            ? 'bg-slate-900 border-slate-800 hover:border-indigo-500/30'
            : 'bg-white border-white hover:border-blue-500/20 shadow-gray-200/50 hover:shadow-2xl'
            }`}>
            <div className="flex items-center justify-between mb-6 shrink-0">
                <div className="flex items-center gap-3 overflow-hidden">
                    <div className={`p-2 rounded-xl shrink-0 ${isDark ? 'bg-slate-800 text-indigo-400' : 'bg-gray-50 text-blue-600'}`}>
                        {type === 'table' ? <Table size={16} /> : <ArrowUpRight size={16} />}
                    </div>
                    <div className="overflow-hidden">
                        <h3 className={`text-base font-black truncate tracking-tight ${isDark ? 'text-slate-100' : 'text-gray-800'}`} title={title}>{title}</h3>
                        {subtitle && <p className={`text-[10px] font-bold truncate ${isDark ? 'text-slate-500' : 'text-gray-400'}`}>{subtitle}</p>}
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <div className={`text-[9px] px-2 py-0.5 rounded-full uppercase font-black tracking-widest transition-colors ${isDark ? 'bg-slate-800 text-slate-500 group-hover:text-indigo-400' : 'bg-gray-50 text-gray-400 group-hover:text-blue-500'
                        }`}>
                        {type}
                    </div>
                    <button className={`p-1 rounded-lg ${isDark ? 'text-slate-600 hover:text-slate-400' : 'text-gray-300 hover:text-gray-500'}`}>
                        <MoreHorizontal size={14} />
                    </button>
                </div>
            </div>
            <div className="flex-1 min-h-0 w-full">
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
            <div className={`flex flex-col items-center justify-center h-[500px] rounded-[40px] border-2 border-dashed p-12 backdrop-blur-sm transition-colors ${isDark ? 'bg-slate-900/50 border-slate-800 text-slate-500' : 'bg-white/50 border-gray-200 text-gray-400'
                }`}>
                <div className={`p-8 rounded-full shadow-2xl mb-8 ${isDark ? 'bg-slate-800 shadow-indigo-500/10' : 'bg-white shadow-blue-500/10'}`}>
                    <span className="text-7xl">📊</span>
                </div>
                <h3 className={`text-2xl font-black mb-3 ${isDark ? 'text-slate-200' : 'text-gray-800'}`}>Ready for Analysis?</h3>
                <p className={`text-sm font-medium ${isDark ? 'text-slate-500' : 'text-gray-500'}`}>Upload your first dataset to generate a professional BI dashboard instantly.</p>
            </div>
        )
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10 pb-16">
            {charts.map((chart) => (
                <ChartItem key={chart.id} chart={chart} theme={theme} />
            ))}
        </div>
    );
};

export default ChartGrid;
