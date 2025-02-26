from __future__ import annotations

from collections import defaultdict
import json
import re

from .utils import dbg, int_keys, get_file

_file = get_file("controllers.json")
if _file is None:
    raise FileNotFoundError("Could not find controllers.json")
controller_data = int_keys(json.loads(_file))
CONTROLLERS = list(controller_data.keys())


class Controller:
    """Represents a controller, gamepad, or other input device."""

    def __init__(self, controller: str) -> None:
        if controller not in controller_data:
            raise ValueError(f"Invalid controller: {controller}")
        data = controller_data[controller]
        self.name: str = data["name"]
        self.buttons: dict[int, str] = defaultdict(str, data["buttons"])
        self.axis_buttons: dict[int, str] = defaultdict(str, data["axis_buttons"])
        self.axes: dict[int, str] = defaultdict(str, data["axes"])
        self.num_buttons: int = data["num_buttons"]
        self.num_axes: int = data["num_axes"]
        self.has_stick: bool = data["has_stick"]
        self.has_dpad: bool = data["has_dpad"]
        self.dpad_buttons = self.get_dpad_buttons()
        self.stick_button = self.get_stick_button()
        self.supported: bool = data["supported"]

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"<Controller: {self.name}>"

    def __getitem__(self, index: int) -> str:
        return self.buttons[index]

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Controller) and self.name == __o.name

    def axis(self, index: int) -> str:
        """Get the name of an axis."""
        return self.axes[index]

    def axis_button(self, index: int) -> str:
        """Get the name of an axis 'button'."""
        return self.axis_buttons[index]

    def button(self, index: int) -> str:
        """Get the name of a button"""
        return self.buttons[index]

    # FIXME: Needs to handle axis dpads
    def get_dpad_buttons(self) -> tuple[int, int, int, int] | None:
        """Get the indicies of the D-pad buttons."""
        if not self.has_dpad:
            return None
        indicies, buttons = zip(*self.buttons.items())
        if (
            "D-Pad Up" in buttons
            and "D-Pad Down" in buttons
            and "D-Pad Left" in buttons
            and "D-Pad Right" in buttons
        ):
            return (
                indicies[buttons.index("D-Pad Up")],
                indicies[buttons.index("D-Pad Down")],
                indicies[buttons.index("D-Pad Left")],
                indicies[buttons.index("D-Pad Right")],
            )
        else:
            return None

    def get_stick_button(self) -> int | None:
        """Get the index of the stick button."""
        indicies, buttons = zip(*self.buttons.items())
        for button_name in ("Stick Click", "Left Stick Click", "Right Stick Click"):
            if button_name in buttons:
                return indicies[buttons.index(button_name)]
        return None


def get_controller_list() -> list[str]:
    """Returns a list of all supported controllers."""
    return [
        controller["name"]
        for controller in controller_data.values()
        if controller["supported"]
    ]


def parse_controller_id(controller_id: str) -> tuple[str | None, str | None] | None:
    """Extracts the vendor and device codes from the ID string"""
    vendor_search = re.search(r"Vendor: (\w{4})", controller_id)
    device_search = re.search(r"Product: (\w{4})", controller_id)
    vendor_id = vendor_search.group(1).lower() if vendor_search is not None else None
    device_id = device_search.group(1).lower() if device_search is not None else None
    return (vendor_id, device_id)


def controller_name_tuple(name: str, buttons: int):
    """The second form is used to disambiguate controllers with compatibility modes."""
    return name, name + f" ({buttons} buttons)"


