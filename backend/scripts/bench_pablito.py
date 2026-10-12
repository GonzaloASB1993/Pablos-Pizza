"""Latency benchmark of Pablito (WhatsApp assistant) against the REAL Anthropic API and a FAKE Firestore.

It runs the production wiring (`routes.whatsapp_routes.process_inbox_message` -> `whatsapp_agent.process_inbox` ->
`ai_chat_routes.run_chat`) for typical messages, with an in-memory `tests.fakes.FakeFirestore` seeded with example data.
Nothing real is read or written: `database.get_db` is replaced before anything else is imported, and Twilio sends are
captured. Only ANTHROPIC_API_KEY is taken from backend/.env (via python-dotenv, never printed).

  python scripts/bench_pablito.py run --variants current,nothink --reps 3 --out bench_current.json
  python scripts/bench_pablito.py run --scenarios stock,gasto --reps 1 --set AI_WHATSAPP_EFFORT=medium
  python scripts/bench_pablito.py report bench_current.json [other.json ...]     # p50/p95 table, rounds, tool calls
  python scripts/bench_pablito.py compare before.json after.json                  # p50/p95 + tool-call equality

Variants (module attributes of routes.ai_chat_routes that are overridden for the run):
  current   the production defaults (whatever the environment / code say)
  nothink   AI_WHATSAPP_THINKING=between_tools (thinking off on Sonnet 5.5; the API has no effort 'minimal')
  haiku     AI_WHATSAPP_MODEL=claude-haiku-5-5
  haiku-nt  haiku + AI_WHATSAPP_THINKING=disabled
Any other `--set NAME=VALUE` is applied on top (e.g. AI_WHATSAPP_EFFORT=medium, AI_WHATSAPP_TEXT_MODEL=claude-haiku-5-5).
"""
import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime, timedelta

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)

PHONE = '+56911111111'

VARIANTS = {
    'current': {},
    'nothink': {'AI_WHATSAPP_THINKING': 'between_tools'},
    'haiku': {'AI_WHATSAPP_MODEL': 'claude-haiku-5-5'},
    'haiku-nt': {'AI_WHATSAPP_MODEL': 'claude-haiku-5-5', 'AI_WHATSAPP_THINKING': 'disabled'},
}

SCENARIOS = {
    'saludo': 'hola pablito, ¿cómo estás?',
    'stock': 'qué hay de stock de queso',
    'agendar': 'agenda un evento para Juan el sábado 16:00 de 12 pizzas',
    'gasto': 'registra gasto bencina 20 mil',
    'ventas': 'cuánto vendimos este mes',
    'semana': 'qué eventos tengo esta semana',
    'pendiente': 'qué hay pendiente',
    'deshacer': 'deshacer',
    'compra': 'compré 2 sacos de harina de 25 kg a 28 mil cada uno',
    'vago': 'quiero registrar algo',
    'manana': 'tengo algo mañana?',
}


# ---------------------------------------------------------------- environment (before importing the app)

def _setup_environment(fs_latency_ms):
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BACKEND, '.env'))            # only to get ANTHROPIC_API_KEY; values are never printed
    os.environ.update({'AI_WHATSAPP_ENABLED': 'true', 'AI_WHATSAPP_ALLOWED': PHONE, 'AI_WHATSAPP_TYPING': 'false',
                       'AI_WHATSAPP_DAILY_LIMIT': '100000', 'AI_WHATSAPP_MODE': 'trigger'})
    for var in ('GOOGLE_APPLICATION_CREDENTIALS', 'FIRESTORE_EMULATOR_HOST'):
        os.environ.pop(var, None)
    from tests.fakes import FakeFirestore
    import tests.fakes as fakes

    holder = {'db': FakeFirestore()}
    import database
    database.get_db = lambda: holder['db']                # nothing imported later can reach the real database

    if fs_latency_ms:                                     # simulate Firestore round trips (the fake is instantaneous)
        delay = fs_latency_ms / 1000.0

        def slow(method):
            def wrapper(*args, **kwargs):
                time.sleep(delay)
                return method(*args, **kwargs)
            return wrapper
        fakes.FakeDocRef.get = slow(fakes.FakeDocRef.get)
        fakes.FakeDocRef.set = slow(fakes.FakeDocRef.set)
        fakes.FakeDocRef.update = slow(fakes.FakeDocRef.update)
        fakes.FakeQuery.stream = slow(fakes.FakeQuery.stream)
    return holder


