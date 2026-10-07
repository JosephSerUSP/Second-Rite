"""The PE Day 1 field menu, built on the original's structure (manual pp.
10-13 and in-game captures; see docs/menu-mechanics.md).

Triangle-equivalent (B here) opens it over the live room. A title bar carries
the help text for the focused entry and the play-time clock; an icon column on
the left picks the page; the status screen is the default view; Aya's HP and
PE sit at the bottom right. Every number shown is one the game actually uses.

build_chapter.py passes its scene helpers in through `Menu(h)` so this module
has no import cycle with the generator run as __main__.
"""

COLUMN = ["Item", "PE", "Weapon", "Armor", "BP"]
PAGE_UI = [21, 23, 22, 24, 25]          # page state for each column entry
OPEN = "sceneState.ui >= 20 and sceneState.ui <= 25"
PLAY = "(variables.playSeconds or 0)"
CLOCK = ("{floor(%(t)s / 3600)}:{floor(%(t)s / 60) %% 60 < 10 and '0' or ''}{floor(%(t)s / 60) %% 60}"
         ":{floor(%(t)s) %% 60 < 10 and '0' or ''}{floor(%(t)s) %% 60}") % {"t": PLAY}
ARMORS = [("n_vest", "N Vest", 2), ("n_protector", "N Protector", 6)]
# Slots in use: every carried thing takes one, the Ammo Crate one in all,
# the worn armor included (the engine moves worn armor out of the inventory).
USED = ("(session.items.m84f + session.items.club + session.items.n_vest + session.items.n_protector"
        " + session.items.medicine + session.items.rehearse_key + (session.items.handgun_ammo > 0 and 1 or 0)"
        " + (sceneState.mArmor ~= '' and 1 or 0))")
N = "\n"


def chain(pairs, default):
    """Lua conditional chain without hand-counted parentheses."""
    expr = default
    for cond, value in reversed(pairs):
        expr = "(%s and %s or %s)" % (cond, value, expr)
    return expr


def lit(text):
    return "'" + text.replace("'", "\\'") + "'"


def fx(dx):
    """x of a window inside the 40-unit menu frame, centred on any surface."""
    return "(surface.width - 40) / 2 - surface.originX + %g" % dx


