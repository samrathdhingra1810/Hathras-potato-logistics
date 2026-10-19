import { CircleMarker, MapContainer, Popup, TileLayer, Tooltip } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { Card } from '../components/ui/Card.jsx';
import { StatusBadge, AssumptionTag, LEVELS } from '../components/ui/StatusBadge.jsx';
import { fmtPct, fmtTonnes } from '../services/format.js';

// Standard OSM tiles (no key). Dark mode dims them with a CSS filter on the tile pane.
// For production traffic, point this at your own tile server or a keyed provider.
const TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

// Radius scales with block storage demand (area ∝ tonnes).
// Map markers are drawn as SVG attributes, so pass literal colors (status hexes are mode-invariant).
const STATUS_HEX = { good: '#0ca30c', warning: '#fab219', serious: '#ec835a', critical: '#d03b3b' };
const SURFACE_HEX = { light: '#fcfcfb', dark: '#1a1a19' };

const radiusFor = (demandT, maxDemand) => 10 + 18 * Math.sqrt(demandT / maxDemand);

export function GisView({ center, blocks, theme, season }) {
  const maxDemand = Math.max(...blocks.map((b) => b.demandT));
  const sorted = [...blocks].sort((a, b) => b.utilisation - a.utilisation);

  return (
    <Card
      title="Block-level storage strain"
      subtitle={`Projected demand ÷ local capacity by development block, ${season}`}
      actions={<AssumptionTag>Block split is modelled</AssumptionTag>}
    >
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
        <div className="relative h-[380px] overflow-hidden rounded-md border border-line lg:col-span-3">
          <MapContainer center={[center.lat, center.lng]} zoom={10} scrollWheelZoom={false} className="h-full w-full">
            <TileLayer url={TILE_URL} attribution={ATTRIBUTION} maxZoom={19} />
            {blocks.map((b) => {
              const color = STATUS_HEX[b.level];
              return (
                <CircleMarker
                  key={b.id}
                  center={[b.lat, b.lng]}
                  radius={radiusFor(b.demandT, maxDemand)}
                  pathOptions={{ color: SURFACE_HEX[theme], weight: 2, fillColor: color, fillOpacity: 0.78 }}
                >
                  <Tooltip direction="top" offset={[0, -6]} opacity={1} permanent>
                    <span className="text-[11px] font-semibold">{b.name}</span>
                  </Tooltip>
                  <Popup>
                    <div className="min-w-[180px] space-y-1 text-xs">
                      <p className="text-sm font-semibold">{b.name} block</p>
                      <p>Storage demand: {fmtTonnes(b.demandT)}</p>
                      <p>Local capacity: {fmtTonnes(b.capacityT)}</p>
                      <p>Utilisation: {fmtPct(b.utilisation)}</p>
                      <p>{b.gapT >= 0 ? `Headroom ${fmtTonnes(b.gapT)}` : `Shortfall ${fmtTonnes(-b.gapT)}`}</p>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}
          </MapContainer>
          <div className="pointer-events-none absolute bottom-2 left-2 z-[400] rounded-md border border-line bg-surface px-2 py-1.5 text-[11px] text-ink-2">
            <p className="mb-1 font-medium text-ink">Strain level</p>
            {Object.entries(LEVELS).map(([k, l]) => (
              <p key={k} className="flex items-center gap-1.5">
                <span aria-hidden="true" style={{ color: l.color }}>
                  {l.icon}
                </span>
                {l.label}
              </p>
            ))}
            <p className="mt-1 text-ink-muted">Size ∝ storage demand</p>
          </div>
        </div>

        <div className="lg:col-span-2">
          <table className="tabular w-full text-xs">
            <thead className="text-ink-muted">
              <tr className="border-b border-line text-left">
                <th className="py-1.5 font-medium">Block</th>
                <th className="py-1.5 text-right font-medium">Demand</th>
                <th className="py-1.5 text-right font-medium">Capacity</th>
                <th className="py-1.5 text-right font-medium">Util.</th>
                <th className="py-1.5 text-right font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((b) => (
                <tr key={b.id} className="border-b border-line last:border-0">
                  <td className="py-1.5 font-medium text-ink">{b.name}</td>
                  <td className="py-1.5 text-right text-ink">{fmtTonnes(b.demandT)}</td>
                  <td className="py-1.5 text-right text-ink">{fmtTonnes(b.capacityT)}</td>
                  <td className="py-1.5 text-right text-ink">{fmtPct(b.utilisation, { digits: 0 })}</td>
                  <td className="py-1.5 text-right">
                    <StatusBadge level={b.level} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-3 text-[11px] leading-relaxed text-ink-muted">
            District demand and capacity are split across blocks using modelled shares (see <code>shared/dataset.js</code>).
            Block markers sit at approximate block HQ locations. Swap in block-level production and the cold storage
            registry to make this layer authoritative.
          </p>
        </div>
      </div>
    </Card>
  );
}
