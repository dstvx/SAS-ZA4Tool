from lib.ui.user_interface import OptionType, UserInterface
from lib.utils.initial_setup import initial_setup_menu
from lib.ui.user_interface import create_option, OptionType
from lib.options.options import generate_options_menu
from lib.options.utilities import generate_utilities_menu
from lib.options.global_options import generate_global_menu
from lib.options.profile_options import generate_profile_menu

from lib.utils.config import ConfigManager

if __name__ == '__main__':
    cm = ConfigManager().data
    
    if not cm.get('selected_profile'):
        print("Running initial setup...")
        setup_ui = UserInterface(initial_setup_menu)
        setup_ui.run()
        
        if not ConfigManager().data.get('selected_profile'):
           print("Setup aborted or incomplete. The main menu will load, but features may not function without a profile.")
               

    
    menu = create_option(
        'Main menu', '1', OptionType.SUBMENU,
        children=[
            generate_global_menu(),
            generate_profile_menu(),
            generate_utilities_menu(),
            generate_options_menu()
        ]
    )

    main_ui = UserInterface(menu)
    main_ui.run()