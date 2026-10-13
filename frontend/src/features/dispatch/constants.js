// In other words: the depth "tiers" decide which data sources the backend queries.
export const TIERS = {
  1: { label: 'Quick', sources: ['weather', 'fire'] },
  2: { label: 'Standard', sources: ['weather', 'air_quality', 'fire', 'geo'] },
  3: { label: 'Deep', sources: ['weather', 'air_quality', 'fire', 'earthquake', 'geo'] },
};
export const PRESETS = {
  cairo: { label: 'Cairo Smoke Inversion', location: 'Cairo', country: 'Egypt', tier: 2, question: 'Is smoke from nearby agricultural fires reaching the city?' },
  izmit: { label: 'İzmit Industrial Seismic', location: 'İzmit', country: 'Turkey', tier: 3, question: 'Are seismic or industrial hazards affecting air quality around İzmit?' },
  pelop: { label: 'Peloponnese Wildfire Corridor', location: 'Peloponnese', country: 'Greece', tier: 2, question: 'Are wildfires in the Peloponnese threatening nearby areas through smoke?' },
};
export const SRC_LABEL = { air_quality: 'OpenAQ', fire: 'NASA FIRMS', weather: 'Open-Meteo', earthquake: 'USGS', geo: 'OSM / Geoapify' };
