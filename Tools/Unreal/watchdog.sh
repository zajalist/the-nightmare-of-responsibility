#!/usr/bin/env bash
# Coordinator's stall watchdog for editor A, armed from launch (startup stalls count too). Reads FoA.log only.
# Stall = no new log line other than Hayba TCP / UDP noise for STALL_S. Then: kill ShaderCompileWorkers that used
# no CPU over 60 s (they starved at 0 CPU in the 22:05 and 00:55 stalls), print an alert, exit; the coordinator
# restarts it after every alert.
LOG="P:/FoA/Saved/Logs/FoA.log"
STALL_S="${STALL_S:-240}"
last=""; since=$(date +%s)
latest() { grep -av "LogHaybaMCPTCP\|LogUdpMessaging" "$LOG" 2>/dev/null | tail -1 | cut -c1-30; }
scw_cpu() { powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='ShaderCompileWorker.exe'\" | ForEach-Object { '{0} {1}' -f \$_.ProcessId, [int](((\$_.KernelModeTime + \$_.UserModeTime)/1e7)) }"; }
while true; do
  if ! tasklist //FI "IMAGENAME eq UnrealEditor.exe" | grep -q UnrealEditor; then echo "ALERT no editor running $(date +%T)"; exit 0; fi
  cur=$(latest)
  if [ "$cur" != "$last" ]; then last=$cur; since=$(date +%s); fi
  if [ $(( $(date +%s) - since )) -gt "$STALL_S" ]; then
    a=$(scw_cpu); sleep 60; b=$(scw_cpu); killed=""
    while read -r pid cpu; do
      [ -z "$pid" ] && continue
      prev=$(echo "$a" | awk -v p="$pid" '$1==p {print $2}')
      if [ -n "$prev" ] && [ "$cpu" = "$prev" ]; then taskkill //PID "$pid" //F >/dev/null 2>&1 && killed="$killed $pid"; fi
    done <<< "$b"
    echo "ALERT editor A log quiet $(( $(date +%s) - since ))s at $(date +%T); killed idle SCWs:${killed:- none}"
    grep -av "LogHaybaMCPTCP\|LogUdpMessaging\|lease_" "$LOG" | tail -6 | cut -c1-200
    exit 0
  fi
  sleep 20
done
