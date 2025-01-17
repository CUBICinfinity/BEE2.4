"""The Style Properties tab, for configuring style-specific properties."""
from __future__ import annotations
from tkinter import *
from tkinter import ttk

from typing import Callable, Optional
import operator
import itertools

from srctools import Property
from srctools.logger import get_logger
from packages import Style, StyleVar
from app.SubPane import SubPane
from app import tooltip, TK_ROOT, itemconfig, tk_tools
from localisation import ngettext, gettext
import BEE2_config


LOGGER = get_logger(__name__)

# Special StyleVars that are hardcoded into the BEE2.
# These are effectively attributes of Portal 2 itself, and always work
# in every style.
styleOptions = [
    StyleVar.unstyled(
        id='MultiverseCave',
        name=gettext('Multiverse Cave'),
        default=True,
        desc=gettext('Play the Workshop Cave Johnson lines on map start.'),
    ),

    StyleVar.unstyled(
        id='FixFizzlerBump',
        name=gettext('Prevent Portal Bump (fizzler)'),
        default=False,
        desc=gettext(
            'Add portal bumpers to make it more difficult to portal across '
            'fizzler edges. This can prevent placing portals in tight spaces '
            'near fizzlers, or fizzle portals on activation.'
        ),
    ),

    StyleVar.unstyled(
        id='NoMidVoices',
        name=gettext('Suppress Mid-Chamber Dialogue'),
        default=False,
        desc=gettext('Disable all voicelines other than entry and exit lines.'),
    ),

    StyleVar.unstyled(
        id='UnlockDefault',
        name=gettext('Unlock Default Items'),
        default=False,
        desc=gettext(
            'Allow placing and deleting the mandatory Entry/Exit Doors and '
            'Large Observation Room. Use with caution, this can have weird '
            'results!'
        ),
    ),

    StyleVar.unstyled(
        id='AllowGooMist',
        name=gettext('Allow Adding Goo Mist'),
        default=True,
        desc=gettext(
            'Add mist particles above Toxic Goo in certain styles. This can '
            'increase the entity count significantly with large, complex goo '
            'pits, so disable if needed.'
        ),
    ),

    StyleVar.unstyled(
        id='FunnelAllowSwitchedLights',
        name=gettext('Light Reversible Excursion Funnels'),
        default=True,
        desc=gettext(
            'Funnels emit a small amount of light. However, if multiple funnels '
            'are near each other and can reverse polarity, this can cause '
            'lighting issues. Disable this to prevent that by disabling '
            'lights. Non-reversible Funnels do not have this issue.'
        ),
    ),

    StyleVar.unstyled(
        id='EnableShapeSignageFrame',
        name=gettext('Enable Shape Framing'),
        default=True,
        desc=gettext(
            'After 10 shape-type antlines are used, the signs repeat. With this'
            ' enabled, colored frames will be added to distinguish them.'
        ),
    ),
]

checkbox_all: dict[str, ttk.Checkbutton] = {}
checkbox_chosen: dict[str, ttk.Checkbutton] = {}
checkbox_other: dict[str, ttk.Checkbutton] = {}
tk_vars: dict[str, IntVar] = {}

VAR_LIST: list[StyleVar] = []
STYLES: dict[str, Style] = {}

window: Optional[SubPane] = None

UI = {}
# Callback triggered whenever we reload vars. This is used to update items
# to show/hide the defaults.
_load_cback: Optional[Callable[[], None]] = None


def mandatory_unlocked() -> bool:
    """Return whether mandatory items are unlocked currently."""
    try:
        return tk_vars['UnlockDefault'].get() != 0
    except KeyError:  # Not loaded yet
        return False


@BEE2_config.OPTION_SAVE('StyleVar')
def save_handler() -> Property:
    """Save variables to configs."""
    props = Property('', [])
    for var_id, var in sorted(tk_vars.items()):
        props[var_id] = str(int(var.get()))
    return props


