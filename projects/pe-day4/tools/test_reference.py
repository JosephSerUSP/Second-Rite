"""Negative controls for source provenance, state gates and snapshot inputs."""
import copy
import unittest
import verify_reference as verify


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.facts = verify.load('facts.json')
        self.route = verify.load('route.json')
        self.snapshot = verify.load('canonical-start.json')
        self.ids = {f['id'] for f in self.facts['facts']}

    def route_errors(self):
        errors = []
        verify.validate_route(self.route, self.ids, errors)
        return errors

    def test_authored_route(self):
        self.assertEqual(self.route_errors(), [])

    def test_mirror_is_not_independent_corroboration(self):
        fact = self.facts['facts'][0]
        for source in fact['sources']:
            self.facts['sources'][source]['independenceGroup'] = 'same-origin'
        errors = []
        verify.validate_facts(self.facts, errors)
        self.assertTrue(any('independent' in e for e in errors))

    def test_each_missing_fuse_breaks_the_route(self):
        original = copy.deepcopy(self.route)
        for flag in ['fuse_1', 'fuse_2', 'fuse_3']:
            self.route = copy.deepcopy(original)
            for node in self.route['nodes']:
                for interaction in node.get('interactions', []):
                    interaction['grants'] = [s for s in interaction.get('grants', []) if s != flag]
            self.assertTrue(any('not statefully reachable' in e for e in self.route_errors()), flag)

    def test_card_gate_cannot_be_bypassed(self):
        next(e for e in self.route['edges'] if e['id'] == 'basement_c_to_d')['requiresAll'] = []
        self.assertTrue(any('entry requirements' in e for e in self.route_errors()))

    def test_power_cannot_skip_wire_repair(self):
        for node in self.route['nodes']:
            for interaction in node.get('interactions', []):
                if interaction['id'] == 'toggle_power':
                    interaction['requiresAll'].remove('wires_repaired')
        self.assertTrue(any('critical requirements' in e for e in self.route_errors()))

    def test_severed_roof_route_is_unreachable(self):
        self.route['edges'] = [e for e in self.route['edges'] if e['id'] != 'roof_elevator']
        self.assertTrue(any('not statefully reachable' in e for e in self.route_errors()))

    def test_crash_cannot_replay_after_power_return(self):
        next(e for e in self.route['edges'] if e['id'] == 'crash_to_basement')['oneShot'] = False
        self.assertTrue(any('mutually exclusive' in e for e in self.route_errors()))

    def test_gondola_fight_cannot_be_skipped(self):
        escape = next(n for n in self.route['nodes'] if n['id'] == 'emergency_elevator')['interactions'][0]
        escape['grants'].append('hospital_complete')
        self.assertTrue(any('critical requirements' in e for e in self.route_errors()))

    def test_severed_gondola_route_is_unreachable(self):
        self.route['edges'] = [e for e in self.route['edges'] if e['id'] != 'gondola_arrival']
        self.assertTrue(any('not statefully reachable' in e for e in self.route_errors()))

    def test_snapshot_rejects_fractional_quantity(self):
        self.snapshot['inventory'][0]['quantity'] = 1.5
        errors = []
        verify.validate_snapshot(self.snapshot, self.ids, set(self.facts['sources']), errors)
        self.assertTrue(any('quantity' in e for e in errors))

    def test_unresolved_magazine_cannot_be_silently_filled(self):
        self.snapshot['equipment']['weapon']['loadedRounds']['value'] = 15
        errors = []
        verify.validate_snapshot(self.snapshot, self.ids, set(self.facts['sources']), errors)
        self.assertTrue(any('unknown value' in e for e in errors))


if __name__ == '__main__':
    unittest.main()
