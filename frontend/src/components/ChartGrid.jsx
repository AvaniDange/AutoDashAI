import React from 'react';
import {
    BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area
} from 'recharts';

const COLORS = ['#4F46E5', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

const ChartItem = ({ chart }) => {
    const { type, title, data, dataKey, xAxis } = chart;

    const CommonTooltip = () => (
        <Tooltip
            contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)', padding: '12px' }}
            cursor={{ fill: '#F3F4F6', opacity: 0.5 }}
        />
    );

    const renderChart = () => {
        switch (type) {
            case 'bar':
                return (
                    <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                        <XAxis dataKey={xAxis} tick={{ fontSize: 11, fill: '#6B7280' }} interval={0} angle={-20} textAnchor="end" height={50} tickLine={false} axisLine={false} />
                        <YAxis tick={{ fontSize: 11, fill: '#6B7280' }} tickLine={false} axisLine={false} />
                        <CommonTooltip />
                        <Bar dataKey={dataKey} fill="#4F46E5" radius={[6, 6, 0, 0]} maxBarSize={60}>
                            {data.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                        </Bar>
                    </BarChart>
                );
            case 'line':
                return (
                    <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                        <XAxis dataKey={xAxis} tick={{ fontSize: 11, fill: '#6B7280' }} tickLine={false} axisLine={false} />
                        <YAxis tick={{ fontSize: 11, fill: '#6B7280' }} tickLine={false} axisLine={false} />
                        <CommonTooltip />
                        <Line type="monotone" dataKey={dataKey} stroke="#8B5CF6" strokeWidth={3} dot={{ r: 4, strokeWidth: 2, fill: '#fff' }} activeDot={{ r: 6, strokeWidth: 0 }} />
                    </LineChart>
                );
            case 'area':
                return (
                    <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                        <XAxis dataKey={xAxis} tick={{ fontSize: 11, fill: '#6B7280' }} tickLine={false} axisLine={false} />
                        <YAxis tick={{ fontSize: 11, fill: '#6B7280' }} tickLine={false} axisLine={false} />
                        <CommonTooltip />
                        <Area type="monotone" dataKey={dataKey} stroke="#10B981" fill="#D1FAE5" strokeWidth={2} />
                    </AreaChart>
                );
            case 'pie':
                return (
                    <PieChart margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                        <Pie
                            data={data}
                            cx="50%"
                            cy="50%"
                            innerRadius={70}
                            outerRadius={100}
                            paddingAngle={2}
                            dataKey="value"
                        >
                            {data.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} strokeWidth={0} />
                            ))}
                        </Pie>
                        <Tooltip />
                        <Legend
                            verticalAlign="bottom"
                            height={36}
                            iconType="circle"
                            formatter={(value) => <span className="text-sm text-gray-600 ml-1">{value}</span>}
                        />
                    </PieChart>
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
        <div className="bg-white p-6 rounded-3xl shadow-sm border border-gray-100 hover:shadow-xl transition-all duration-300 h-[420px] flex flex-col group">
            <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-bold text-gray-800 truncate" title={title}>{title}</h3>
                <div className="bg-gray-50 text-gray-400 text-xs px-2 py-1 rounded-md uppercase font-medium group-hover:bg-blue-50 group-hover:text-blue-500 transition-colors">
                    {type}
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

const ChartGrid = ({ charts }) => {
    if (!charts || charts.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center h-[500px] text-gray-400 bg-white/50 rounded-3xl border-2 border-dashed border-gray-200 p-12 backdrop-blur-sm">
                <div className="bg-white p-6 rounded-full shadow-lg mb-6">
                    <span className="text-6xl">📊</span>
                </div>
                <h3 className="text-xl font-bold text-gray-800 mb-2">No charts yet</h3>
                <p className="text-gray-500">Upload data to see insights here.</p>
            </div>
        )
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 pb-10">
            {charts.map((chart) => (
                <ChartItem key={chart.id} chart={chart} />
            ))}
        </div>
    );
};

export default ChartGrid;
