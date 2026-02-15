const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const publicDir = path.join(__dirname, '../public');

async function optimizeImage(inputPath, outputPath, options = {}) {
  const { width = 1200, quality = 80 } = options;

  try {
    await sharp(inputPath)
      .resize(width, null, { withoutEnlargement: true })
      .webp({ quality })
      .toFile(outputPath);

    const inputStats = fs.statSync(inputPath);
    const outputStats = fs.statSync(outputPath);
    const savings = ((1 - outputStats.size / inputStats.size) * 100).toFixed(1);

    console.log(`✅ ${path.basename(inputPath)} → ${path.basename(outputPath)}`);
    console.log(`   ${(inputStats.size / 1024).toFixed(0)}KB → ${(outputStats.size / 1024).toFixed(0)}KB (${savings}% smaller)`);

    return true;
  } catch (err) {
    console.error(`❌ Error optimizing ${inputPath}:`, err.message);
    return false;
  }
}

async function main() {
  console.log('🖼️  Optimizing images...\n');

  // Optimize pizza-party.png (2.6MB!)
  const pizzaPartyPng = path.join(publicDir, 'images/pizza-party.png');
  const pizzaPartyWebp = path.join(publicDir, 'images/pizza-party.webp');

  if (fs.existsSync(pizzaPartyPng)) {
    await optimizeImage(pizzaPartyPng, pizzaPartyWebp, { width: 1200, quality: 85 });
  }

  // Optimize taller-corporativo.jpg
  const tallerCorp = path.join(publicDir, 'images/talleres/taller-corporativo.jpg');
  const tallerCorpWebp = path.join(publicDir, 'images/talleres/taller-corporativo.webp');

  if (fs.existsSync(tallerCorp)) {
    await optimizeImage(tallerCorp, tallerCorpWebp, { width: 1200, quality: 85 });
  }

  console.log('\n✨ Image optimization complete!');
}

main().catch(console.error);
