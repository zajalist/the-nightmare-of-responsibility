#!/usr/bin/env bash
# Continuous devlog screen recording of the desktop (the Unreal editor), in 30-minute MP4 segments.
# The editor window can't be grabbed directly (DirectX comes out black), so this records the whole desktop.
#   bash Tools/Capture/record_editor.sh          # runs until killed (Ctrl+C or: taskkill /IM ffmpeg.exe)
# FPS defaults to 5, which plays back as a timelapse; set FPS=30 for real-time footage of a specific moment.
OUT="${OUT:-P:/FoA-Devlog/recordings}"
FPS="${FPS:-5}"
mkdir -p "$OUT"
exec ffmpeg -hide_banner -loglevel warning -f gdigrab -framerate "$FPS" -draw_mouse 1 -i desktop \
  -vf "scale=1920:-2" -c:v libx264 -preset ultrafast -crf 26 -pix_fmt yuv420p \
  -f segment -segment_time 1800 -reset_timestamps 1 -strftime 1 \
  "$OUT/editor_%Y%m%d_%H%M%S.mp4"
