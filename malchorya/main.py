from core.world import create_world
from core.state import create_initial_state
from core.enums import WindDirection
from logic.handle_command import handle_command
from ui.app import App

def on_command(state, raw: str):
    return handle_command(state, raw)

def main() -> None:
    world = create_world()
    state = create_initial_state(world)
    App(state=state, on_command=on_command).run()


if __name__ == "__main__":
    main()
