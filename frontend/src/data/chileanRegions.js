// Solo comunas de la Región Metropolitana - Pablo's Pizza opera únicamente en Santiago
export const santiagoComunas = [
  'Alhué',
  'Buin',
  'Calera de Tango',
  'Cerrillos',
  'Cerro Navia',
  'Colina',
  'Conchalí',
  'Curacaví',
  'El Bosque',
  'El Monte',
  'Estación Central',
  'Huechuraba',
  'Independencia',
  'Isla de Maipo',
  'La Cisterna',
  'La Florida',
  'La Granja',
  'La Pintana',
  'La Reina',
  'Lampa',
  'Las Condes',
  'Lo Barnechea',
  'Lo Espejo',
  'Lo Prado',
  'Macul',
  'Maipú',
  'María Pinto',
  'Melipilla',
  'Ñuñoa',
  'Padre Hurtado',
  'Paine',
  'Pedro Aguirre Cerda',
  'Peñaflor',
  'Peñalolén',
  'Pirque',
  'Providencia',
  'Pudahuel',
  'Puente Alto',
  'Quilicura',
  'Quinta Normal',
  'Recoleta',
  'Renca',
  'San Bernardo',
  'San Joaquín',
  'San José de Maipo',
  'San Miguel',
  'San Pedro',
  'San Ramón',
  'Santiago',
  'Talagante',
  'Tiltil',
  'Vitacura'
].sort()

// Mantener compatibilidad hacia atrás
export const chileanRegions = [
  {
    id: 'RM',
    name: 'Región Metropolitana',
    comunas: santiagoComunas
  }
]

export const getAllComunas = () => {
  return santiagoComunas.map(comuna => ({
    comuna,
    region: 'Región Metropolitana',
    regionId: 'RM'
  }))
}

// Defaults usados como fallback si el API no responde
export const DEFAULT_COMUNAS_LEJANAS = [
  'Quilicura',
  'Lampa',
  'Colina',
  'Huechuraba'
]

export const DEFAULT_CARGO_COMUNA_LEJANA = 20000

// Kept for backwards compatibility - will be overridden by API values
export const comunasLejanas = DEFAULT_COMUNAS_LEJANAS
export const CARGO_COMUNA_LEJANA = DEFAULT_CARGO_COMUNA_LEJANA

export const isComunaLejana = (comuna, listaComunas = DEFAULT_COMUNAS_LEJANAS) => {
  if (!comuna) return false
  return listaComunas.some(c => c.toLowerCase() === comuna.toLowerCase())
}
