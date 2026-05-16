import unittest

import main


class CalculatorHelpersTestCase(unittest.TestCase):
    def test_to_float_accepts_spaces_and_comma(self):
        self.assertEqual(main.to_float('1 234,56'), 1234.56)
        self.assertEqual(main.to_float('1000.5'), 1000.5)

    def test_to_float_returns_default_for_invalid_value(self):
        self.assertEqual(main.to_float('abc', default=42), 42)
        self.assertEqual(main.to_float(None, default=7), 7)

    def test_get_period_in_years(self):
        self.assertEqual(main.get_period_in_years(24, 'months'), 2)
        self.assertEqual(main.get_period_in_years(5, 'years'), 5)

    def test_get_periods_per_year(self):
        self.assertEqual(main.get_periods_per_year('daily'), 365)
        self.assertEqual(main.get_periods_per_year('1'), 12)
        self.assertEqual(main.get_periods_per_year('3'), 4)


class CalculatorLogicTestCase(unittest.TestCase):
    def test_calculate_without_reinvest(self):
        result = main.calculate_final_sum(
            start_sum=1200,
            monthly_payment=0,
            rate=12,
            years=1,
            reinvest=False,
            reinvest_period='1',
            add_period='1',
            add_index=0,
            tax_enabled=False,
            tax=0,
            inflation_enabled=False,
            inflation=0,
        )

        self.assertEqual(result['months'], 12)
        self.assertEqual(result['final_sum'], 1344.00)
        self.assertEqual(result['total_payments'], 1200.00)
        self.assertEqual(result['profit'], 144.00)
        self.assertEqual(result['total_tax'], 0)
        self.assertEqual(len(result['months_data']), 12)
        self.assertEqual(len(result['years_data']), 1)

    def test_calculate_with_monthly_reinvest(self):
        result = main.calculate_final_sum(
            start_sum=1200,
            monthly_payment=0,
            rate=12,
            years=1,
            reinvest=True,
            reinvest_period='1',
            add_period='1',
            add_index=0,
            tax_enabled=False,
            tax=0,
            inflation_enabled=False,
            inflation=0,
        )

        self.assertEqual(result['final_sum'], 1352.19)
        self.assertEqual(result['profit'], 152.19)

    def test_calculate_with_tax(self):
        result = main.calculate_final_sum(
            start_sum=1200,
            monthly_payment=0,
            rate=12,
            years=1,
            reinvest=False,
            reinvest_period='1',
            add_period='1',
            add_index=0,
            tax_enabled=True,
            tax=10,
            inflation_enabled=False,
            inflation=0,
        )

        self.assertEqual(result['final_sum'], 1329.60)
        self.assertEqual(result['profit'], 129.60)
        self.assertEqual(result['total_tax'], 14.40)

    def test_calculate_with_inflation(self):
        result = main.calculate_final_sum(
            start_sum=1200,
            monthly_payment=0,
            rate=0,
            years=1,
            reinvest=False,
            reinvest_period='1',
            add_period='1',
            add_index=0,
            tax_enabled=False,
            tax=0,
            inflation_enabled=True,
            inflation=20,
        )

        self.assertEqual(result['final_sum'], 1200.00)
        self.assertEqual(result['real_final_sum'], 1000.00)
        self.assertEqual(result['inflation_loss'], 200.00)

    def test_calculate_with_monthly_payments_and_indexation(self):
        result = main.calculate_final_sum(
            start_sum=1000,
            monthly_payment=100,
            rate=0,
            years=2,
            reinvest=False,
            reinvest_period='1',
            add_period='1',
            add_index=10,
            tax_enabled=False,
            tax=0,
            inflation_enabled=False,
            inflation=0,
        )

        # 12 payments by 100 in the first year and 12 payments by 110 in the second year.
        self.assertEqual(result['total_payments'], 3520.00)
        self.assertEqual(result['final_sum'], 3520.00)
        self.assertEqual(result['profit'], 0.00)

    def test_find_rate(self):
        rate = main.find_rate(
            goal=1352.19,
            start_sum=1200,
            monthly_payment=0,
            years=1,
            reinvest=True,
            reinvest_period='1',
            add_period='1',
            add_index=0,
        )

        self.assertEqual(rate, 12.00)

    def test_find_start_sum(self):
        start_sum = main.find_start_sum(
            goal=1344,
            monthly_payment=0,
            rate=12,
            years=1,
            reinvest=False,
            reinvest_period='1',
            add_period='1',
            add_index=0,
        )

        self.assertEqual(start_sum, 1200.00)

    def test_find_monthly_payment(self):
        payment = main.find_monthly_payment(
            goal=2200,
            start_sum=1000,
            rate=0,
            years=1,
            reinvest=False,
            reinvest_period='1',
            add_period='1',
            add_index=0,
        )

        self.assertEqual(payment, 100.00)

    def test_find_years(self):
        years = main.find_years(
            goal=2200,
            start_sum=1000,
            monthly_payment=100,
            rate=0,
            reinvest=False,
            reinvest_period='1',
            add_period='1',
            add_index=0,
        )

        self.assertEqual(years, 1.00)


class FlaskRoutesTestCase(unittest.TestCase):
    def setUp(self):
        main.app.config['TESTING'] = True
        main.calculation_history.clear()
        main.next_history_id = 1
        self.client = main.app.test_client()

    def test_index_get_returns_page(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response.content_type)

    def test_index_post_adds_record_to_history(self):
        response = self.client.post('/', data={
            'calc_type': 'income',
            'goal': '1000000',
            'start_sum': '1200',
            'period': '1',
            'period_unit': 'years',
            'rate': '12',
            'reinvest': '1',
            'reinvest_period': '1',
            'monthly_payment': '0',
            'add_period': '1',
            'add_index': '0',
            'view_interval': 'years',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(main.calculation_history), 1)
        self.assertEqual(main.calculation_history[0]['id'], 1)
        self.assertEqual(main.calculation_history[0]['type'], 'income')
        self.assertEqual(main.calculation_history[0]['final_sum'], 1352.19)

    def test_history_keeps_only_last_ten_records(self):
        for number in range(12):
            self.client.post('/', data={
                'calc_type': 'income',
                'start_sum': str(1000 + number),
                'period': '1',
                'period_unit': 'years',
                'rate': '0',
                'monthly_payment': '0',
                'add_period': '1',
                'add_index': '0',
            })

        self.assertEqual(len(main.calculation_history), 10)
        self.assertEqual(main.calculation_history[0]['id'], 12)
        self.assertEqual(main.calculation_history[-1]['id'], 3)

    def test_clear_history(self):
        main.calculation_history.append({'id': 1})

        response = self.client.post('/clear_history')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(main.calculation_history, [])


if __name__ == '__main__':
    unittest.main()
