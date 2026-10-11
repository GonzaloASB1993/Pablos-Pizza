"""WhatsApp "deshacer": SI saves, "deshacer" proposes the undo, SI undoes it (exact or not at all)"""
import os
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402,F401
from services import booking_proposals, expense_proposals, inventory_proposals  # noqa: E402
from services import inventory_service as inv  # noqa: E402
from services import pending_actions_service as pas  # noqa: E402
from services import undo_service  # noqa: E402
from services import whatsapp_agent as wa  # noqa: E402
from tests.fakes import FakeFirestore  # noqa: E402
from tests.undo_support import doc, item, seed_item  # noqa: E402

ADMIN = '+56911111111'
USER = wa.user_for(ADMIN)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv('AI_WHATSAPP_ENABLED', 'true')
    monkeypatch.setenv('ADMIN_WHATSAPP_NUMBER', ADMIN)
    monkeypatch.setenv('PARTNER_WHATSAPP_NUMBER', '+56922222222')
    monkeypatch.delenv('AI_WHATSAPP_ALLOWED', raising=False)
    monkeypatch.setattr(pas, '_transactional', lambda fn: (lambda txn, *a, **k: fn(txn, *a, **k)))
    monkeypatch.setattr('utils.audit.log_audit', lambda *a, **k: None)
    monkeypatch.setattr('services.booking_service.notify_new_booking', lambda booking: None)


@pytest.fixture
def db():
    return FakeFirestore()


class Chat:
    """Drives process_inbox like a person typing; the agent is a fake that proposes what the test tells it to"""

    def __init__(self, db):
        self.db, self.sent, self.proposals, self.agent_calls, self.n = db, [], [], [], 0

    def agent(self, messages, user):
        self.agent_calls.append(messages[-1])
        actions = [fn(self.db) for fn in self.proposals]
        self.proposals = []
        return {'response': 'Listo, lo preparé.', 'pending_actions': actions, 'choices': [], 'usage': {}}

    def say(self, text, **form):
        self.n += 1
        wa.store_inbound(self.db, {'MessageSid': f'SM{self.n}', 'From': f'whatsapp:{ADMIN}', 'Body': text, 'NumMedia': '0', **form})
        mark = len(self.sent)
        deps = wa.Deps(send=lambda phone, body: self.sent.append(body), run_chat=self.agent,
                       download_media=lambda url: b'', now=datetime.utcnow)
        wa.process_inbox(self.db, f'SM{self.n}', deps)
        return '\n'.join(self.sent[mark:])


def waste(item_id='flour', quantity=3):
    return lambda db: inventory_proposals.propose_stock_adjustment(
        db, {'item_id': item_id, 'mode': 'waste', 'quantity': quantity}, USER)


def expense(supplier='Copec', total=20000):
    return lambda db: expense_proposals.propose_expense(
        db, {'supplier': supplier, 'total': total, 'date': '2026-10-10'}, USER)


def saved_one_thing(db):
    """The person saved a waste of 3 kg of flour through WhatsApp (stock 10 -> 7)"""
    seed_item(db, 'flour', stock=10, avg=1000)
    chat = Chat(db)
    chat.proposals = [waste()]
    chat.say('anota 3 kilos de merma de harina')
    assert 'Guardado' in chat.say('si') or 'Listo' in chat.sent[-1]
    assert item(db, 'flour')['current_stock'] == 7
    return chat


# ---------- the command ----------

@pytest.mark.parametrize('text,expected', [
    ('deshacer', (None,)), ('Deshacer!', (None,)), ('deshaz', (None,)), ('deshace', (None,)), ('revertir', (None,)),
    ('deshacer lo último', (None,)), ('deshaz eso', (None,)), ('deshacer 2', (2,)), ('revertir todas', ('all',)),
    ('deshacer todo', ('all',)),
])
def test_the_command_is_recognized(text, expected):
    assert wa.parse_undo(text) == expected


@pytest.mark.parametrize('text', ['quiero deshacer la compra de ayer', 'deshacer la reserva', 'no deshagas nada', 'si', '',
                                  'deshacer 2 3', 'rehacer'])
def test_other_text_is_not_the_command(text):
    assert wa.parse_undo(text) is None


# ---------- the flow ----------

def test_si_records_what_it_saved_for_undo(db):
    chat = saved_one_thing(db)
    entries = doc(db, 'whatsapp_contacts', ADMIN)['last_confirmed']
    assert len(entries) == 1 and entries[0]['n'] == 1 and entries[0]['at']
    assert pas.get(db, entries[0]['id'])['type'] == 'stock_adjustment'
    assert chat.agent_calls                                                      # sanity: the agent was used for the proposal


