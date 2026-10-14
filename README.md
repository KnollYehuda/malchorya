# malchorya
Malchorya rpg game — 2D (pygame) and 3D (Panda3D) front ends over the same game logic.
Everything runs in Docker; nothing is installed on the host.

    ./build.sh run3d     # 3D version   (GPU=1 ./build.sh run3d to use /dev/dri)
    ./build.sh run       # 2D version
    ./build.sh test      # tests, headless
    ./build.sh screenshots3d [location_ids]   # headless renders -> tools/shots3d

Audio is synthesized in code (music, ambience, effects) and baked into the Docker image;
`./build.sh run3d` forwards your PulseAudio socket so it plays on the host speakers.

3D controls: WASD move, E talk / pick up, F attack, H potion, Z rest, I/C/Q/L inventory/status/quests/look,
Enter opens a command line (buy, sell, equip, wait ...), hold right mouse button and drag to rotate/tilt the camera (arrows also work), wheel zooms, M opens the world map (a minimap is always shown), Esc quits.
