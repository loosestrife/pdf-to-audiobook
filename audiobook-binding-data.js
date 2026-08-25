const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

function getDurationMs(filePath) {
  const stdout = execSync(
    `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${filePath}"`,
    { encoding: 'utf-8' }
  );
  return Math.round(parseFloat(stdout.trim()) * 1000);
}

function toTitleCase(str) {
  return str.replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.slice(1).toLowerCase());
}

function generateAudiobookMetadata({inDir='.', outDir='.'}) {
  const files = fs.readdirSync(inDir).filter((file) => file.endsWith('.wav'));

  const wavFiles = files.sort((a, b) => {
    const numA = a.match(/^\d+/);
    const numB = b.match(/^\d+/);

    if (numA && numB) {
      return parseInt(numA[0], 10) - parseInt(numB[0], 10);
    }
    if (numA) return -1;
    if (numB) return 1;
    return a.localeCompare(b);
  });

  const ffmpegList = [];
  const metadataLines = [';FFMETADATA1'];
  let currentTimeMs = 0;

  // 2. Parse durations and build metadata
  for (const wavFile of wavFiles) {
    const durationMs = getDurationMs(wavFile);

    // Clean chapter title (e.g., "01_chapter_one.wav" -> "Chapter One")
    const baseName = path.parse(wavFile).name;
    let title = baseName.replace(/^\d+[_\s-]*/, '').replace(/_/g, ' ');
    title = toTitleCase(title).trim();
    if (!title) {
      title = baseName;
    }

    const start = currentTimeMs;
    const end = currentTimeMs + durationMs;

    metadataLines.push(
      '\n[CHAPTER]',
      'TIMEBASE=1/1000',
      `START=${start}`,
      `END=${end}`,
      `title=${title}`
    );

    // Format line for concat list file
    const escapedFile = wavFile.replace(/'/g, "'\\''");
    ffmpegList.push(`file '${escapedFile}'`);

    currentTimeMs = end;
  }

  // Write temporary control files
  const controlfiles = ['FFMETADATAFILE', 'list.txt'].map(n => path.join(outDir, n));
  fs.writeFileSync(controlfiles[0], metadataLines.join('\n'), 'utf-8');
  fs.writeFileSync(controlfiles[1], ffmpegList.join('\n'), 'utf-8');
  return controlFiles;
}

if(require.main == module){
  generateAudiobookMetadata()
  console.log(
    'now do a ffmpeg -y -f concat -safe 0 -i list.txt -i FFMETADATAFILE -map_metadata 1 -c:a aac -b:a 64k output.m4b'
  );
} else {
  module.exports = generateAudiobookMetadata();
}