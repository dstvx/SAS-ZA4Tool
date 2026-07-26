import sys
from lib.menu import run_app
from lib.utils.logger import setup_logger, logger


def main() -> None:
    setup_logger()
    logger.info("SAS:ZA4Tool launched.")

    from lib.config import config
    from lib.exceptions import CancelError

    if not config.setup_done:
        try:
            from lib.utils.setup import run_setup
            run_setup()
        except (KeyboardInterrupt, CancelError):
            import subprocess
            subprocess.run("cls", shell=True)
            logger.info("SAS:ZA4Tool setup terminated by user.")
            sys.exit(0)

    if config.check_updates:
        try:
            from lib.utils.updates import check_for_updates, VERSION
            has_update, latest = check_for_updates()
            if has_update:
                print(f"\n[INFO] A new version of SAS:ZA4Tool is available! (Current: {VERSION}, Latest: {latest})")
                try:
                    input("Press Enter to continue...")
                except KeyboardInterrupt:
                    pass
        except Exception as e:
            logger.error(f"Update check failed: {e}")

    try:
        run_app()
    except (KeyboardInterrupt, CancelError):
        import subprocess
        subprocess.run("cls", shell=True)
        logger.info("SAS:ZA4Tool terminated by user.")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Unhandled crash: {e}", exc_info=True)
        print(f"\n[CRITICAL ERROR] The application crashed: {e}")
        print("If logging is enabled in settings, details have been written to sas_za4tool.log.")
        try:
            input("\nPress Enter to exit...")
        except KeyboardInterrupt:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()