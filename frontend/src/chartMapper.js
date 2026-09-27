export function mapChartSpecToChartJs(spec) {
  if (!spec || !['bar', 'line', 'pie'].includes(spec.type)) return null;
  if (!Array.isArray(spec.labels) || !Array.isArray(spec.datasets) || spec.datasets.some(d => !Array.isArray(d.data) || d.data.length !== spec.labels.length)) return null;
  return {type: spec.type, data: {labels: spec.labels, datasets: spec.datasets}, options: {responsive: true, plugins: {title: {display: Boolean(spec.title), text: spec.title || ''}}, scales: spec.type === 'pie' ? undefined : {x: {title: {display: Boolean(spec.xLabel), text: spec.xLabel || ''}}, y: {title: {display: Boolean(spec.yLabel), text: spec.yLabel || ''}}}}};
}
