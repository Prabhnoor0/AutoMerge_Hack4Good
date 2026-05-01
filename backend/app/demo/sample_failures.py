"""
Demo Sample Failures

Realistic failure scenarios for demonstration purposes.
"""


DEMO_SCENARIOS = {
    "test_failure": {
        "title": "test_calculate_total fails — expected 150.00, got 50.00",
        "failure_type": "test_failure",
        "logs": """$ python -m pytest tests/test_utils.py -v
========================= test session starts =========================
platform linux -- Python 3.11.4, pytest-7.4.0
collected 12 items

tests/test_utils.py::test_format_date PASSED
tests/test_utils.py::test_parse_input PASSED
tests/test_utils.py::test_validate_email PASSED
tests/test_utils.py::test_calculate_total FAILED
tests/test_utils.py::test_calculate_tax PASSED
tests/test_utils.py::test_round_currency PASSED

=============================== FAILURES ================================
_________________________ test_calculate_total __________________________

    def test_calculate_total():
        items = [
            Item(name="Widget A", price=25.00, quantity=2),
            Item(name="Widget B", price=50.00, quantity=1),
            Item(name="Widget C", price=25.00, quantity=1),
        ]
>       assert calculate_total(items) == 125.00
E       AssertionError: assert 100.0 == 125.00
E        +  where 100.0 = calculate_total([Item(...), Item(...), Item(...)])

src/utils/calculate.py:15: AssertionError
========================= 1 failed, 5 passed in 0.42s =========================
""",
    },
    "build_error": {
        "title": "TypeScript compilation failed in Dashboard.tsx",
        "failure_type": "build_error",
        "logs": """$ npm run build

> automerge-frontend@1.0.0 build
> next build

   ▲ Next.js 14.2.3
   Creating an optimized production build ...

Failed to compile.

./src/components/Dashboard.tsx
TypeScript error in ./src/components/Dashboard.tsx(7,42):
  Type 'null' is not assignable to type 'string'.  TS2322

    5 | export function Dashboard({ data }) {
    6 |   const [filter, setFilter] = useState(null);
  > 7 |   const filtered = data.filter(d => d.status = filter);
      |                                          ^
    8 |   return <DataChart data={filtered} />;
    9 | }

./src/components/Dashboard.tsx(5,26):
  Parameter 'data' implicitly has an 'any' type.  TS7006

Build failed. Exit code: 1

npm ERR! code ELIFECYCLE
npm ERR! errno 1
""",
    },
    "type_error": {
        "title": "TypeError: Cannot read properties of undefined (reading 'name')",
        "failure_type": "type_error",
        "logs": """$ node src/server.js
Server starting on port 3000...

/app/src/services/api.ts:4
  return data.user.name;
                  ^

TypeError: Cannot read properties of undefined (reading 'name')
    at fetchUser (/app/src/services/api.ts:4:19)
    at processTicksAndRejections (node:internal/process/task_queues:95:5)
    at async UserController.getProfile (/app/src/controllers/user.ts:12:20)
    at async /app/src/middleware/handler.ts:8:5

Traceback:
  File "src/services/api.ts", line 4
    return data.user.name;
  Error: response.json() returns a Promise, not the resolved value.
  The 'await' keyword is missing before response.json().

Process exited with code 1
""",
    },
}


def get_demo_scenario(scenario_name: str) -> dict:
    """Get a demo scenario by name. Falls back to test_failure."""
    return DEMO_SCENARIOS.get(scenario_name, DEMO_SCENARIOS["test_failure"])


def list_scenarios() -> list[str]:
    """List available demo scenario names."""
    return list(DEMO_SCENARIOS.keys())
