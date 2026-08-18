import sys

from lib.menu import run_app
from lib.ui.ui import clear_screen
from lib.utils.logger import logger, setup_logger


def main() -> None:
    setup_logger()
    logger.info("SAS:ZA4Tool launched.")

    from lib.config import config
    from lib.exceptions import CancelError

    if config.setup_done:
        errors = config.validate()
        critical_errors = [e for e in errors if e.startswith("Critical:")]
        if critical_errors:
            print("\n[WARNING] Configuration validation failed:")
            for err in errors:
                print(f"  - {err}")
            print("\nResetting setup state. Starting setup wizard...")
            try:
                input("Press Enter to run Setup...")
            except KeyboardInterrupt:
                sys.exit(0)
            config.update(setup_done=False)

    if not config.setup_done:
        try:
            from lib.utils.setup import run_setup

            run_setup()
        except (KeyboardInterrupt, CancelError):
            clear_screen()
            logger.info("SAS:ZA4Tool setup terminated by user.")
            sys.exit(0)

    if config.check_updates:
        try:
            from lib.utils.updates import VERSION, check_for_updates

            has_update, latest = check_for_updates()
            if has_update:
                print(
                    f"\n[INFO] A new version of SAS:ZA4Tool is available! (Current: {VERSION}, Latest: {latest})"
                )
                try:
                    input("Press Enter to continue...")
                except KeyboardInterrupt:
                    pass
        except (OSError, ValueError) as e:
            logger.error(f"Update check failed: {e}")

    try:
        run_app()
    except (KeyboardInterrupt, CancelError):
        clear_screen()
        logger.info("SAS:ZA4Tool terminated by user.")
        sys.exit(0)
    except Exception as e:  # noqa: BLE001
        logger.critical(f"Unhandled crash: {e}", exc_info=True)
        print(f"\n[CRITICAL ERROR] The application crashed: {e}")
        print(
            "If logging is enabled in settings, details have been written to sas_za4tool.log."
        )
        try:
            input("\nPress Enter to exit...")
        except KeyboardInterrupt:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
