#!/bin/bash -e

IMAGE="malchorya"
SCRIPT="$(basename "$0")"

usage() {
    echo "Usage: ./$SCRIPT <command>"
    echo ""
    echo "Commands:"
    echo "  build      Build the Docker image"
    echo "  rebuild    Force rebuild (no cache)"
    echo "  run        Run the game (builds if image missing)"
    echo "  dev        Run the game in Docker with live source mounted"
    echo "  test       Run the test suite inside Docker (headless)"
    echo "  screenshots [ids]  Render every location to tools/shots (in Docker)"
    echo "  run3d      Run the 3D version (GPU=1 to use /dev/dri)"
    echo "  screenshots3d [ids]  Render 3D locations headless to tools/shots3d"
    echo "  sprites    Re-cut player sprite frames from the sheet (in Docker)"
    echo "  shell      Open a shell inside the container"
    echo "  clean      Remove the Docker image"
    echo "  help       Show this message"
}

cmd_build() {
    echo "Building $IMAGE..."
    docker build -t "$IMAGE" .
    echo "Done."
}

cmd_rebuild() {
    echo "Rebuilding $IMAGE (no cache)..."
    docker build --no-cache -t "$IMAGE" .
    echo "Done."
}

cmd_run() {
    if ! docker image inspect "$IMAGE" &>/dev/null; then
        echo "Image not found — building first..."
        cmd_build
    fi
    xhost +local:docker >/dev/null 2>&1 || true
    docker run --rm \
        -e DISPLAY="$DISPLAY" \
        -v /tmp/.X11-unix:/tmp/.X11-unix \
        --ipc=host \
        "$IMAGE"
}

ensure_image() {
    if ! docker image inspect "$IMAGE" &>/dev/null; then
        echo "Image not found — building first..."
        cmd_build
    fi
}

cmd_dev() {
    ensure_image
    xhost +local:docker >/dev/null 2>&1 || true
    docker run --rm \
        -e DISPLAY="$DISPLAY" \
        -v /tmp/.X11-unix:/tmp/.X11-unix \
        -v "$(cd "$(dirname "$0")" && pwd)/malchorya:/app/malchorya" \
        --ipc=host \
        "$IMAGE"
}

cmd_test() {
    cmd_build
    docker run --rm -e PYTHONDONTWRITEBYTECODE=1 "$IMAGE" python3 -m unittest discover -s tests -v
}

cmd_sprites() {
    local root
    root="$(cd "$(dirname "$0")" && pwd)"
    docker run --rm -v "$root:/work" -w /work python:3.10-slim bash -c \
        "pip install -q --no-cache-dir pillow numpy opencv-python-headless >/dev/null 2>&1 && python3 tools/extract_sprites.py malchorya/assets/sprites/player_sheet.png malchorya/assets/sprites/player && chown -R $(id -u):$(id -g) malchorya/assets/sprites/player"
}

cmd_screenshots() {
    cmd_build >/dev/null
    local root
    root="$(cd "$(dirname "$0")" && pwd)"
    mkdir -p "$root/tools/shots"
    docker run --rm -v "$root/tools/shots:/shots" -v "$root/tools:/app/tools" "$IMAGE" \
        python3 tools/screenshots.py /shots "$@"
    docker run --rm -v "$root/tools/shots:/shots" "$IMAGE" chown -R "$(id -u):$(id -g)" /shots
}

cmd_run3d() {
    ensure_image
    xhost +local:docker >/dev/null 2>&1 || true
    local gpu_args=(-e LIBGL_ALWAYS_SOFTWARE=1)
    if [ "${GPU:-0}" = "1" ] && [ -d /dev/dri ]; then
        gpu_args=(--device /dev/dri)
    fi
    docker run --rm \
        -e DISPLAY="$DISPLAY" \
        -v /tmp/.X11-unix:/tmp/.X11-unix \
        "${gpu_args[@]}" \
        --ipc=host \
        "$IMAGE" python3 malchorya/main3d.py
}

cmd_screenshots3d() {
    cmd_build >/dev/null
    local root
    root="$(cd "$(dirname "$0")" && pwd)"
    mkdir -p "$root/tools/shots3d"
    docker run --rm -v "$root/tools/shots3d:/shots" -v "$root/tools:/app/tools" "$IMAGE" \
        python3 tools/screenshots3d.py /shots "$@"
    docker run --rm -v "$root/tools/shots3d:/shots" "$IMAGE" chown -R "$(id -u):$(id -g)" /shots
}

cmd_shell() {
    if ! docker image inspect "$IMAGE" &>/dev/null; then
        echo "Image not found — building first..."
        cmd_build
    fi
    xhost +local:docker >/dev/null 2>&1 || true
    docker run --rm -it \
        -e DISPLAY="$DISPLAY" \
        -v /tmp/.X11-unix:/tmp/.X11-unix \
        --ipc=host \
        "$IMAGE" bash
}

cmd_clean() {
    if docker image inspect "$IMAGE" &>/dev/null; then
        docker rmi "$IMAGE"
        echo "Removed image $IMAGE."
    else
        echo "No image to remove."
    fi
}

case "${1:-help}" in
    build)   cmd_build   ;;
    rebuild) cmd_rebuild ;;
    run)     cmd_run     ;;
    dev)     cmd_dev     ;;
    test)    cmd_test    ;;
    sprites) cmd_sprites ;;
    run3d)   cmd_run3d   ;;
    screenshots3d) shift; cmd_screenshots3d "$@" ;;
    screenshots) shift; cmd_screenshots "$@" ;;
    shell)   cmd_shell   ;;
    clean)   cmd_clean   ;;
    help)    usage       ;;
    *)
        echo "Unknown command: $1"
        echo ""
        usage
        exit 1
        ;;
esac