@BEE2_config.OPTION_LOAD('StyleVar')
def load_handler(props: Property) -> None:
    """Load variables from configs."""
    for prop in props:
        try:
            tk_vars[prop.real_name].set(prop.value)
        except KeyError:
            LOGGER.warning('No stylevar "{}", skipping.', prop.real_name)
    if _load_cback is not None:
        _load_cback()


def export_data(chosen_style: Style) -> dict[str, bool]:
    """Construct a dict containing the current stylevar settings."""
    return {
        var.id: (tk_vars[var.id].get() == 1)
        for var in
        itertools.chain(VAR_LIST, styleOptions)
        if var.applies_to_style(chosen_style)
    }


def make_desc(var: StyleVar) -> str:
    """Generate the description text for a StyleVar.

    This adds 'Default: on/off', and which styles it's used in.
    """
    if var.desc:
        desc = [var.desc, '']
    else:
        desc = []

    # i18n: StyleVar default value.
    desc.append(gettext('Default: On') if var.default else gettext('Default: Off'))

    if var.styles is None:
        # i18n: StyleVar which is totally unstyled.
        desc.append(gettext('Styles: Unstyled'))
    else:
        app_styles = [
            style
            for style in
            STYLES.values()
            if var.applies_to_style(style)
        ]

        if len(app_styles) == len(STYLES):
            # i18n: StyleVar which matches all styles.
            desc.append(gettext('Styles: All'))
        else:
            style_list = sorted(
                style.selitem_data.short_name
                for style in
                app_styles
            )
            desc.append(ngettext(
                # i18n: The styles a StyleVar is allowed for.
                'Style: {}', 'Styles: {}', len(style_list),
            ).format(', '.join(style_list)))

    return '\n'.join(desc)


def refresh(selected_style: Style) -> None:
    """Move the stylevars to the correct position.

    This depends on which apply to the current style.
    """
    en_row = 0
    dis_row = 0
    for var in VAR_LIST:
        if var.applies_to_all():
            continue  # Always visible!
        if var.applies_to_style(selected_style):
            checkbox_chosen[var.id].grid(
                row=en_row,
                sticky="W",
                padx=3,
            )
            checkbox_other[var.id].grid_remove()
            en_row += 1
        else:
            checkbox_chosen[var.id].grid_remove()
            checkbox_other[var.id].grid(
                row=dis_row,
                sticky="W",
                padx=3,
            )
            dis_row += 1
    if en_row == 0:
        UI['stylevar_chosen_none'].grid(sticky='EW')
    else:
        UI['stylevar_chosen_none'].grid_remove()

    if dis_row == 0:
        UI['stylevar_other_none'].grid(sticky='EW')
    else:
        UI['stylevar_other_none'].grid_remove()


