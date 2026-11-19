"""Scientific checks for sequential feed laws and native event handling."""
import unittest

import numpy as np
import pandas as pd

import feed_flow_optimization as reference
import pyfoomb_feed_model as native
from pyfoomb_feed_optimization import HERE, cases
from extend_two_stage_study import replay_timepoints, seed_candidates


class TwoStageFeedTests(unittest.TestCase):
    def test_switch_resets_stage_clock_and_selects_second_rate(self):
        parameters = dict(F1=0.01, F2=0.025, k1=0.002, k2=0.003,
                          mu1=0.08, mu2=0.06, t_switch=12.0)
        for name, shapes in reference.TWO_STAGE_SHAPES.items():
            with self.subTest(strategy=name):
                fn = reference.STRATEGIES[name]['fn']
                p = [parameters[key] for key in reference.STRATEGIES[name]['names']]
                expected_first = (0.01 + 0.002*5 if shapes[0] == 'linear'
                                  else 0.01*np.exp(0.08*5))
                expected_second = (0.025 + 0.003*3 if shapes[1] == 'linear'
                                   else 0.025*np.exp(0.06*3))
                self.assertAlmostEqual(fn(5, None, p, None), expected_first)
                self.assertAlmostEqual(fn(12, None, p, None), parameters['F2'])
                self.assertAlmostEqual(fn(15, None, p, None), expected_second)

    def test_historical_case_indices_are_preserved(self):
        old = pd.read_csv(HERE / 'pyfoomb_results/final/feed_flow_results.csv')
        for index, kind, dataset_index, name in cases(reference.LEGACY_STRATEGIES):
            self.assertEqual(old.iloc[index].strategy, name)
            self.assertEqual(old.iloc[index]['product'], reference.DATA[kind][dataset_index]['product'])
        self.assertEqual([task[0] for task in cases(reference.TWO_STAGE_SHAPES)], list(range(63, 99)))

    def test_solver_agreement_and_mass_balance_across_switch(self):
        ds = reference.DATA['bell_shaped'][1]
        kin = reference.KINETICS[ds['organism_type']]
        qp, fit = reference.fit_qp_model('bell_shaped', ds['mu'], ds['qp'])
        cap = float(ds['mu'].max()*1.2)
        batch = native.simulate_batch(ds, 'bell_shaped')
        for name in reference.TWO_STAGE_SHAPES:
            with self.subTest(strategy=name):
                runner = native.make_runner(ds, 'bell_shaped', name, batch_result=batch)
                for simulator in runner.caretaker.simulators.values():
                    simulator.integrator_kwargs.update(rtol=1e-8, atol=1e-11)
                params = {key: value for key, value in zip(runner.parameter_names,
                          [0.015, 0.002 if 'linear' in reference.TWO_STAGE_SHAPES[name][0] else 0.06,
                           0.08, 0.003 if 'linear' in reference.TWO_STAGE_SHAPES[name][1] else 0.07, 12.0])}
                points = np.unique(np.r_[np.linspace(0, 40, 401), 11.999, 12.0, 12.001])
                result = runner.simulate(params, points)
                scipy = reference.simulate_fedbatch(reference.STRATEGIES[name],
                    [params[key] for key in runner.parameter_names], kin, qp, fit, cap,
                    batch.y_feed, 0.25, rtol=1e-8, atol=1e-11)
                self.assertTrue(scipy.success)
                np.testing.assert_allclose(result.y[:, -1], scipy.y[:, -1], rtol=2e-5, atol=1e-6)
                X, S, P, V = result.y
                X0, S0, _, V0 = batch.y_feed
                residual = X*V-X0*V0 + kin['Yxs']*(S*V-S0*V0-reference.S_IN*(V-V0))
                self.assertLess(np.max(np.abs(residual))/np.max(X*V), 1e-6)
                raw = runner.caretaker.simulate(t=points, parameters=params, verbosity=50)
                volume = next(state.values for state in raw if state.name == 'V')
                self.assertLessEqual(np.max(volume), reference.V_MAX + 1e-7)
                self.assertAlmostEqual(volume[-1], 4.0, places=7)
                runner.caretaker.set_parameters(params)
                model = next(iter(runner.caretaker.simulators.values())).bioprocess_model
                switches = [False]*native.N_EVENTS
                y = [0.0, 0.5, 1.0, 10.0]
                self.assertAlmostEqual(model.state_events(12, y, switches)[native.STAGE_EVENT_INDEX], 0.0)
                switches[native.STAGE_EVENT_INDEX] = True
                self.assertAlmostEqual(model._feed_rate(12, y, switches), params['F2'])
                switches[native.VOLUME_EVENT_INDEX] = True
                self.assertEqual(model._feed_rate(13, y, switches), 0.0)

    def test_equal_constant_stages_reproduce_original_constant_feed(self):
        ds = reference.DATA['linear'][0]
        base = native.make_runner(ds, 'linear', 'constant')
        expected = base.simulate([0.075])
        for name in reference.TWO_STAGE_SHAPES:
            runner = native.make_runner(ds, 'linear', name, batch_result=base.batch)
            params = dict(F1=0.075, F2=0.075, t_switch=13.0)
            params.update({key: 0.0 for key in runner.parameter_names if key not in params})
            result = runner.simulate(params)
            np.testing.assert_allclose(result.y[:, -1], expected.y[:, -1], rtol=2e-4, atol=2e-5)

    def test_dense_replay_avoids_output_point_at_stage_root(self):
        ds = reference.DATA['hyperbolic'][1]
        baseline = pd.read_csv(HERE/'pyfoomb_results/final/feed_flow_results.csv')
        baseline = baseline[baseline['product'] == ds['product']]
        kin = reference.KINETICS[ds['organism_type']]
        name = 'two_stage_exp_exp'
        runner = native.make_runner(ds, 'hyperbolic', name)
        for simulator in runner.caretaker.simulators.values():
            simulator.integrator_kwargs.update(rtol=1e-8, atol=1e-11)
        for source, parameters in seed_candidates(baseline, name, kin):
            if parameters['t_switch'] != 30.0:
                continue
            with self.subTest(candidate=source):
                points = replay_timepoints(parameters['t_switch'])
                self.assertFalse(np.any(points == 30.0))
                result = runner.simulate(parameters, points)
                endpoint = runner.simulate(parameters, [0.0, 40.0])
                # Near depletion, S can differ by sub-microgram/L solver noise.
                np.testing.assert_allclose(result.y[:, -1], endpoint.y[:, -1], rtol=1e-6, atol=1e-6)
                np.testing.assert_allclose(result.total_product, endpoint.total_product, rtol=1e-7)


if __name__ == '__main__':
    unittest.main()
