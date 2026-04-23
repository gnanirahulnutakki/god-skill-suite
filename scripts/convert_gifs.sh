#!/bin/bash
# Converts key video clips to optimized palette GIFs for README embedding
# Using 2-pass palette generation for best quality/size ratio

VIDEOS_DIR="videos"
GIFS_DIR="assets/gifs"
mkdir -p "$GIFS_DIR"

convert_gif() {
  local input="$1"
  local output="$2"
  local fps="${3:-12}"
  local width="${4:-480}"

  echo "Converting: $(basename $input) → $(basename $output)"
  
  # Pass 1: generate optimal palette
  ffmpeg -y -i "$input" \
    -vf "fps=$fps,scale=$width:-1:flags=lanczos,palettegen=stats_mode=diff" \
    /tmp/palette.png -loglevel error

  # Pass 2: encode GIF using palette
  ffmpeg -y -i "$input" -i /tmp/palette.png \
    -lavfi "fps=$fps,scale=$width:-1:flags=lanczos [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" \
    "$output" -loglevel error

  local size=$(du -sh "$output" | cut -f1)
  echo "  ✓ Done → $output ($size)"
}

# === How It Works Strip (3 clips) ===
convert_gif "videos/scene1.mp4"                          "$GIFS_DIR/chaos.gif"        12 460
convert_gif "videos/cyberpunk_haki_shockwave.mp4"        "$GIFS_DIR/activation.gif"   12 460
convert_gif "videos/AI_Engineering_Suite_Never_Guess.mp4" "$GIFS_DIR/never_guess.gif" 12 460

# === Domain Accordion GIFs (one per section) ===
convert_gif "videos/scene 3.mp4"                         "$GIFS_DIR/security.gif"     10 420
convert_gif "videos/rasengan_data_sphere_neon_city.mp4"  "$GIFS_DIR/web3.gif"         10 420
convert_gif "videos/scene4.mp4"                          "$GIFS_DIR/devops.gif"       10 420
convert_gif "videos/anime_cyberpunk_ui_dashboard.mp4"    "$GIFS_DIR/uiux.gif"         10 420

echo ""
echo "All GIFs converted!"
ls -lh "$GIFS_DIR"