def make_pane(tool_frame: Frame, menu_bar: Menu, update_item_vis: Callable[[], None]) -> None:
    """Create the styleVar pane.

    update_item_vis is the callback fired whenever change defaults changes.
    """
    global window, _load_cback
    _load_cback = update_item_vis

    window = SubPane(
        TK_ROOT,
        title=gettext('Style/Item Properties'),
        name='style',
        menu_bar=menu_bar,
        resize_y=True,
        tool_frame=tool_frame,
        tool_img='icons/win_stylevar',
        tool_col=3,
    )

    UI['nbook'] = nbook = ttk.Notebook(window)

    nbook.grid(row=0, column=0, sticky=NSEW)
    window.rowconfigure(0, weight=1)
    window.columnconfigure(0, weight=1)
    nbook.enable_traversal()

    stylevar_frame = ttk.Frame(nbook)
    stylevar_frame.rowconfigure(0, weight=1)
    stylevar_frame.columnconfigure(0, weight=1)
    nbook.add(stylevar_frame, text=gettext('Styles'))

    canvas = Canvas(stylevar_frame, highlightthickness=0)
    # need to use a canvas to allow scrolling
    canvas.grid(sticky='NSEW')
    window.rowconfigure(0, weight=1)

    UI['style_scroll'] = ttk.Scrollbar(
        stylevar_frame,
        orient=VERTICAL,
        command=canvas.yview,
        )
    UI['style_scroll'].grid(column=1, row=0, rowspan=2, sticky="NS")
    canvas['yscrollcommand'] = UI['style_scroll'].set

    tk_tools.add_mousewheel(canvas, stylevar_frame)

    canvas_frame = ttk.Frame(canvas)

    frame_all = ttk.Labelframe(canvas_frame, text=gettext("All:"))
    frame_all.grid(row=0, sticky='EW')

    frm_chosen = ttk.Labelframe(canvas_frame, text=gettext("Selected Style:"))
    frm_chosen.grid(row=1, sticky='EW')

    ttk.Separator(
        canvas_frame,
        orient=HORIZONTAL,
        ).grid(row=2, sticky='EW', pady=(10, 5))

    frm_other = ttk.Labelframe(canvas_frame, text=gettext("Other Styles:"))
    frm_other.grid(row=3, sticky='EW')

    UI['stylevar_chosen_none'] = ttk.Label(
        frm_chosen,
        text=gettext('No Options!'),
        font='TkMenuFont',
        justify='center',
        )
    UI['stylevar_other_none'] = ttk.Label(
        frm_other,
        text=gettext('None!'),
        font='TkMenuFont',
        justify='center',
        )

    VAR_LIST[:] = sorted(StyleVar.all(), key=operator.attrgetter('id'))

    all_pos = 0
    for all_pos, var in enumerate(styleOptions):
        # Add the special stylevars which apply to all styles
        tk_vars[var.id] = int_var = IntVar(value=var.default)
        checkbox_all[var.id] = ttk.Checkbutton(
            frame_all,
            variable=int_var,
            text=var.name,
        )
        checkbox_all[var.id].grid(row=all_pos, column=0, sticky="W", padx=3)

        # Special case - this needs to refresh the filter when swapping,
        # so the items disappear or reappear.
        if var.id == 'UnlockDefault':
            checkbox_all[var.id]['command'] = lambda: update_item_vis()

        tooltip.add_tooltip(checkbox_all[var.id], make_desc(var))

    for var in VAR_LIST:
        tk_vars[var.id] = IntVar(value=var.enabled)
        args = {
            'variable': tk_vars[var.id],
            'text': var.name,
        }
        desc = make_desc(var)
        if var.applies_to_all():
            # Available in all styles - put with the hardcoded variables.
            all_pos += 1

            checkbox_all[var.id] = check = ttk.Checkbutton(frame_all, **args)
            check.grid(row=all_pos, column=0, sticky="W", padx=3)
            tooltip.add_tooltip(check, desc)
        else:
            # Swap between checkboxes depending on style.
            checkbox_chosen[var.id] = ttk.Checkbutton(frm_chosen, **args)
            checkbox_other[var.id] = ttk.Checkbutton(frm_other, **args)

            tooltip.add_tooltip(checkbox_chosen[var.id], desc)
            tooltip.add_tooltip(checkbox_other[var.id], desc)

    canvas.create_window(0, 0, window=canvas_frame, anchor="nw")
    canvas.update_idletasks()
    canvas.config(
        scrollregion=canvas.bbox(ALL),
        width=canvas_frame.winfo_reqwidth(),
    )

    if tk_tools.USE_SIZEGRIP:
        ttk.Sizegrip(
            window,
            cursor=tk_tools.Cursors.STRETCH_VERT,
        ).grid(row=1, column=0)

    canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox(ALL)))

    item_config_frame = ttk.Frame(nbook)
    nbook.add(item_config_frame, text=gettext('Items'))
    itemconfig.make_pane(item_config_frame)
