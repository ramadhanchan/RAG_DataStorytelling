import {describe, it, expect} from 'vitest';
import {mapChartSpecToChartJs} from '../src/chartMapper';

describe('mapChartSpecToChartJs', () => {
  const validBar = {type: 'bar', title: 'Sales Q3', labels: ['Fiction', 'Non-Fiction'], datasets: [{label: 'Qty', data: [100, 200]}], xLabel: 'Genre', yLabel: 'Units', insight: 'Fiction leads'};
  const validLine = {type: 'line', title: 'Trend', labels: ['Jan', 'Feb'], datasets: [{label: 'Qty', data: [50, 80]}], xLabel: 'Month', yLabel: 'Units'};
  const validPie = {type: 'pie', title: 'Share', labels: ['A', 'B'], datasets: [{label: 'Pct', data: [30, 70]}], insight: 'B dominates'};

  it('maps valid bar chart spec', () => {
    const cfg = mapChartSpecToChartJs(validBar);
    expect(cfg.type).toBe('bar');
    expect(cfg.data.labels).toEqual(['Fiction', 'Non-Fiction']);
    expect(cfg.options.plugins.title.text).toBe('Sales Q3');
    expect(cfg.options.scales.x.title.text).toBe('Genre');
    expect(cfg.options.scales.y.title.text).toBe('Units');
  });

  it('maps valid line chart spec', () => {
    const cfg = mapChartSpecToChartJs(validLine);
    expect(cfg.type).toBe('line');
    expect(cfg.data.datasets[0].data).toEqual([50, 80]);
  });

  it('maps valid pie chart spec without scales', () => {
    const cfg = mapChartSpecToChartJs(validPie);
    expect(cfg.type).toBe('pie');
    expect(cfg.options.scales).toBeUndefined();
  });

  it('returns null for null/undefined spec', () => {
    expect(mapChartSpecToChartJs(null)).toBeNull();
    expect(mapChartSpecToChartJs(undefined)).toBeNull();
  });

  it('returns null for unsupported chart type', () => {
    expect(mapChartSpecToChartJs({type: 'radar', labels: [], datasets: []})).toBeNull();
  });

  it('returns null for mismatched label/data lengths', () => {
    expect(mapChartSpecToChartJs({type: 'bar', labels: ['A'], datasets: [{data: [10, 20]}]})).toBeNull();
  });

  it('returns null for non-array datasets', () => {
    expect(mapChartSpecToChartJs({type: 'bar', labels: ['A'], datasets: 'not-array'})).toBeNull();
  });

  it('returns null for non-array labels', () => {
    expect(mapChartSpecToChartJs({type: 'bar', labels: 'not-array', datasets: []})).toBeNull();
  });

  it('retains insight in spec but does not include it in Chart.js config', () => {
    const cfg = mapChartSpecToChartJs(validBar);
    expect(cfg.insight).toBeUndefined();
    expect(cfg.options.plugins.tooltip).toBeUndefined();
  });

  it('handles empty labels/datasets gracefully', () => {
    const cfg = mapChartSpecToChartJs({type: 'bar', title: '', labels: ['X'], datasets: [{label: '', data: [0]}], xLabel: '', yLabel: ''});
    expect(cfg).not.toBeNull();
    expect(cfg.data.labels).toEqual(['X']);
  });
});
