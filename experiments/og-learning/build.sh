#!/usr/bin/env bash
set -euo pipefail
experiment_dir="$(cd "$(dirname "$0")" && pwd)"
docker_cmd=(docker --context "${DOCKER_CONTEXT:-desktop-linux}")
artifacts="$experiment_dir/artifacts"
mkdir -p "$artifacts"
tf_wheel=tensorflow-1.15.5-cp37-cp37m-linux_aarch64.whl
if [[ ! -f "$artifacts/$tf_wheel" ]]; then
  curl --fail --location --silent --show-error \
    "https://media.githubusercontent.com/media/noahzhy/tf-aarch64/75a83c8e83b43834a1de73fa11822967e4634ad3/$tf_wheel" \
    -o "$artifacts/$tf_wheel"
fi
python3 - "$artifacts/$tf_wheel" <<'PY'
import hashlib, pathlib, sys
assert hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest() == '3002e4e405b3c7d6c0453304aa40fd64353ffefa03e5b99ad722816bbc762052'
PY
"${docker_cmd[@]}" build --platform linux/arm64 -t og-learning:tf1 "$experiment_dir"
"${docker_cmd[@]}" run --rm --platform linux/arm64 \
  --mount "type=bind,src=$experiment_dir,dst=/experiment-source,readonly" \
  --mount "type=bind,src=$artifacts,dst=/export" \
  og-learning:tf1 python /experiment-source/collect_artifacts.py /export
cp "$artifacts/manifest/requirements.lock" "$experiment_dir/requirements.lock"
python3 "$experiment_dir/prepare_runtime.py"
"${docker_cmd[@]}" build --platform linux/arm64 -t og-learning:runtime "$artifacts/runtime-context"
"${docker_cmd[@]}" image inspect og-learning:runtime > "$artifacts/runtime-image.json"

run_id="$(date -u +%Y%m%dT%H%M%SZ)"
host_results="$artifacts/host-$run_id"
mkdir -p "$host_results"
for phase in train restore; do
  "${docker_cmd[@]}" run --rm --network none --platform linux/arm64 \
    --mount "type=bind,src=$host_results,dst=/results" \
    og-learning:runtime python /workspace/experiments/og-learning/benchmark.py \
    "$phase" --output /results > "$host_results/$phase.log" 2>&1
done
# Package only after both actual training and restart tests pass.
"${docker_cmd[@]}" run --rm --network none --platform linux/arm64 \
  --mount "type=bind,src=$artifacts,dst=/out" og-learning:runtime \
  mksquashfs / /out/runtime.squashfs -noappend -comp gzip -processors 2 -wildcards \
  -e 'proc/*' 'sys/*' 'dev/*' 'out/*' 'tmp/*' 'root/.cache/*'
python3 - "$artifacts/runtime.squashfs" <<'PY'
import hashlib, pathlib, sys
p = pathlib.Path(sys.argv[1])
p.with_suffix('.squashfs.sha256').write_text(hashlib.sha256(p.read_bytes()).hexdigest() + '  runtime.squashfs\n')
PY
printf 'Host acceptance results: %s\nRuntime: %s/runtime.squashfs\n' "$host_results" "$artifacts"