def test_deshacer_proposes_and_si_undoes(db):
    chat = saved_one_thing(db)
    calls_before = len(chat.agent_calls)

    proposal = chat.say('deshacer')
    assert '↩️ ¿Deshago *Merma de Harina*?' in proposal and '*SI* / *NO*' in proposal
    assert 'Harina: stock 7 → 10' in proposal
    assert len(proposal.split('\n')) <= 5
    assert item(db, 'flour')['current_stock'] == 7                               # proposing writes nothing
    assert len(chat.agent_calls) == calls_before                                 # deterministic: no model involved

    done = chat.say('si')
    assert 'deshice *Merma de Harina*' in done
    assert item(db, 'flour')['current_stock'] == 10
    target = pas.get(db, doc(db, 'whatsapp_contacts', ADMIN)['last_confirmed'][0]['id'])
    assert target['status'] == 'confirmed' and target['undo']['state'] == 'done'
    assert len(chat.agent_calls) == calls_before


def test_no_cancels_the_undo(db):
    chat = saved_one_thing(db)
    chat.say('deshacer')
    assert 'Cancelada' in chat.say('no')
    assert item(db, 'flour')['current_stock'] == 7


def test_deshacer_twice_does_not_offer_the_same_thing_again(db):
    chat = saved_one_thing(db)
    chat.say('deshacer')
    chat.say('si')
    assert wa.NOTHING_TO_UNDO in chat.say('deshacer')
    assert item(db, 'flour')['current_stock'] == 10
    assert len([m for m in db.store['inventory_movements'].values() if m['movement_type'] == 'reversal']) == 1


def test_an_undo_is_not_remembered_as_the_last_thing(db):
    chat = saved_one_thing(db)
    original = doc(db, 'whatsapp_contacts', ADMIN)['last_confirmed']
    chat.say('deshacer')
    chat.say('si')
    assert doc(db, 'whatsapp_contacts', ADMIN)['last_confirmed'] == original      # still the original; the undo is not "last"
    assert wa.NOTHING_TO_UNDO in chat.say('deshacer')


def test_nothing_to_undo(db):
    chat = Chat(db)
    reply = chat.say('deshacer')
    assert reply == wa.NOTHING_TO_UNDO and chat.agent_calls == []


def test_a_pending_proposal_is_pointed_to_no_when_there_is_nothing_confirmed(db):
    seed_item(db, 'flour')
    chat = Chat(db)
    chat.proposals = [waste()]
    chat.say('anota una merma')
    assert 'responde *NO*' in chat.say('deshacer')


def test_a_later_movement_is_refused_with_the_alternative(db):
    chat = saved_one_thing(db)
    inv.register_movement(db, 'flour', 'purchase', 5, 1000, movement_id='later')
    reply = chat.say('deshacer')
    assert 'Ya hubo movimientos de Harina' in reply and 'conteo' in reply
    assert '*SI*' not in reply and item(db, 'flour')['current_stock'] == 12
    assert [a for a in db.store['pending_actions'].values() if a['type'] == 'undo'] == []


def test_the_state_changing_between_the_proposal_and_the_si_is_reported(db):
    chat = saved_one_thing(db)
    chat.say('deshacer')
    inv.register_movement(db, 'flour', 'purchase', 5, 1000, movement_id='later')
    reply = chat.say('si')
    assert 'No pude hacerlo' in reply and 'Ya hubo movimientos de Harina' in reply
    assert item(db, 'flour')['current_stock'] == 12


def test_an_old_action_says_to_use_the_panel(db):
    chat = saved_one_thing(db)
    entry = doc(db, 'whatsapp_contacts', ADMIN)['last_confirmed'][0]
    stored = doc(db, 'pending_actions', entry['id'])['result']
    stored.pop('movement_id')
    stored['delta'] = 5                                                           # not the no-op shape either
    db.collection('pending_actions').document(entry['id']).update({'result': stored})
    assert chat.say('deshacer') == 'Esa es antigua, hazlo desde el panel.'


def test_after_24_hours_it_points_to_the_panel(db):
    chat = saved_one_thing(db)
    entry = doc(db, 'whatsapp_contacts', ADMIN)['last_confirmed'][0]
    db.collection('pending_actions').document(entry['id']).update({'confirmed_at': datetime.utcnow() - timedelta(hours=30)})
    reply = chat.say('deshacer')
    assert '24 horas' in reply and 'panel' in reply and item(db, 'flour')['current_stock'] == 7


