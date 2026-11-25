# -*- coding: utf-8 -*-
import unittest
from dataclasses import replace
from threading import Barrier, Thread
from end_guard import EndGuard, Receipt

class EndTests(unittest.TestCase):
    def setUp(self):
        self.g = EndGuard()
        self.g.start('a', 'LOCAL', True)
        self.ack = Receipt('a', 'LOCAL', 'LOCAL_ADAPTER', 'SUCCESS', True, True, True)

    def test_running_blocks_new_id(self):
        self.assertEqual(self.g.start('b', 'CLOUD', True), 'BLOCKED_IN_FLIGHT')

    def test_cancel_retains_slot(self):
        self.assertEqual(self.g.interrupt('a', 'CANCEL'), 'CANCEL_REQUESTED')
        self.assertIsNotNone(self.g.active)
        self.assertEqual(self.g.start('b', 'LOCAL', True), 'BLOCKED_IN_FLIGHT')

    def test_unknown_retains_slot(self):
        self.g.interrupt('a', 'TIMEOUT')
        self.assertEqual(self.g.interrupt('a', 'CANCEL'), 'UNKNOWN')
        self.assertEqual(self.g.start('b', 'LOCAL', True), 'BLOCKED_IN_FLIGHT')

    def test_bad_receipts_do_not_release(self):
        for field, value in [('rid', 'old'), ('backend', 'CLOUD'), ('source', 'UI'),
                             ('verified', False), ('ended', False), ('released', False),
                             ('ended', 1), ('outcome', 'UNKNOWN')]:
            with self.subTest(field=field):
                self.assertEqual(self.g.confirm(replace(self.ack, **{field: value})), 'REJECT_RECEIPT')
                self.assertIsNotNone(self.g.active)

    def test_cancelled_late_success_hidden(self):
        self.g.fragment('a', '虚构草稿')
        self.g.interrupt('a', 'CANCEL')
        self.assertEqual(self.g.fragment('a', '迟到正文'), 'DROP')
        self.assertEqual(self.g.confirm(self.ack), 'ENDED_SUPPRESSED')
        self.assertEqual(self.g.draft, '')

    def test_unknown_confirmation_then_new_intent(self):
        self.g.interrupt('a', 'LOST')
        self.assertEqual(self.g.confirm(self.ack), 'ENDED_SUPPRESSED')
        self.assertEqual(self.g.start('b', 'LOCAL', True), 'STARTED')

    def test_no_automatic_restart(self):
        self.g.confirm(self.ack)
        self.assertIsNone(self.g.active)
        self.assertEqual(self.g.start('a', 'CLOUD', True), 'DUPLICATE')

    def test_late_old_receipt_cannot_clear_new_slot(self):
        self.g.confirm(self.ack)
        self.g.start('b', 'LOCAL', True)
        self.assertEqual(self.g.confirm(self.ack), 'REJECT_RECEIPT')
        self.assertEqual(self.g.active, ('b', 'LOCAL'))

    def test_old_fragments_ignored(self):
        self.assertEqual(self.g.fragment('old', 'x'), 'DROP')
        self.assertEqual(self.g.draft, '')

    def test_failed_and_cancelled_clear_draft(self):
        for status in ('FAILED', 'CANCELLED'):
            g = EndGuard(); g.start('a', 'LOCAL', True); g.fragment('a', 'x')
            self.assertEqual(g.confirm(replace(self.ack, outcome=status)), 'ENDED_' + status)
            self.assertEqual(g.draft, '')

    def test_new_intent_needs_fresh_approval(self):
        self.g.confirm(self.ack)
        self.assertEqual(self.g.start('b', 'CLOUD'), 'DENY')
        self.assertIsNone(self.g.active)

    def test_parallel_start_one_winner(self):
        g = EndGuard(); barrier = Barrier(3); answers = []
        def start(rid):
            barrier.wait(); answers.append(g.start(rid, 'LOCAL', True))
        threads = [Thread(target=start, args=(rid,)) for rid in ('a', 'b')]
        for t in threads: t.start()
        barrier.wait()
        for t in threads: t.join(timeout=2); self.assertFalse(t.is_alive())
        self.assertCountEqual(answers, ['STARTED', 'BLOCKED_IN_FLIGHT'])

if __name__ == '__main__': unittest.main(verbosity=2)
