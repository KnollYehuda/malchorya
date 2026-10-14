from core.world import create_world
from core.state import create_initial_state
from logic.handle_command import handle_command
from ui3d.app3d import Game3D


def main() -> None:
    state = create_initial_state(create_world())
    Game3D(state=state, on_command=handle_command).run()


if __name__ == "__main__":
    main()