def _seed(db):
    """Example business data (dates relative to today, Chile)"""
    from utils import clock
    today = clock.now_cl().date()

    def day(offset):
        return (today + timedelta(days=offset)).isoformat()
    saturday = today + timedelta(days=(5 - today.weekday()) % 7 or 7)

    bookings = [
        ('b1', 'Juan Pérez', 'Pizzeros en Acción', f'{saturday.isoformat()}T16:00:00', 12, 'confirmed', 180000, 'Ñuñoa'),
        ('b2', 'María González', 'Pizza Party', f'{day(2)}T13:00:00', 30, 'pending', 240000, 'Providencia'),
        ('b3', 'Colegio San José', 'Pizzeros en Acción', f'{day(8)}T10:00:00', 40, 'confirmed', 360000, 'Las Condes'),
        ('b4', 'Carolina Soto', 'Pizza Party', f'{day(1)}T19:00:00', 20, 'confirmed', 150000, 'La Reina'),
        ('b5', 'Empresa Andes', 'Pizzeros en Acción', f'{day(-6)}T12:00:00', 25, 'completed', 275000, 'Santiago'),
        ('b6', 'Pedro Silva', 'Pizza Party', f'{day(-20)}T18:00:00', 15, 'completed', 120000, 'Maipú'),
    ]
    for bid, name, service, when, people, status, price, place in bookings:
        db.collection('bookings').document(bid).set({
            'client_name': name, 'service_type': service, 'event_date': when, 'event_time': when[11:16],
            'participants': people, 'status': status, 'estimated_price': price, 'location': place,
            'client_email': 'cliente@example.com', 'client_phone': '+56900000000'})
    month = today.replace(day=1)
    for i, (title, price, cost) in enumerate([('Empresa Andes', 275000, 90000), ('Pedro Silva', 120000, 50000),
                                              ('Colegio Norte', 300000, 110000)]):
        db.collection('events').document(f'e{i}').set({
            'title': title, 'event_date': (month + timedelta(days=i * 3)).isoformat(), 'participants': 20 + i,
            'category': 'Pizzeros en Acción', 'final_price': price, 'event_cost': cost, 'status': 'completed'})
    inventory = [('Queso mozzarella', 'Lácteos', 'kg', 3.2, 5, True, 7800), ('Harina 000', 'Secos', 'kg', 60, 25, False, 1100),
                 ('Salsa de tomate', 'Salsas', 'kg', 8, 6, False, 1900), ('Pepperoni', 'Embutidos', 'kg', 1.5, 3, True, 9500),
                 ('Aceite de oliva', 'Aceites', 'lt', 4, 2, False, 6200), ('Queso parmesano', 'Lácteos', 'kg', 2, 1, False, 14000)]
    for i, (name, category, unit, stock, minimum, restock, cost) in enumerate(inventory):
        db.collection('inventory').document(f'i{i}').set({
            'name': name, 'category': category, 'unit': unit, 'current_stock': stock, 'min_stock': minimum,
            'needs_restock': restock, 'cost_per_unit': cost})
    db.collection('contacts').document('c1').set({
        'name': 'Ana', 'email': 'ana@example.com', 'phone': '+56911112222', 'subject': 'Cotización', 'message': 'Hola, cotizar',
        'priority': 'high', 'status': 'pending', 'created_at': datetime.utcnow()})
    db.collection('pending_actions').document('pa1').set({
        'id': 'pa1', 'summary': 'Gasto Copec $15.000', 'status': 'confirmed', 'type': 'expense',
        'created_at': datetime.utcnow() - timedelta(hours=5)})


# ---------------------------------------------------------------- one run

def _percentile(values, q):
    values = sorted(values)
    if not values:
        return None
    index = (len(values) - 1) * q
    low, high = int(index), min(int(index) + 1, len(values) - 1)
    return round(values[low] + (values[high] - values[low]) * (index - low))


def _tool_signature(tools):
    """Order-independent summary of the tool calls (name + inputs) of one run"""
    return sorted(json.dumps({'name': t['name'], 'input': t.get('input')}, ensure_ascii=False, sort_keys=True) for t in tools)


