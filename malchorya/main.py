from core.world import create_world
from core.state import create_initial_state
from logic.commands import handle_command


def main() -> None:
    world = create_world()
    state = create_initial_state(world)

    print("Welcome to Malchorya.")
    while True:
        raw = input("> ").strip()
        if not raw:
            continue
        if raw.lower() in {"quit", "exit"}:
            print("Bye.")
            return

        out = handle_command(state, raw)
        print(out)
        print()


if __name__ == "__main__":
    main()
