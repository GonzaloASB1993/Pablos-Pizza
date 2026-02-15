import { Helmet } from 'react-helmet-async'

const SEO = ({
  title,
  description,
  keywords,
  image = '/assets/logo.png',
  url,
  type = 'website',
  noindex = false
}) => {
  const siteUrl = 'https://pablospizza.cl'
  const defaultTitle = "Pablo's Pizza - Talleres de Pizza para Niños en Santiago"
  const defaultDescription = "Talleres de pizza para niños y pizza parties en Santiago. Experiencias gastronómicas educativas donde los niños aprenden a hacer pizzas artesanales. Servicio a domicilio."
  const defaultKeywords = "talleres pizza niños Santiago, pizza party cumpleaños, eventos infantiles Santiago, taller cocina niños, catering pizza Santiago, fiestas infantiles Chile, pizzeros en acción, experiencias gastronómicas niños"

  const finalTitle = title ? `${title} | Pablo's Pizza` : defaultTitle
  const finalDescription = description || defaultDescription
  const finalKeywords = keywords || defaultKeywords
  const finalUrl = url ? `${siteUrl}${url}` : siteUrl
  const finalImage = image.startsWith('http') ? image : `${siteUrl}${image}`

  return (
    <Helmet>
      {/* Primary Meta Tags */}
      <title>{finalTitle}</title>
      <meta name="title" content={finalTitle} />
      <meta name="description" content={finalDescription} />
      <meta name="keywords" content={finalKeywords} />
      <meta name="author" content="Pablo's Pizza" />

      {/* Robots */}
      {noindex ? (
        <meta name="robots" content="noindex, nofollow" />
      ) : (
        <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1" />
      )}

      {/* Canonical URL */}
      <link rel="canonical" href={finalUrl} />

      {/* Open Graph / Facebook */}
      <meta property="og:type" content={type} />
      <meta property="og:url" content={finalUrl} />
      <meta property="og:title" content={finalTitle} />
      <meta property="og:description" content={finalDescription} />
      <meta property="og:image" content={finalImage} />
      <meta property="og:image:alt" content="Pablo's Pizza - Talleres de pizza para niños" />
      <meta property="og:site_name" content="Pablo's Pizza" />
      <meta property="og:locale" content="es_CL" />

      {/* Twitter */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:url" content={finalUrl} />
      <meta name="twitter:title" content={finalTitle} />
      <meta name="twitter:description" content={finalDescription} />
      <meta name="twitter:image" content={finalImage} />

      {/* Geo Tags for local SEO */}
      <meta name="geo.region" content="CL-RM" />
      <meta name="geo.placename" content="Santiago, Chile" />
      <meta name="geo.position" content="-33.4489;-70.6693" />
      <meta name="ICBM" content="-33.4489, -70.6693" />
    </Helmet>
  )
}

export default SEO