def run_once(holder, app, scenario, text, counter):
    from routes import whatsapp_routes as routes
    from services import whatsapp_agent as wa
    from tests.fakes import FakeFirestore
    holder['db'] = FakeFirestore()
    db = holder['db']
    _seed(db)
    counter[0] += 1
    sid = f'BENCH{counter[0]:06d}'
    sent = []
    routes._send = lambda phone, body: sent.append(body)
    wa.store_inbound(db, {'MessageSid': sid, 'From': f'whatsapp:{PHONE}', 'Body': text, 'NumMedia': '0'})
    started = time.perf_counter()
    status = routes.process_inbox_message(app, sid)
    wall_ms = round((time.perf_counter() - started) * 1000)
    doc = db.collection('whatsapp_inbox').document(sid).get().to_dict()
    timings = doc.get('timings') or {}
    # the exact tool inputs are kept in the usage-less trace of the stored doc only as names; re-read them from a hook
    return {'scenario': scenario, 'status': status, 'wall_ms': wall_ms, 'timings': timings, 'reply': '\n---\n'.join(sent),
            'tools_called': _LAST_TOOLS[:], 'error': doc.get('error')}


_LAST_TOOLS = []


def _hook_tools():
    """Record the tool calls (name + input) of every run without changing behaviour"""
    from routes import ai_chat_routes
    original = ai_chat_routes.execute_tool

    def spy(name, tool_input):
        _LAST_TOOLS.append({'name': name, 'input': tool_input})
        return original(name, tool_input)
    ai_chat_routes.execute_tool = spy


def cmd_run(args):
    holder = _setup_environment(args.fs_latency_ms)
    from flask import Flask
    from routes import ai_chat_routes
    from services import pending_actions_service as pas
    pas._transactional = lambda fn: (lambda txn, *a, **k: fn(txn, *a, **k))   # the fake has no real transactions
    import utils.audit
    utils.audit.log_audit = lambda *a, **k: None
    ai_chat_routes.AI_CHAT_SERVER_FALLBACK = os.getenv('AI_CHAT_SERVER_FALLBACK', 'true').strip().lower() != 'false'
    _hook_tools()
    app = Flask(__name__)
    base = {name: getattr(ai_chat_routes, name) for name in dir(ai_chat_routes) if name.startswith('AI_')}
    overrides = {}
    for item in args.set or []:
        key, value = item.split('=', 1)
        overrides[key] = value

    variants = [v.strip() for v in args.variants.split(',')]
    scenarios = [s.strip() for s in args.scenarios.split(',')] if args.scenarios != 'all' else list(SCENARIOS)
    print(f'effective config: model={ai_chat_routes.AI_CHAT_MODEL} whatsapp_effort={ai_chat_routes.AI_WHATSAPP_EFFORT} '
          f'cache_ttl={ai_chat_routes.AI_CACHE_TTL} fallback={ai_chat_routes.AI_CHAT_SERVER_FALLBACK} '
          f'fs_latency_ms={args.fs_latency_ms}', flush=True)

    def apply(variant):
        for name, value in base.items():
            setattr(ai_chat_routes, name, value)
        for source in (VARIANTS[variant], overrides):
            for name, value in source.items():
                if not hasattr(ai_chat_routes, name):
                    print(f'  (note: {name} does not exist in this code version; ignored)')
                    continue
                current = getattr(ai_chat_routes, name)
                setattr(ai_chat_routes, name, int(value) if isinstance(current, int) else value)

    results, counter = [], [0]
    # warm the prefix cache of every variant before measuring (the production keep-warm does the same)
    for variant in variants:
        apply(variant)
        with app.test_request_context():
            try:
                for _ in range(2):
                    ai_chat_routes.warm_prompt_cache()
            except Exception as exc:  # noqa: BLE001
                print(f'warm-up failed for {variant}: {str(exc)[:200]}')
    for rep in range(args.reps):
        for scenario in scenarios:
            for variant in variants:
                apply(variant)
                del _LAST_TOOLS[:]
                row = run_once(holder, app, scenario, SCENARIOS[scenario], counter)
                row.update({'variant': variant, 'rep': rep})
                results.append(row)
                t = row['timings']
                print(f"[{rep}] {scenario:10s} {variant:9s} wall={row['wall_ms']:6d}ms agent={t.get('agent_ms')} "
                      f"rounds={len(t.get('rounds', []))} tools={[x['name'] for x in row['tools_called']]} {row['status']}"
                      + (f" ERROR {row['error']}" if row['error'] else ''), flush=True)
    meta = {'when': datetime.utcnow().isoformat(), 'overrides': overrides, 'fs_latency_ms': args.fs_latency_ms,
            'model': ai_chat_routes.AI_CHAT_MODEL, 'git': os.popen('git rev-parse --short HEAD').read().strip()}
    with open(args.out, 'w', encoding='utf-8') as handle:
        json.dump({'meta': meta, 'results': results}, handle, ensure_ascii=False, indent=1, default=str)
    print('saved', args.out)