class Menu:
    def __init__(self, h):
        self.h = h
        self.weapon_name = "(%s == 'baton' and 'Club' or 'M84F')" % h.WEAPON
        self.armor_name = chain([("sceneState.mArmor == '%s'" % i, lit(n)) for i, n, _ in ARMORS], "'--'")

    # --- state ----------------------------------------------------------------
    def snapshot(self):
        h = self.h
        return [{"cmd": "FOR_EACH", "scope": "party", "as": "aya", "do": [
            h.setv(mHp="aya.hp", mMax="aya.maxHp", mPe="aya.res.pe", mLv="aya.level",
                   mNext="aya.progress.toNext", mOff="aya.stat.offense", mDef="aya.stat.defense",
                   mPen="aya.stat.penergy", mSrec="aya.stat.srecover", mAct="aya.stat.act",
                   mCapLv="aya.stat.cap", mCap="9 + aya.stat.cap", mArmor="aya.equip.armor")]},
                h.setv(mUsed=USED)]

    def initial(self):
        return dict(mcol=0, mi=1, wi=0, ai=0, bi=0, menuNote="''", mHp=0, mMax=1, mPe=0, mLv=1, mNext=0,
                    mOff=1, mDef=1, mPen=1, mSrec=1, mAct=1, mCapLv=1, mCap=10, mUsed=0, mArmor="''")

    def issue_kit(self):
        """Aya's carried kit at the start: the M84F, the Club and the N Vest she
        wears (units have no starting-equipment field, so the first room she
        enters issues it once)."""
        return self.h.iff("flag:kit_issued", [], [
            {"cmd": "SET_FLAG", "flag": "kit_issued", "value": True},
            {"cmd": "CHANGE_ITEM", "item": "m84f", "count": 1},
            {"cmd": "CHANGE_ITEM", "item": "club", "count": 1},
            {"cmd": "CHANGE_ITEM", "item": "n_vest", "count": 1},
            {"cmd": "EQUIP_ITEM", "slot": 2, "target": 1, "itemIndex": 2}])

    def room_for(self, item, then, full_text="No room. Item Capacity is full."):
        """Wrap a pickup: refused when every slot is taken (rounds join the
        Ammo Crate's slot; story flags take none)."""
        h = self.h
        if item is None:
            return then
        needs_slot = "true" if item != "handgun_ammo" else "session.items.handgun_ammo == 0"
        return self.snapshot() + [h.iff("%s and sceneState.mUsed >= sceneState.mCap" % needs_slot,
                                        [h.message(full_text, ui=9)], then)]

    # --- input -----------------------------------------------------------------
    def open(self):
        return self.snapshot() + [self.h.setv(ui=20, mcol=0, menuNote="''")]

    def cancel(self):
        h = self.h
        return h.iff("sceneState.ui == 20", [h.setv(ui=0)], [h.setv(ui=20, menuNote="''")])

    def move(self, step):
        h = self.h
        up = step < 0
        wrap = lambda var, n: h.setv(**{var: "(sceneState.%s + %d) %% %d" % (var, n - 1 if up else 1, n), "menuNote": "''"})
        return [
            h.iff("sceneState.ui == 20", [wrap("mcol", len(COLUMN))]),
            h.iff("sceneState.ui == 21", [h.setv(
                mi="max(1, min(session.itemCount, sceneState.mi %s 1))" % ("-" if up else "+"), menuNote="''")]),
            h.iff("sceneState.ui == 22", [wrap("wi", 2)]),
            h.iff("sceneState.ui == 24", [wrap("ai", len(ARMORS))]),
            h.iff("sceneState.ui == 25", [wrap("bi", 2)]),
        ]

    def select(self):
        h = self.h
        note = lambda text: h.setv(menuNote=lit(text))
        enter = [h.iff("sceneState.mcol == %d" % k, [h.setv(ui=PAGE_UI[k], mi=1, ai=0, bi=0, menuNote="''",
                                                          wi="%s == 'baton' and 1 or 0" % h.WEAPON)])
                 for k in range(len(COLUMN))]
        use_item = [{"cmd": "USE_ITEM", "itemIndex": "sceneState.mi", "target": 1}] + self.snapshot() + [
            h.setv(menuNote="sceneState.lastItemResult and (sceneState.lastItemResult.success and "
                            "('Used ' .. sceneState.lastItemResult.itemName .. '.') or sceneState.popupText) or ''"),
            h.setv(mi="max(1, min(session.itemCount, sceneState.mi))")]
        equip_weapon = [h.iff("sceneState.wi == 0",
                              [{"cmd": "SET_GAME_VARIABLE", "name": "weapon", "value": "'handgun'"}, note("Equipped the M84F.")],
                              [{"cmd": "SET_GAME_VARIABLE", "name": "weapon", "value": "'baton'"}, note("Equipped the Club.")])]
        equip_armor = []
        for k, (item, name, _) in enumerate(ARMORS):
            equip_armor.append(h.iff("sceneState.ai == %d" % k, [
                h.iff("sceneState.mArmor == '%s'" % item, [note("Already wearing the %s." % name)], [
                    h.iff("session.items.%s > 0" % item,
                          [{"cmd": "EQUIP_ITEM", "slot": 2, "target": 1, "itemIndex": 2}] + self.snapshot()
                          + [note("Now wearing the %s." % name)],
                          [note("Aya does not have the %s." % name)])])]))
        heal_pe = [h.iff("sceneState.mPe >= 30", [
            h.iff("sceneState.mHp >= sceneState.mMax", [note("HP is already full.")], [
                {"cmd": "FOR_EACH", "scope": "party", "as": "aya", "do": [
                    {"cmd": "CHANGE_RESOURCE", "target": "aya", "resource": "pe", "amount": -30},
                    {"cmd": "HEAL", "target": "aya", "amount": 30}]}] + self.snapshot() + [note("Heal 1. HP restored.")])],
            [note("Not enough PE.")])]
        spend = []
        for k, (param, label) in enumerate([("act", "Active Time"), ("cap", "Item Capacity")]):
            spend.append(h.iff("sceneState.bi == %d" % k, [
                {"cmd": "SET_GAME_VARIABLE", "name": "bp", "value": "(variables.bp or 0) - 100"},
                {"cmd": "FOR_EACH", "scope": "party", "as": "aya", "do": [
                    {"cmd": "ADD_PARAM", "target": "aya", "param": param, "amount": 1}]}] + self.snapshot()
                + [note("%s rose by one level." % label)]))
        bp = [h.iff("(variables.bp or 0) >= 100", spend, [note("100 BP are needed for one level.")])]
        return h.iff("sceneState.ui == 20", enter, [
            h.iff("sceneState.ui == 21", use_item, [
                h.iff("sceneState.ui == 22", equip_weapon, [
                    h.iff("sceneState.ui == 23", heal_pe, [
                        h.iff("sceneState.ui == 24", equip_armor, bp)])])])])

    # --- windows -------------------------------------------------------------------
    def help_text(self):
        h = self.h
        column = chain([("sceneState.mcol == %d" % k, lit(t)) for k, t in enumerate(
            ["Use or inspect items.", "Use Parasite Energy.", "Change weapons.", "Change armor.",
             "Distribute Bonus Points."])], "''")
        item = "(sel('menu_items') and sel('menu_items').description or '')"
        weapon = chain([("sceneState.wi == 0", lit("M84F: handgun. Fires rounds from the Ammo Crate."))],
                       lit("Club: melee. Unlimited swings at close range."))
        armor = chain([("sceneState.ai == %d" % k, lit("%s: DEF +%d." % (n, d))) for k, (_, n, d) in enumerate(ARMORS)], "''")
        bp = chain([("sceneState.bi == 0", lit("Active Time: the AT gauge fills faster. 100 BP per level."))],
                   lit("Item Capacity: one more item slot. 100 BP per level."))
        page = chain([("sceneState.ui == 20", column), ("sceneState.ui == 21", item), ("sceneState.ui == 22", weapon),
                      ("sceneState.ui == 23", lit("Heal 1: restores 30 HP for 30 PE.")), ("sceneState.ui == 24", armor)], bp)
        return "(sceneState.menuNote ~= '' and sceneState.menuNote or %s)" % page

    def windows(self):
        h = self.h
        def W(wid, x, y, w, hh, text, visible=OPEN, chrome="none"):
            win = {"id": wid, "rect": {"x": fx(x), "y": y, "w": w, "h": hh}, "style": "panel",
                   "visible": visible, "content": [{"type": "text", "text": text}] if text is not None else []}
            if chrome != "skin":          # "skin": the Project's bevelled windowskin
                win["chrome"] = chrome
            return win
        mark = lambda k: ("{sceneState.ui == 20 and sceneState.mcol == %d and '>' or "
                          "(sceneState.ui > 20 and sceneState.mcol == %d and '*' or ' ')}") % (k, k)
        cur = lambda var, k: "{sceneState.%s == %d and '> ' or '  '}" % (var, k)
        rounds = "{%s == 'baton' and '--' or session.items.handgun_ammo}" % h.WEAPON
        out = [
            # frame: title bar (help + clock), icon column, content panel, HP block
            dict(W("menu_title_frame", 0, 0.5, 40, 3, None, chrome="skin"), dimBehind=0.45),   # PS1 darken behind the menu
            W("menu_title", 0, 0.5, 31, 3, "{" + self.help_text() + "}"),
            W("menu_clock", 31, 0.5, 9, 3, CLOCK),
            W("menu_column", 0, 4, 6, 17, (N + N).join(mark(k) + name.upper()[:4] for k, name in enumerate(COLUMN)),
              chrome="skin"),
            W("menu_panel", 6, 4, 34, 17, None, chrome="skin"),
            W("menu_hp", 27, 22, 13, 4, "{sceneState.mHp}/{sceneState.mMax} HP", chrome="skin"),
            {"id": "menu_pe_bar", "rect": {"x": fx(27), "y": 22, "w": 13, "h": 4}, "style": "panel", "chrome": "none",
             "visible": OPEN, "content": [{"type": "gauge", "x": 1, "y": 2.4, "width": 9, "height": 0.45,
                                           "labelPlacement": "right", "label": "PE", "value": "sceneState.mPe",
                                           "max": "100", "fill": [0.15, 0.75, 0.23], "color": [0.11, 0.24, 0.20]}]},
            # status screen (the default view)
            W("menu_status_left", 6, 4, 17, 17,
              "Aya" + N + N + "LEVEL       {sceneState.mLv}" + N + N + "NEXT LEVEL  {sceneState.mNext}" + N + N + N
              + "EQUIPMENT" + N + N + " {" + self.weapon_name + "}  " + rounds + N + N + " {" + self.armor_name + "}",
              visible="sceneState.ui == 20"),
            W("menu_status_right", 22, 4, 18, 17,
              "BONUS POINT  {variables.bp or 0}" + N + N + N + "OFFENSE         {sceneState.mOff}" + N + N
              + "DEFENSE         {sceneState.mDef}" + N + N + "PENERGY         {sceneState.mPen}" + N + N
              + "STATUS RECOVER  {sceneState.mSrec}" + N + N + N + "ACTIVE TIME     {sceneState.mAct}" + N + N
              + "ITEM CAPACITY   {sceneState.mCapLv}", visible="sceneState.ui == 20"),
            # item page: the real inventory, and the slot total
            {"id": "menu_items", "rect": {"x": fx(6), "y": 4, "w": 34, "h": 14}, "style": "list", "chrome": "none",
             "visible": "sceneState.ui == 21",
             "content": [{"type": "list", "listId": "inventory", "format": "{name}  {qty}", "cursor": "sceneState.mi"}]},
            W("menu_items_worn", 6, 17, 16, 3, "Worn: {" + self.armor_name + "}", visible="sceneState.ui == 21"),
            W("menu_items_total", 25, 17, 15, 3, "Total  {sceneState.mUsed}/{sceneState.mCap}", visible="sceneState.ui == 21"),
            # weapon page: the highlighted weapon's real numbers; carried weapons
            W("menu_weapon_stats", 6, 4, 18, 17, chain(
                [("sceneState.wi == 0", "'M84F' .. '\\n\\nATTACK   7\\nRANGE    4.0\\nROUNDS   ' .. session.items.handgun_ammo")],
                "'Club\\n\\nATTACK   3\\nRANGE    1.5\\nROUNDS   --'").join(["{", "}"]), visible="sceneState.ui == 22"),
            W("menu_weapon_list", 24, 4, 16, 17,
              cur("wi", 0) + "M84F{%s == 'handgun' and ' E' or ''}" % h.WEAPON + N
              + cur("wi", 1) + "Club{%s == 'baton' and ' E' or ''}" % h.WEAPON, visible="sceneState.ui == 22"),
            # PE page
            W("menu_pe", 6, 4, 34, 17, "> Heal 1       PE 30", visible="sceneState.ui == 23"),
            # armor page
            W("menu_armor_stats", 6, 4, 18, 17, "{" + chain(
                [("sceneState.ai == %d" % k, lit("%s\\n\\nDEFENSE  +%d" % (n, d))) for k, (_, n, d) in enumerate(ARMORS)],
                "''") + "}", visible="sceneState.ui == 24"),
            W("menu_armor_list", 24, 4, 16, 17, N.join(
                cur("ai", k) + "{(session.items.%s > 0 or sceneState.mArmor == '%s') and '%s' or '--'}" % (i, i, n)
                + "{sceneState.mArmor == '%s' and ' E' or ''}" % i for k, (i, n, _) in enumerate(ARMORS)),
              visible="sceneState.ui == 24"),
            # bonus points page
            W("menu_bp", 6, 4, 34, 17,
              "BONUS POINT  {variables.bp or 0}" + N + N + cur("bi", 0) + "ACTIVE TIME    {sceneState.mAct}" + N
              + cur("bi", 1) + "ITEM CAPACITY  {sceneState.mCapLv}" + N + N + "100 BP raise one level.",
              visible="sceneState.ui == 25"),
        ]
        return out
