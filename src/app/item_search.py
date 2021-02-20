from tkinter import ttk
import tkinter as tk

from collections import defaultdict

from app import UI

from marisa_trie import Trie
from typing import Dict, Optional, Set, Callable, Tuple
import srctools.logger


LOGGER = srctools.logger.get_logger(__name__)
database = Trie()
word_to_ids: Dict[str,  Set[Tuple[str, int]]] = defaultdict(set)
_type_cback: Optional[Callable[[], None]] = None


def init(frm: tk.Frame, refresh_cback: Callable[[Optional[Set[Tuple[str, int]]]], None]) -> None:
    """Initialise the UI objects.

    The callback is triggered whenever the UI changes, passing along
    the visible items.
    """
    global _type_cback

    def on_type(*args):
        """Re-search whenever text is typed."""
        text = search_var.get()
        words = text.split()
        if not words:
            refresh_cback(None)
            return

        found: Set[Tuple[str, int]] = set()
        for word in words:
            for name in database.iterkeys(word):
                found |= word_to_ids[name]
        # Calling the callback deselects us, so save and restore.
        selected = searchbar.selection_present()
        if selected:
            start = searchbar.index('sel.first')
            end = searchbar.index('sel.last')
        else:
            start = end = 0

        refresh_cback(found)

        if selected:
            searchbar.selection_range(start, end)

    frm.columnconfigure(1, weight=1)

    ttk.Label(
        frm,
        text=_('Search:'),
    ).grid(row=0, column=0)

    search_var = tk.StringVar()
    search_var.trace_add('write', on_type)

    searchbar = tk.Entry(frm, textvariable=search_var)
    searchbar.grid(row=0, column=1, sticky='EW')

    _type_cback = on_type


def rebuild_database() -> None:
    """Rebuild the search database."""
    global database
    LOGGER.info('Updating search database...')
    # Clear and reset.
    word_to_ids.clear()

    for item in UI.item_list.values():
        for subtype_ind in item.visual_subtypes:
            for tag in item.get_tags(subtype_ind):
                for word in tag.split():
                    word_to_ids[word.casefold()].add((item.id, subtype_ind))
    database = Trie(word_to_ids.keys())
    LOGGER.debug('Tags: {}', database.keys())
    _type_cback()