# ---------------------------------------------------------------- reports

def _load(path):
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


def _group(results):
    groups = {}
    for row in results:
        groups.setdefault((row['scenario'], row['variant']), []).append(row)
    return groups


def _stat(rows, key):
    values = [r['timings'][key] if key in r['timings'] else r.get(key) for r in rows]
    values = [v for v in values if isinstance(v, (int, float))]
    return (_percentile(values, 0.5), _percentile(values, 0.95)) if values else (None, None)


def cmd_report(args):
    for path in args.files:
        data = _load(path)
        print(f"\n## {path}  (git {data['meta'].get('git')}, overrides {data['meta'].get('overrides')}, "
              f"fs_latency_ms {data['meta'].get('fs_latency_ms')})")
        print('| escenario | variante | n | total p50 | total p95 | agente p50 | rondas | ronda ms (media) | herramientas ms (media) | llamadas |')
        print('|---|---|---|---|---|---|---|---|---|---|')
        for (scenario, variant), rows in sorted(_group(data['results']).items()):
            total = _stat(rows, 'total_ms')
            agent = _stat(rows, 'agent_ms')
            rounds = [len(r['timings'].get('rounds', [])) for r in rows]
            round_ms = [x['ms'] for r in rows for x in r['timings'].get('rounds', [])]
            tool_ms = [x['ms'] for r in rows for x in r['timings'].get('tools', [])]
            calls = sorted({tuple(sorted(t['name'] for t in r['tools_called'])) for r in rows})
            print(f"| {scenario} | {variant} | {len(rows)} | {total[0]} | {total[1]} | {agent[0]} | "
                  f"{statistics.mean(rounds):.1f} | {round(statistics.mean(round_ms)) if round_ms else '-'} | "
                  f"{round(statistics.mean(tool_ms)) if tool_ms else '-'} | {' / '.join(','.join(c) or '-' for c in calls)} |")


def cmd_compare(args):
    before, after = _load(args.before), _load(args.after)
    gb, ga = _group(before['results']), _group(after['results'])
    print(f"before: git {before['meta'].get('git')} {before['meta'].get('overrides')}  |  after: git {after['meta'].get('git')} "
          f"{after['meta'].get('overrides')}")
    print('| escenario | variante | total p50 antes | p50 despues | p95 antes | p95 despues | rondas antes | rondas despues | mismas llamadas |')
    print('|---|---|---|---|---|---|---|---|---|')
    for key in sorted(set(gb) & set(ga)):
        b, a = gb[key], ga[key]
        sb, sa = _stat(b, 'total_ms'), _stat(a, 'total_ms')
        calls_b = {tuple(_tool_signature(r['tools_called'])) for r in b}
        calls_a = {tuple(_tool_signature(r['tools_called'])) for r in a}
        names_b = {tuple(sorted(t['name'] for t in r['tools_called'])) for r in b}
        names_a = {tuple(sorted(t['name'] for t in r['tools_called'])) for r in a}
        same = 'identicas' if calls_b == calls_a else ('mismos nombres' if names_b == names_a else 'DISTINTAS')
        rb = statistics.mean(len(r['timings'].get('rounds', [])) for r in b)
        ra = statistics.mean(len(r['timings'].get('rounds', [])) for r in a)
        print(f'| {key[0]} | {key[1]} | {sb[0]} | {sa[0]} | {sb[1]} | {sa[1]} | {rb:.1f} | {ra:.1f} | {same} |')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='cmd', required=True)
    run = sub.add_parser('run')
    run.add_argument('--variants', default='current')
    run.add_argument('--scenarios', default='all')
    run.add_argument('--reps', type=int, default=3)
    run.add_argument('--fs-latency-ms', type=int, default=0, help='simulated Firestore round trip per call')
    run.add_argument('--set', action='append', help='NAME=VALUE override of an AI_* attribute of ai_chat_routes')
    run.add_argument('--out', default='bench_result.json')
    report = sub.add_parser('report')
    report.add_argument('files', nargs='+')
    compare = sub.add_parser('compare')
    compare.add_argument('before')
    compare.add_argument('after')
    args = parser.parse_args()
    {'run': cmd_run, 'report': cmd_report, 'compare': cmd_compare}[args.cmd](args)


if __name__ == '__main__':
    main()
