"""The package containg all UI code."""
import tkinter as tk
from types import TracebackType
from typing import Type
import utils
import trio  # Import first, so it monkeypatch traceback before us.

# We must always have one Tk object, and it needs to be constructed
# before most of TKinter will function. So doing it here does it first.
TK_ROOT = tk.Tk()
TK_ROOT.withdraw()  # Hide the window until everything is loaded.


def _run_main_loop(*args, **kwargs) -> None:
    """Allow determining if this is running."""
    global _main_loop_running
    _main_loop_running = True
    _orig_mainloop(*args, **kwargs)


_main_loop_running = False
_orig_mainloop = TK_ROOT.mainloop
TK_ROOT.mainloop = _run_main_loop
del _run_main_loop


# noinspection PyBroadException
def tk_error(
    exc_type: Type[BaseException],
    exc_value: BaseException,
    exc_tb: TracebackType,
) -> None:
    """Log TK errors."""
    # The exception is caught inside the TK code.
    # We don't care about that, so try and move the traceback up
    # one level.
    import logging
    if exc_tb.tb_next:
        exc_tb = exc_tb.tb_next

    try:
        on_error(exc_type, exc_value, exc_tb)
    except Exception:
        pass

    logger = logging.getLogger('BEE2')
    logger.error(
        msg='Uncaught Tk Exception:',
        exc_info=(exc_type, exc_value, exc_tb),
    )

    try:
        import BEE2
        BEE2.APP_NURSERY.cancel_scope.cancel()
    except Exception:
        pass

TK_ROOT.report_callback_exception = tk_error


# noinspection PyBroadException
def on_error(
    exc_type: Type[BaseException],
    exc_value: BaseException,
    exc_tb: TracebackType,
) -> None:
    """Run when the application crashes. Display to the user, log it, and quit."""
    # We don't want this to fail, so import everything here, and wrap in
    # except Exception.
    import traceback
    err = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))

    # Grab and release the grab so nothing else can block the error message.
    try:
        TK_ROOT.grab_set_global()
        TK_ROOT.grab_release()

        # Append traceback to the clipboard.
        TK_ROOT.clipboard_append(err)
    except Exception:
        pass

    if not issubclass(exc_type, Exception):
        # It's subclassing BaseException (KeyboardInterrupt, SystemExit),
        # so ignore the error.
        return

    # Put it onscreen.
    try:
        from tkinter import messagebox
        from localisation import gettext
        messagebox.showinfo(
            title=gettext('BEEMOD {} Error!').format(utils.BEE_VERSION),
            message=gettext(
                'An error occurred: \n{}\n\n'
                'This has been copied to the clipboard.'
            ).format(err),
            icon=messagebox.ERROR,
        )
    except Exception:
        pass

    try:
        from BEE2_config import GEN_OPTS
        # Try to turn on the logging window for next time..
        GEN_OPTS.load()
        GEN_OPTS['Debug']['show_log_win'] = '1'
        GEN_OPTS['Debug']['window_log_level'] = 'DEBUG'
        GEN_OPTS.save()
    except Exception:
        # Ignore failures...
        pass

# Various configuration booleans.
PLAY_SOUND = tk.BooleanVar(value=True, name='OPT_play_sounds')
KEEP_WIN_INSIDE = tk.BooleanVar(value=True, name='OPT_keep_win_inside')
FORCE_LOAD_ONTOP = tk.BooleanVar(value=True, name='OPT_force_load_ontop')
SHOW_LOG_WIN = tk.BooleanVar(value=False, name='OPT_show_log_window')
LAUNCH_AFTER_EXPORT = tk.BooleanVar(value=True, name='OPT_launch_after_export')
PRESERVE_RESOURCES = tk.BooleanVar(value=False, name='OPT_preserve_bee2_resource_dir')
DEV_MODE = tk.BooleanVar(value=utils.DEV_MODE, name='OPT_development_mode')
