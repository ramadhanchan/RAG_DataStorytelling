const ACCENT = ['#d28b5b', '#8fa68a', '#c9b27c', '#a3786a', '#7f8b93', '#b98f6d'];
const ACCENT_SOFT = ['rgba(210,139,91,.62)', 'rgba(143,166,138,.62)', 'rgba(201,178,124,.62)', 'rgba(163,120,106,.62)', 'rgba(127,139,147,.62)', 'rgba(185,143,109,.62)'];
const ACCENT_FILL = ['rgba(210,139,91,.16)', 'rgba(143,166,138,.16)', 'rgba(201,178,124,.16)', 'rgba(163,120,106,.16)', 'rgba(127,139,147,.16)', 'rgba(185,143,109,.16)'];
const GRID = 'rgba(140,130,115,.18)';
const TICK = '#8d8577';

function styleDatasets(type, datasets) {
  return datasets.map((dataset, index) => {
    const strong = ACCENT[index % ACCENT.length];
    if (type === 'pie') {
      return {
        ...dataset,
        backgroundColor: dataset.backgroundColor || ACCENT_SOFT,
        borderColor: dataset.borderColor || 'rgba(19,18,16,.65)',
        borderWidth: dataset.borderWidth ?? 2,
        hoverOffset: 6,
      };
    }
    return {
      ...dataset,
      borderColor: dataset.borderColor || strong,
      backgroundColor: dataset.backgroundColor || (type === 'line' ? ACCENT_FILL[index % ACCENT_FILL.length] : strong),
      borderWidth: dataset.borderWidth ?? (type === 'line' ? 2 : 0),
      borderRadius: type === 'bar' ? 6 : undefined,
      tension: type === 'line' ? 0.35 : undefined,
      fill: type === 'line' ? true : undefined,
      pointBackgroundColor: type === 'line' ? strong : undefined,
      pointBorderColor: type === 'line' ? 'rgba(19,18,16,.65)' : undefined,
    };
  });
}

export function mapChartSpecToChartJs(spec) {
  if (!spec || !['bar', 'line', 'pie'].includes(spec.type)) return null;
  if (!Array.isArray(spec.labels) || !Array.isArray(spec.datasets) || spec.datasets.some(d => !Array.isArray(d.data) || d.data.length !== spec.labels.length)) return null;
  return {
    type: spec.type,
    data: {labels: spec.labels, datasets: styleDatasets(spec.type, spec.datasets)},
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {duration: 450},
      plugins: {
        title: {display: Boolean(spec.title), text: spec.title || '', color: TICK, font: {size: 12, weight: '600'}},
        legend: {display: spec.datasets.length > 1 || spec.type === 'pie', labels: {color: TICK, boxWidth: 10, boxHeight: 10, usePointStyle: true, font: {size: 11}}},
      },
      scales: spec.type === 'pie' ? undefined : {
        x: {title: {display: Boolean(spec.xLabel), text: spec.xLabel || '', color: TICK}, grid: {color: GRID}, ticks: {color: TICK}},
        y: {title: {display: Boolean(spec.yLabel), text: spec.yLabel || '', color: TICK}, grid: {color: GRID}, ticks: {color: TICK}, beginAtZero: true},
      },
    },
  };
}