def identify_controller(
    id_: str,
    buttons: int | str,
    num_axes: int | str,
    ebd: bool = False,
) -> tuple[str, str] | None:
    """Identifies a controller based on the ID name and number of buttons and axes."""
    dbg(id_)
    buttons, num_axes = int(buttons), int(num_axes)
    device_name = id_
    vendor_id, device_id = parse_controller_id(id_)

    # Joy-Cons present twice, only recognise the correct one
    if id_ == "Joy-Con (L/R) (STANDARD GAMEPAD)":
        return None

    # Identify 8BitDo controllers pretending to be something else
    if ebd and (vendor_id, device_id) in [
        ("054c", "05c4"),
        ("045e", "028e"),
    ]:
        return controller_name_tuple("8BitDo Pro", buttons)

    if ebd and (vendor_id, device_id) == ("045e", "02e0"):
        return controller_name_tuple("8BitDo Zero (X Input)", buttons)

    if vendor_id == "2dc8" or not "8bitdo" in id_.lower():
        controllers_file = get_file("controllerIDs.json")
        assert controllers_file is not None
        controller_ids = json.loads(controllers_file)

        try:
            device_name = controller_ids["devices"][vendor_id][device_id]
        except KeyError:
            pass
        else:
            if device_name in CONTROLLERS:
                return controller_name_tuple(device_name, buttons)
            if device_name == "invalid":
                return None

    id_ = id_.lower()

    # this would be a good place to use case match
    if "dualshock" in id_ or "playstation" in id_ or "sony" in id_:
        if buttons == 17:
            device_name = "DualShock 3"
        elif "dualsense" in id_:
            device_name = "DualSense"
        elif buttons == 18:
            device_name = "DualShock 4"
    elif "xbox" in id_ or "microsoft" in id_:
        if "360" in id_ or "adaptive" in id_:
            device_name = "Xbox 360"
        elif "one" in id_:
            device_name = "Xbox One"
        elif "series" in id_ or "elite" in id_:
            device_name = "Xbox Series"
        elif buttons == 17:
            device_name = "Xbox 360"
        else:
            device_name = "Xbox Series"
    elif "joycon" in id_ or "joy-con" in id_ or "switch" in id_:
        if "pro" in id_:
            device_name = "Switch Pro"
        if "left" in id_:
            device_name = "Joy-Con Left"
        if "right" in id_:
            device_name = "Joy-Con Right"
        else:
            device_name = "Joy-Con"
    elif "steam" in id_ or "valve" in id_:
        device_name = "Steam Controller"
    elif "8bitdo" in id_:
        if "zero" in id_:
            if buttons == 17:
                device_name = "8BitDo Zero (X Input)"
            else:
                device_name = "8BitDo Zero (D Input)"
        elif "lite" in id_:
            device_name = "8BitDo Lite"
        elif "pro" in id_:
            device_name = "8BitDo Pro"
    elif "ps3" in id_:
        device_name = "DualShock 3"
    elif "ps4" in id_:
        device_name = "DualShock 4"
    elif "ps5" in id_ or "dualsense" in id_:
        device_name = "DualSense"

    return controller_name_tuple(device_name, buttons)


BUTTON_ORDER = [
    "Left Shoulder",
    "Right Shoulder",
    "Left Trigger",
    "Right Trigger",
    "SL",
    "SR",
    "ZL",
    "ZR",
    "L",
    "R",
    "L1",
    "R1",
    "L2",
    "R2",
    "Triangle",
    "Circle",
    "Square",
    "Cross",
    "Y",
    "X",
    "B",
    "A",
    "D-Pad Up",
    "D-Pad Down",
    "D-Pad Left",
    "D-Pad Right",
    "Up",
    "Down",
    "Left",
    "Right",
    "Up Arrow",
    "Down Arrow",
    "Left Arrow",
    "Right Arrow",
    "Z",
    "LZ",
    "RZ",
    "Capture",
    "Plus",
    "Minus",
    "Menu",
    "View",
    "Start",
    "Select",
    "Star",
    "Steam",
    "Forward",
    "Back",
    "Xbox",
    "Home",
    "Share",
    "Options",
    "Stick",
    "Left Stick",
    "Right Stick",
    "Left Stick Click",
    "Right Stick Click",
    "Click Left Stick",
    "Click Right Stick",
    "Stick Click",
    "Stick Up",
    "Stick Down",
    "Stick Left",
    "Stick Right",
    "Left Stick",
    "Right Stick",
    "Left Stick Up",
    "Left Stick Down",
    "Left Stick Left",
    "Left Stick Right",
    "Right Track",
    "Left Track Up",
    "Left Track Down",
    "Left Track Left",
    "Left Track Right",
    "Right Stick Up",
    "Right Stick Down",
    "Right Stick Left",
    "Right Stick Right",
    "Right Track Up",
    "Right Track Down",
    "Right Track Left",
    "Right Track Right",
    "Left D-Pad Up",
    "Left D-Pad Down",
    "Left D-Pad Left",
    "Left D-Pad Right",
    "Right D-Pad Up",
    "Right D-Pad Down",
    "Right D-Pad Left",
    "Right D-Pad Right",
    "Left Grip",
    "Right Grip",
    "Pad",
    "PS",
]

BUTTONS_ON_LEFT = [
    "Left Shoulder",
    "Left Trigger",
    "L2",
    "D-Pad Up",
    "D-Pad Down",
    "D-Pad Left",
    "D-Pad Right",
    "Up",
    "Down",
    "Left",
    "Right",
    "Up Arrow",
    "Down Arrow",
    "Left Arrow",
    "Right Arrow",
    "Z",
    "LZ",
    "RZ",
    "Capture",
    "Plus",
    "Minus",
    "Menu",
    "View",
    "Select",
    "Star",
    "Steam",
    "Back",
    "Xbox",
    "Share",
    "Stick",
    "Left Stick",
    "Left Stick Click",
    "Click Left Stick",
    "Stick Up",
    "Stick Down",
    "Stick Left",
    "Stick Right",
    "Left Stick",
    "Left Stick Up",
    "Left Stick Down",
    "Left Stick Left",
    "Left Stick Right",
    "Left D-Pad Up",
    "Left D-Pad Down",
    "Left D-Pad Left",
    "Left D-Pad Right",
    "Left Grip",
    "PS",
]
