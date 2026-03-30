import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

export default function XAIPanel({ keywords }) {
  if (!keywords || keywords.length === 0) return null

  const data = keywords.map(([word, weight]) => ({
    word,
    weight: Math.abs(weight),
    positive: weight > 0,
  }))

  return (
    <div className="sg-card !p-4">
      <div className="sec-label mb-3">TF-IDF Feature Analysis</div>
      <div className="font-mono text-[10px] text-[var(--muted)] mb-3 tracking-wider">
        TOP CONTRIBUTING KEYWORDS
      </div>
      <ResponsiveContainer width="100%" height={data.length * 36 + 20}>
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 20, bottom: 0, left: 60 }}>
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="word"
            tick={{ fill: '#4a7090', fontFamily: "'Share Tech Mono', monospace", fontSize: 11 }}
            width={55}
          />
          <Tooltip
            contentStyle={{
              background: '#08111c',
              border: '1px solid #112233',
              borderRadius: 8,
              fontFamily: "'Share Tech Mono', monospace",
              fontSize: 11,
              color: '#d8eaf8',
            }}
            formatter={(val) => [val.toFixed(3), 'Weight']}
          />
          <Bar dataKey="weight" radius={[0, 4, 4, 0]} barSize={14}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.positive ? '#e8203c' : '#00aaff'} fillOpacity={0.7} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