def test_a_booking_the_customer_was_told_about_is_not_undone(db):
    chat = Chat(db)
    chat.proposals = [lambda d: booking_proposals.propose_booking(d, {
        'client_name': 'Carla Soto', 'client_email': 'carla@example.com', 'services': ['party'],
        'event_date': '2027-12-20', 'event_time': '15:00', 'location': 'Calle 1', 'comuna': 'Lampa', 'pizza_quantity': 12}, USER)]
    chat.say('agenda una pizza party')
    chat.say('si')
    booking_id = next(iter(db.store['bookings']))
    db.collection('bookings').document(booking_id).update({'status': 'confirmed'})
    assert 'cancélala desde el panel' in chat.say('deshacer')
    assert doc(db, 'bookings', booking_id)['status'] == 'confirmed'


def test_a_pending_booking_is_undone_and_warns_that_the_notice_was_sent(db):
    chat = Chat(db)
    chat.proposals = [lambda d: booking_proposals.propose_booking(d, {
        'client_name': 'Carla Soto', 'client_email': 'carla@example.com', 'services': ['party'],
        'event_date': '2027-12-20', 'event_time': '15:00', 'location': 'Calle 1', 'comuna': 'Lampa', 'pizza_quantity': 12}, USER)]
    chat.say('agenda una pizza party')
    chat.say('si')
    proposal = chat.say('deshacer')
    assert 'Reserva de Carla Soto' in proposal and 'ya les llegó' in proposal
    done = chat.say('si')
    assert 'deshice' in done and 'ya les llegó' in done
    assert next(iter(db.store['bookings'].values()))['status'] == 'cancelled'


# ---------- several things confirmed with one SI ----------

def two_things(db):
    seed_item(db, 'flour', stock=10, avg=1000)
    chat = Chat(db)
    chat.proposals = [waste(), expense()]
    chat.say('anota la merma y el gasto')
    chat.say('si todas')
    return chat


def test_si_todas_records_every_action_with_its_number(db):
    two_things(db)
    entries = doc(db, 'whatsapp_contacts', ADMIN)['last_confirmed']
    assert [e['n'] for e in entries] == [1, 2]


def test_bare_deshacer_asks_which_one_when_several_were_saved(db):
    chat = two_things(db)
    reply = chat.say('deshacer')
    assert 'Confirmaste varias cosas' in reply and '*1*: Merma de Harina' in reply and '*2*: Gasto Copec $20.000' in reply
    assert item(db, 'flour')['current_stock'] == 7 and len(db.store['variable_expenses']) == 1


def test_deshacer_n_undoes_only_that_one(db):
    chat = two_things(db)
    assert '¿Deshago *Gasto Copec $20.000*?' in chat.say('deshacer 2')
    chat.say('si')
    assert len(db.store['variable_expenses']) == 0 and item(db, 'flour')['current_stock'] == 7
    assert 'No encuentro la 5' in chat.say('deshacer 5')


def test_deshacer_todas_proposes_both_and_si_todas_undoes_both(db):
    chat = two_things(db)
    reply = chat.say('deshacer todas')
    assert '¿Cuáles deshago?' in reply and '*SI 1*' in reply
    assert 'deshice' in chat.say('si todas')
    assert len(db.store['variable_expenses']) == 0 and item(db, 'flour')['current_stock'] == 10


def test_one_refusal_among_several_is_reported_next_to_the_proposal(db):
    chat = two_things(db)
    inv.register_movement(db, 'flour', 'purchase', 5, 1000, movement_id='later')
    reply = chat.say('deshacer todas')
    assert '¿Deshago *Gasto Copec $20.000*?' in reply and 'No se puede: Merma de Harina' in reply


def test_deshacer_cancels_a_stale_pending_proposal(db):
    chat = saved_one_thing(db)
    chat.proposals = [waste(quantity=1)]
    chat.say('anota otra merma')
    live = [a for a in db.store['pending_actions'].values() if a['status'] == 'pending']
    assert len(live) == 1
    reply = chat.say('deshacer')
    assert '(Cancelé la propuesta que tenías pendiente.)' in reply
    assert [a for a in db.store['pending_actions'].values() if a['type'] == 'stock_adjustment' and a['status'] == 'pending'] == []


# ---------- not a command ----------

def test_a_forwarded_message_or_a_photo_with_those_words_is_not_a_command(db):
    chat = saved_one_thing(db)
    calls = len(chat.agent_calls)
    chat.say('deshacer', Forwarded='true')
    assert len(chat.agent_calls) == calls + 1 and item(db, 'flour')['current_stock'] == 7
