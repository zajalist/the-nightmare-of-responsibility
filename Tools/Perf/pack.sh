#!/usr/bin/env bash
# Package FoA from a mirror of P:\FoA (coordinator's pack_dev.sh, perf lane copy). The cooker must never hold the shared
# editor's Content files open (that silently breaks the editor's saves) or answer Hayba / Python remote execution.
#   bash Tools/Perf/pack.sh [Shipping|Development]     (default Shipping)
# Output: P:/FoA-Builds/<Config>_<stamp>/ plus <Config>_<stamp>.zip next to it; log in P:/FoA/Saved/Perf/pack/.
# Shipping: -nodebuginfo keeps FoA.pdb out of the build (329 MB in the first Development build).
set -u
export MSYS_NO_PATHCONV=1  # Git Bash would rewrite robocopy /MIR and /XD into paths
CONFIG="${1:-Shipping}"
SRC="P:/FoA"
MIR="P:/FoA-PackMirror"
STAMP=$(date +%Y%m%d_%H%M)
OUT="P:/FoA-Builds/${CONFIG}_${STAMP}"
LOGDIR="P:/FoA/Saved/Perf/pack"
LOG="$LOGDIR/uat_${CONFIG}_${STAMP}.log"
mkdir -p "$MIR" "$OUT" "$LOGDIR"
for sub in Content Config Plugins Binaries Build; do  # Binaries: UAT reads Win64/FoAEditor.target; Build: PSO caches
  # Hayba stays out of the mirror: an editor-only plugin whose TCP server must exist once, in the shared editor.
  robocopy "$SRC/$sub" "$MIR/$sub" /MIR /R:2 /W:1 /NP /NFL /NDL /NJH /NJS /XD Intermediate Saved DerivedDataCache .git HaybaMCPToolkit >/dev/null
done
cp -f "$SRC/FoA.uproject" "$MIR/FoA.uproject"
[ -e "$MIR/DerivedDataCache" ] || cmd /c mklink /J "P:\\FoA-PackMirror\\DerivedDataCache" "P:\\FoA\\DerivedDataCache" >/dev/null
# The cooker loads editor plugins: keep Python remote execution off so ue_remote.py only ever finds the shared editor.
grep -q "PythonScriptPluginSettings" "$MIR/Config/DefaultEngine.ini" || printf '\n[/Script/PythonScriptPlugin.PythonScriptPluginSettings]\nbRemoteExecution=False\n' >> "$MIR/Config/DefaultEngine.ini"
EXTRA=""
[ "$CONFIG" = "Shipping" ] && EXTRA="-nodebuginfo"
# Bundled PSO cache: the cook must write stable shader keys (*.shk, for recording) and turns
# Build/Windows/PipelineCaches/*_FoA_PCD3D_SM6.spc into the packaged FoA_PCD3D_SM6.stable.upipelinecache. Mirror only:
# in the shared editor this switch could change shader DDC keys and force a full shader recompile on its next start.
printf '\n[DevOptions.Shaders]\nNeedsShaderStableKeys=true\n' >> "$MIR/Config/DefaultEngine.ini"
# Perf builds (Development): F7 also opens the console. This machine's fr-CA layout makes backtick a dead key, so the
# default Tilde never reaches UE and Tools/Perf/cooked_driver.py could not type commands. Mirror only (robocopy above
# restores the original on every run), never P:\FoA, never Shipping.
[ "$CONFIG" = "Development" ] && printf '\n[/Script/Engine.InputSettings]\n+ConsoleKeys=F7\n' >> "$MIR/Config/DefaultInput.ini"
echo "mirror ready $(date +%T); packaging $CONFIG to $OUT; log $LOG"
"C:/Program Files/Epic Games/UE_5.9/Engine/Build/BatchFiles/RunUAT.bat" BuildCookRun \
  -project="P:/FoA-PackMirror/FoA.uproject" -noP4 -platform=Win64 -clientconfig="$CONFIG" \
  -build -cook -stage -pak -iostore -compressed -archive -archivedirectory="$OUT" $EXTRA \
  -unattended -utf8output -nocompileeditor > "$LOG" 2>&1
code=$?
echo "UAT exit $code at $(date +%T)"
grep -E "BUILD SUCCESSFUL|BUILD FAILED|Error:|error :|AutomationTool exiting" "$LOG" | tail -15
if [ $code -eq 0 ] && [ "$CONFIG" = "Shipping" ]; then
  python "$SRC/Tools/Perf/zip_build.py" "$OUT"  # the submission's zip: deflate, like Explorer's (tar -a stored it raw)
fi
du -sh "$OUT" 2>/dev/null
