import constants

from internal_handlers.error_handlers import handle_misinput
from internal_handlers.menu_logic_handlers import update_menu_logic, register_menu_logic, delete_menu_logic
from internal_handlers import user_io_handlers

def app():
    while True:
        try:
            main_input = user_io_handlers.handle_main_menu()

            if main_input is None:  # Quit Option
                break
            elif main_input == 1:  # Firmware Update Option
                update_menu_logic()
            elif main_input == 2:  # Register Device Option
                register_menu_logic()
            elif main_input == 3:  # Delete option
                delete_menu_logic()

        except (ValueError, IndexError) as err:
            handle_misinput(err)

    print('Thank you!')


# CLI Entry point
if __name__ == '__main__':
    app()
