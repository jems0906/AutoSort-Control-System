# AutoSort Control System

A PLC-style package routing simulator that models how an automated sortation line behaves inside a fulfillment center.

## ✅ What this project demonstrates

- **PLC/control systems thinking** with scan → decision → route cycles
- **Industrial automation logic** using deterministic state-machine behavior
- **Routing logic** similar to warehouse package sortation
- **Failure handling** for misreads, blocked lanes, overflow, and queue buildup
- **Basic visualization** through both a console dashboard and a small Tkinter UI
- **Operator controls** for manual barcode input and lane jam simulation

## System flow

1. Packages enter the **inbound queue**
2. A simulated scanner reads the package barcode / destination
3. Routing logic applies:
   - `X -> Lane A`
   - `Y -> Lane B`
   - `Z -> Lane C`
4. If a package cannot be routed, it is diverted to **exception handling**

## PLC-style state machine

```text
IDLE -> SCAN -> DECIDE -> ROUTE -> CLEAR
                |         |
                |         +-> REQUEUE (blocked/full lane)
                +------------> ERROR (misread / overflow)
```

## Simulated constraints

- **Inbound capacity limits**
- **Lane capacity limits**
- **Blocked downstream lane events**
- **Queue buildup and retry logic**
- **Misread / bad barcode handling**

---

## 🚀 Run the project

### Console simulation

```bash
python main.py --mode console --cycles 18
```

### UI simulation

```bash
python main.py --mode ui
```

### Interactive demo controls in the UI

- **Inject Package**: add a package directly by destination (`X`, `Y`, `Z`, or `Q`)
- **Scan Barcode**: test barcode-style inputs like `BC-Y-501`
- **Force misreads**: enter `BAD-UNKNOWN-01`
- **Toggle Lane A/B/C**: simulate a jam or blocked conveyor lane

---

## Example PLC-style control logic

```python
if scanned_destination == "X":
    route_to("A")
elif scanned_destination == "Y":
    route_to("B")
elif scanned_destination == "Z":
    route_to("C")
else:
    divert_to_exception_lane("MISREAD")
```

## Project structure

```text
AutoSort Control System/
├── main.py
├── pyproject.toml
├── README.md
├── docs/
│   └── PLC_DESIGN.md
├── src/
│   └── autosort/
│       ├── __init__.py
│       ├── console_view.py
│       ├── controller.py
│       └── ui.py
└── tests/
    └── test_controller.py
```

## Documentation

- `docs/PLC_DESIGN.md` — PLC I/O map, ladder-style logic, and state machine notes

## Verification

Run the automated checks with:

```bash
python -m unittest discover -s tests -v
```

## Submission checklist

- ✅ Working simulator in `console` and `ui` modes
- ✅ PLC-style control documentation
- ✅ Automated verification tests
- ✅ Clean, minimal project structure
- ✅ MIT `LICENSE`

## Notes

This implementation uses **Python to mimic PLC logic**, which makes it easy to demo industrial control principles without requiring a hardware PLC or OpenPLC runtime. It uses only the Python standard library, so no separate dependency file is required.
