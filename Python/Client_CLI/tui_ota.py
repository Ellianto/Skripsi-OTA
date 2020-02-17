import internal_handlers

def run():
    while True:
        try:
            main_input = internal_handlers.user_io_handlers.handle_main_menu()

            if main_input is None:  # Quit Option
                break
            elif main_input == 1:  # Firmware Update Option
                internal_handlers.menu_logic_handlers.update_menu_logic()
            elif main_input == 2:  # Register Device Option
                internal_handlers.menu_logic_handlers.register_menu_logic()
            elif main_input == 3:  # Delete option
                internal_handlers.menu_logic_handlers.delete_menu_logic()

        except Exception as err:
            internal_handlers.error_handlers.handle_misinput(err)

    print('Thank you!')


# CLI Entry point
if __name__ == '__main__':
    run()
